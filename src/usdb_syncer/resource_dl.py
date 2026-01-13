"""Functions for downloading and processing media."""

from __future__ import annotations

import io
import re
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final, Generic, TypeVar, assert_never

import filetype
import requests
import yt_dlp
from PIL import Image, ImageEnhance, ImageOps
from PIL.Image import Resampling
from yt_dlp.utils import UnsupportedError, YoutubeDLError, download_range_func

from usdb_syncer import SongId, utils
from usdb_syncer.constants import YtErrorMsg
from usdb_syncer.discord import notify_discord
from usdb_syncer.download_options import AudioOptions, VideoOptions
from usdb_syncer.logger import Logger, song_logger
from usdb_syncer.meta_tags import ImageMetaTags
from usdb_syncer.postprocessing import normalize_audio
from usdb_syncer.settings import (
    AudioNormalization,
    Browser,
    CoverMaxSize,
    YtdlpRateLimit,
)
from usdb_syncer.usdb_scraper import SongDetails
from usdb_syncer.utils import video_url_from_resource

IMAGE_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
}

# Constants for ffmpeg's freezedetect analysis
START_TIME_SECONDS: Final[int] = 0
DURATION_SECONDS: Final[int] = 15
FREEZE_NOISE_DB: Final[int] = -80
FREEZE_DURATION_SECONDS: Final[int] = 1
FREEZE_RATIO_THRESHOLD: Final[float] = 0.5
FFMPEG_TIMEOUT_SECONDS: Final[int] = 60

YtdlOptions = dict[str, str | bool | tuple | list | int | download_range_func]


@dataclass
class ResourceDLError:
    """An error that occurred when downloading a resource."""

    type: DLErrType
    return_code: int | None = None

    def should_notify(self) -> bool:
        """Return whether this error should trigger a Discord notification."""
        return self.type.should_notify()

    def notify_discord(
        self, song_id: SongId, url: str, kind: str, logger: Logger
    ) -> None:
        """Send a Discord notification for this error if enabled."""
        if self.should_notify():
            notify_discord(
                song_id, url, kind, self.type.value, self.return_code, logger
            )


class DLErrType(Enum):
    """Errors that can occur when downloading a resource."""

    INVALID = "resource invalid"
    UNSUPPORTED = "resource unsupported"
    GEO_RESTRICTED = "resource geo-restricted"
    GEO_BLOCKED = "resource geo-blocked"
    UNAVAILABLE = "resource unavailable"
    FORMAT_ERROR = "resource parse error"
    DL_FAILED = "resource download failed"
    FORBIDDEN = "resource forbidden"
    PREMIUM_ONLY = "resource premium only"

    def should_notify(self) -> bool:
        """Return whether this error type should trigger a Discord notification."""
        return self in {
            DLErrType.INVALID,
            DLErrType.UNSUPPORTED,
            DLErrType.UNAVAILABLE,
            DLErrType.FORMAT_ERROR,
        }


T = TypeVar("T", covariant=True)


@dataclass
class ResourceDLResult(Generic[T]):
    """The result of a download operation."""

    content: T | None = None
    error: ResourceDLError | None = None


class ImageKind(Enum):
    """Types of images used for songs."""

    COVER = "CO"
    BACKGROUND = "BG"

    def __str__(self) -> str:
        match self:
            case ImageKind.COVER:
                return "cover"
            case ImageKind.BACKGROUND:
                return "background"
            case _ as unreachable:
                assert_never(unreachable)


def download_audio(
    resource: str,
    options: AudioOptions,
    browser: Browser,
    path_stem: Path,
    logger: Logger,
) -> ResourceDLResult[str]:
    """Download audio from resource to path and process it according to options.

    Parameters:
        resource: URL or YouTube id
        options: parameters for downloading and processing
        browser: browser to use cookies from
        path_stem: the target on the file system *without* an extension
        logger: logger

    Returns:
        DownloadResult with the extension of the (postprocessed, possibly normalized)
        audio file, if successful
    """
    ydl_opts = _ytdl_options(
        options.ytdl_format(), browser, path_stem, options.rate_limit
    )
    if options.normalization in {
        AudioNormalization.DISABLE,
        AudioNormalization.REPLAYGAIN,
    }:
        # DISABLE or REPLAYGAIN normalization will not re-encode the audio file to
        # target format, so we have to add a postprocessor to get it
        postprocessor = {
            "key": "FFmpegExtractAudio",
            "preferredquality": options.bitrate.ytdl_format(),
            "preferredcodec": options.format.ytdl_codec(),
        }
        ydl_opts["postprocessors"] = [postprocessor]

    dl_result = _download_resource(resource, ydl_opts, logger)
    if not dl_result.content:
        return dl_result
    if options.normalization is not AudioNormalization.DISABLE:
        normalize_audio(options, path_stem, dl_result.content, logger)

    # either way, the resulting file is in target format, so we have to correct the
    # extension before returning dl_result
    dl_result.content = options.format.value
    return dl_result


def download_video(
    resource: str,
    options: VideoOptions,
    browser: Browser,
    path_stem: Path,
    logger: Logger,
) -> ResourceDLResult[str]:
    """Download video from resource to path and process it according to options.

    Parameters:
        resource: URL or YouTube id
        options: parameters for downloading and processing
        browser: browser to use cookies from
        path_stem: the target on the file system *without* an extension

    Returns:
        DownloadResult with the extension of the downloaded file if successful
    """
    ydl_opts = _ytdl_options(
        options.ytdl_format(), browser, path_stem, options.rate_limit
    )
    return _download_resource(resource, ydl_opts, logger)


def fallback_resource_is_audio_only(
    options: VideoOptions, url: str, browser: Browser, logger: Logger
) -> bool:
    """Check if a video is audio-only using ffmpeg's freezedetect filter."""

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        temp_video_file = Path(tmp.name)

    try:
        ydl_opts = _ytdl_options(
            options.ytdl_format(),
            browser,
            temp_video_file,
            options.rate_limit,
            segment_only=True,
        )

        dl_result = _download_resource(url, ydl_opts, logger)
        if not dl_result.content:
            return False

        freeze_durations = run_freezedetect(temp_video_file)
        return freeze_ratio_larger_threshold(url, freeze_durations, logger)

    except (subprocess.SubprocessError, OSError, ValueError):
        logger.debug(
            f"Failed to analyze commented resource '{url}' for audio-only content."
        )
        return False

    finally:
        if temp_video_file.exists():
            temp_video_file.unlink()


def run_freezedetect(video_path: Path) -> list[float]:
    with utils.LinuxEnvCleaner():
        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(video_path),
                "-vf",
                f"freezedetect=noise={FREEZE_NOISE_DB}dB:"
                f"duration={FREEZE_DURATION_SECONDS}",
                "-an",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
        )

    return [
        float(duration)
        for duration in re.findall(r"freeze_duration: ([\d.]+)", result.stderr)
    ]


def freeze_ratio_larger_threshold(
    url: str, freeze_durations: list[float], logger: Logger
) -> bool:
    if not freeze_durations:
        logger.debug(f"Commented resource '{url}' is a video, no freezes detected.")
        return False

    freeze_ratio = sum(freeze_durations) / DURATION_SECONDS

    if freeze_ratio >= FREEZE_RATIO_THRESHOLD:
        logger.debug(
            f"Commented resource '{url}' is most likely audio-only: "
            f"{freeze_ratio:.2%} freeze detected."
        )
    else:
        logger.debug(
            f"Commented resource '{url}' is most likely a video: "
            f"only {freeze_ratio:.2%} freeze detected."
        )

    return freeze_ratio >= FREEZE_RATIO_THRESHOLD


def _ytdl_options(
    format_: str,
    browser: Browser,
    target_stem: Path,
    ratelimit: YtdlpRateLimit,
    segment_only: bool = False,
) -> YtdlOptions:
    options: YtdlOptions = {
        "format": format_,
        "outtmpl": f"{target_stem}.%(ext)s",
        "keepvideo": False,
        "verbose": False,
        # suppresses download of playlists, channels and search results
        "playlistend": 0,
        "overwrites": True,
    }
    if ratelimit.value is not None:
        options["ratelimit"] = ratelimit.value
    if browser:
        options["cookiesfrombrowser"] = (browser.value, None, None, None)
    if segment_only:
        options["outtmpl"] = f"{target_stem}"  # includes extension of temp file
        options["download_ranges"] = download_range_func(
            [], [(START_TIME_SECONDS, DURATION_SECONDS)]
        )
        options["force_keyframes_at_cuts"] = True
        options["quiet"] = True
        options["no_warnings"] = True
    return options


def _download_resource(
    resource: str, options: YtdlOptions, logger: Logger
) -> ResourceDLResult[str]:
    if (url := video_url_from_resource(resource)) is None:
        return ResourceDLResult[str](error=ResourceDLError(type=DLErrType.INVALID))

    options_without_cookies = options.copy()
    options_without_cookies.pop("cookiesfrombrowser", None)

    with yt_dlp.YoutubeDL(options_without_cookies) as ydl:  # pyright: ignore[reportArgumentType]  # yt-dlp expects dynamic params
        try:
            filename = ydl.prepare_filename(ydl.extract_info(url))
            ext = Path(filename).suffix[1:]
            return ResourceDLResult(content=ext)
        except UnsupportedError:
            return ResourceDLResult(error=ResourceDLError(type=DLErrType.UNSUPPORTED))
        except YoutubeDLError as e:
            error_message = utils.remove_ansi_codes(str(e))
            logger.debug(f"Failed to download '{url}': {error_message}")
            return _handle_youtube_error(url, resource, error_message, options, logger)


def _handle_youtube_error(
    url: str, resource: str, error_message: str, options: YtdlOptions, logger: Logger
) -> ResourceDLResult:
    """Handle different YouTube error types."""

    if any(
        msg in error_message
        for msg in (YtErrorMsg.YT_AGE_RESTRICTED, YtErrorMsg.VM_UNAUTHENTICATED)
    ):
        dl_result = _retry_with_cookies(url, options, logger)
        return ResourceDLResult[str](content=dl_result.content)

    if any(
        msg in error_message
        for msg in (
            YtErrorMsg.YT_GEO_RESTRICTED_1,
            YtErrorMsg.YT_GEO_RESTRICTED_2,
            YtErrorMsg.YT_GEO_RESTRICTED_3,
        )
    ):
        _handle_geo_restriction(url, resource, logger)
        return ResourceDLResult(error=ResourceDLError(type=DLErrType.GEO_RESTRICTED))

    if YtErrorMsg.YT_UNAVAILABLE in error_message:
        _handle_unavailable(url, logger)
        return ResourceDLResult(error=ResourceDLError(type=DLErrType.UNAVAILABLE))
    if YtErrorMsg.YT_PARSE_ERROR in error_message:
        _handle_parse_error(url, logger)
        return ResourceDLResult(error=ResourceDLError(type=DLErrType.FORMAT_ERROR))

    if YtErrorMsg.YT_FORBIDDEN in error_message:
        _handle_forbidden(url, logger)
        return ResourceDLResult(error=ResourceDLError(type=DLErrType.FORBIDDEN))

    if YtErrorMsg.YT_PREMIUM_ONLY in error_message:
        _handle_premium_only(url, logger)
        return ResourceDLResult(error=ResourceDLError(type=DLErrType.PREMIUM_ONLY))
    if YtErrorMsg.YT_CONFIRM_NOT_BOT in error_message:
        logger.warning(
            "Download failed because YouTube suspects bot activity. "
            "Reconnect to your ISP / reboot your router to get a new external "
            "IP address and try again."
        )
        return ResourceDLResult(error=ResourceDLError(type=DLErrType.DL_FAILED))

    raise


def _retry_with_cookies(
    url: str, options: YtdlOptions, logger: Logger
) -> ResourceDLResult:
    logger.warning("Age-restricted resource. Retrying with cookies ...")
    with yt_dlp.YoutubeDL(options) as ydl:  # pyright: ignore[reportArgumentType]  # yt-dlp expects dynamic params
        try:
            filename = ydl.prepare_filename(ydl.extract_info(url))
            ext = Path(filename).suffix[1:]
            return ResourceDLResult[str](content=ext)
        except YoutubeDLError as re:
            msg = f"Retry failed: {utils.remove_ansi_codes(str(re))}"
            logger.error(msg)  # noqa: TRY400
            raise


def _handle_geo_restriction(url: str, resource: str, logger: Logger) -> None:
    logger.warning("Geo-restricted resource. You can retry after connecting to a VPN.")
    if "youtube" in url and (
        allowed_countries := utils.get_allowed_countries(resource)
    ):
        logger.info(
            "Countries where the resource is available: " + ", ".join(allowed_countries)
        )


def _handle_unavailable(url: str, logger: Logger) -> None:
    logger.warning(
        f"Resource '{url}' is no longer available. Please support the community, "
        "find a suitable replacement resource and comment it on USDB."
    )


def _handle_parse_error(url: str, logger: Logger) -> None:
    logger.warning(f"Failed to parse XML for resource '{url}'.")


def _handle_premium_only(url: str, logger: Logger) -> None:
    logger.warning(f"Failed to download resource '{url}'. Resource is premium-only.")


def _handle_forbidden(url: str, logger: Logger) -> None:
    logger.warning(
        f"Failed to download resource '{url}'. Your IP/account might have been blocked."
    )


def download_image(url: str, logger: Logger) -> ResourceDLResult[bytes]:
    try:
        reply = requests.get(
            url, allow_redirects=True, headers=IMAGE_DOWNLOAD_HEADERS, timeout=60
        )
    except requests.exceptions.SSLError:
        logger.exception(
            f"Failed to retrieve {url}. The SSL certificate could not be verified."
        )
        return ResourceDLResult[bytes](
            error=ResourceDLError(type=DLErrType.UNAVAILABLE)
        )
    except requests.RequestException:
        logger.exception(
            f"Failed to retrieve {url}. The URL might be invalid, the server may be "
            "down or your internet connection is currently unavailable."
        )
        return ResourceDLResult[bytes](
            error=ResourceDLError(type=DLErrType.UNAVAILABLE)
        )
    if reply.status_code in range(100, 299):
        # 1xx informational response, 2xx success
        return ResourceDLResult[bytes](content=reply.content)
    if reply.status_code in range(300, 399):
        # 3xx redirection
        logger.debug(
            f"'{url}' redirects to '{reply.headers['Location']}'. "
            "Please adapt metatags."
        )
        return ResourceDLResult[bytes](content=reply.content)
    if reply.status_code in range(400, 499):
        logger.error(
            f"Client error {reply.status_code}. Failed to download {reply.url}"
        )
    elif reply.status_code in range(500, 599):
        logger.error(
            f"Server error {reply.status_code}. Failed to download {reply.url}"
        )
    return ResourceDLResult[bytes](
        error=ResourceDLError(type=DLErrType.UNAVAILABLE, return_code=reply.status_code)
    )


def download_and_process_image(
    url: str,
    *,
    target_stem: Path,
    meta_tags: ImageMetaTags | None,
    details: SongDetails,
    kind: ImageKind,
    max_width: CoverMaxSize | None,
    process: bool = True,
    notify_discord: bool = False,
) -> Path | None:
    logger = song_logger(details.song_id)
    if not (dl_result := download_image(url, logger)).content:
        logger.error(f"#{str(kind).upper()}: file does not exist at url: {url}")
        if notify_discord and dl_result.error:
            dl_result.error.notify_discord(
                details.song_id, url, str(kind).capitalize(), logger
            )
        return None

    if not filetype.is_image(dl_result.content):
        logger.error(f"#{str(kind).upper()}: file at {url} is not an image")
        ResourceDLError(type=DLErrType.INVALID).notify_discord(
            details.song_id, url, str(kind).capitalize(), logger
        )
        return None

    path = target_stem.with_name(f"{target_stem.name} [{kind.value}].jpg")
    with Image.open(io.BytesIO(dl_result.content)).convert("RGB") as img:
        img.save(path)

    if process:
        _process_image(meta_tags, kind, max_width, path)
    return path


def _rotate(image: Image.Image, meta_tags: ImageMetaTags) -> Image.Image:
    if rotate := meta_tags.rotate:
        return image.rotate(rotate, resample=Resampling.BICUBIC, expand=True)
    return image


def _crop(image: Image.Image, meta_tags: ImageMetaTags) -> Image.Image:
    if crop := meta_tags.crop:
        return image.crop((crop.left, crop.upper, crop.right, crop.lower))
    return image


def _resize(image: Image.Image, meta_tags: ImageMetaTags) -> Image.Image:
    if resize := meta_tags.resize:
        return image.resize((resize.width, resize.height), resample=Resampling.LANCZOS)
    return image


def _adjust_contrast(image: Image.Image, meta_tags: ImageMetaTags) -> Image.Image:
    if meta_tags.contrast == "auto":
        return ImageOps.autocontrast(image, cutoff=5)
    if meta_tags.contrast:
        return ImageEnhance.Contrast(image).enhance(meta_tags.contrast)
    return image


def _process_image(
    meta_tags: ImageMetaTags | None,
    kind: ImageKind,
    max_width: CoverMaxSize | None,
    path: Path,
) -> None:
    processed = False
    with Image.open(path).convert("RGB") as image:
        if meta_tags and meta_tags.image_processing():
            processed = True
            match kind:
                case ImageKind.COVER:
                    operations = [_rotate, _crop, _resize, _adjust_contrast]
                case ImageKind.BACKGROUND:
                    operations = [_resize, _crop]
                case _ as unreachable:
                    assert_never(unreachable)

            for operation in operations:
                image = operation(image, meta_tags)

        if (
            max_width
            and max_width != CoverMaxSize.DISABLE
            and max_width.value < image.width
        ):
            processed = True
            height = round(image.height * max_width.value / image.width)
            image = image.resize((max_width.value, height), resample=Resampling.LANCZOS)

        if processed:
            image.save(path, "jpeg", quality=100, subsampling=0)
