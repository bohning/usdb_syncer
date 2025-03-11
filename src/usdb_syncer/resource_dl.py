"""Functions for downloading and processing media."""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Union, assert_never

import filetype
import requests
import yt_dlp
from ffmpeg_normalize import FFmpegNormalize
from PIL import Image, ImageEnhance, ImageOps
from PIL.Image import Resampling

from usdb_syncer import utils
from usdb_syncer.constants import YtErrorMsg
from usdb_syncer.download_options import AudioOptions, VideoOptions
from usdb_syncer.logger import Log, song_logger
from usdb_syncer.meta_tags import ImageMetaTags
from usdb_syncer.settings import Browser, CoverMaxSize, YtdlpRateLimit
from usdb_syncer.usdb_scraper import SongDetails
from usdb_syncer.utils import video_url_from_resource

IMAGE_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
}

YtdlOptions = dict[str, Union[str, bool, tuple, list, int]]


class ResourceInvalidError(Exception):
    """Raised when a resource is invalid."""


class ResourceUnsupportedError(Exception):
    """Raised when a resource is unsupported."""


class ResourceGeoRestrictedError(Exception):
    """Raised when a resource is geo-restricted."""


class ResourceUnavailableError(Exception):
    """Raised when a resource is not available."""


class ResourceDLError(Enum):
    """Errors that can occur when downloading a resource."""

    RESOURCE_INVALID = "Resource invalid"
    RESOURCE_UNSUPPORTED = "Resource unsupported"
    RESOURCE_GEO_RESTRICTED = "Resource geo-restricted"
    RESOURCE_UNAVAILABLE = "Resource unavailable"
    RESOURCE_DL_FAILED = "Resource download failed"


@dataclass
class ResourceDLResult:
    """The result of a download operation."""

    extension: Optional[str] = None
    error: Optional[ResourceDLError] = None


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
    resource: str, options: AudioOptions, browser: Browser, path_stem: Path, logger: Log
) -> ResourceDLResult:
    """Download audio from resource to path and process it according to options.

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
    if not options.normalize:
        # Add postprocessor if normalization is NOT needed (direct audio extract)
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredquality": options.bitrate.ytdl_format(),
                "preferredcodec": options.format.ytdl_codec(),
            }
        ]

    # Download the resource
    download_result = _download(resource, ydl_opts, logger)

    # If download was successful and normalization is requested
    if download_result.extension and options.normalize:
        filename = f"{path_stem}.{download_result.extension}"
        _normalize(options, path_stem, filename)

    return download_result


def _normalize(options: AudioOptions, path_stem: Path, filename: str) -> None:
    normalizer = FFmpegNormalize(
        normalization_type="ebu",  # default: "ebu"
        target_level=-23,  # default: -23
        print_stats=True,  # set to False?
        keep_lra_above_loudness_range_target=True,  # needed for linear normalization
        loudness_range_target=7,  # default: 7.0
        true_peak=-2,  # default: -2
        dynamic=False,  # default: False
        audio_codec=options.format.ffmpeg_encoder(),
        audio_bitrate=options.bitrate.ffmpeg_format(),
        sample_rate=None,  # default
        debug=True,  # set to False
        progress=True,  # set to False?
    )
    ext = options.format.value
    normalizer.add_media_file(filename, f"{path_stem}.{ext}")
    normalizer.run_normalization()


def download_video(
    resource: str, options: VideoOptions, browser: Browser, path_stem: Path, logger: Log
) -> ResourceDLResult:
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
    return _download(resource, ydl_opts, logger)


def _download(resource: str, options: YtdlOptions, logger: Log) -> ResourceDLResult:
    try:
        filename = _download_resource(options, resource, logger)
        ext = os.path.splitext(filename)[1][1:]
        return ResourceDLResult(extension=ext)
    except ResourceInvalidError as e:
        logger.warning(str(e))
        return ResourceDLResult(error=ResourceDLError.RESOURCE_INVALID)
    except ResourceUnsupportedError as e:
        logger.warning(str(e))
        return ResourceDLResult(error=ResourceDLError.RESOURCE_UNSUPPORTED)
    except ResourceGeoRestrictedError as e:
        logger.warning(str(e))
        return ResourceDLResult(error=ResourceDLError.RESOURCE_GEO_RESTRICTED)
    except ResourceUnavailableError as e:
        logger.warning(str(e))
        return ResourceDLResult(error=ResourceDLError.RESOURCE_UNAVAILABLE)
    except yt_dlp.utils.YoutubeDLError as e:
        logger.warning(f"YoutubeDL error: {e}")
        return ResourceDLResult(error=ResourceDLError.RESOURCE_DL_FAILED)


def _ytdl_options(
    format_: str, browser: Browser, target_stem: Path, ratelimit: YtdlpRateLimit
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
    return options


def _download_resource(options: YtdlOptions, resource: str, logger: Log) -> str:
    if (url := video_url_from_resource(resource)) is None:
        raise ResourceInvalidError(f"Invalid resource {resource}")

    options_without_cookies = options.copy()
    options_without_cookies.pop("cookiesfrombrowser", None)

    with yt_dlp.YoutubeDL(options_without_cookies) as ydl:
        try:
            return ydl.prepare_filename(ydl.extract_info(url))
        except yt_dlp.utils.UnsupportedError as e:
            raise ResourceUnsupportedError(f"Resource {resource} not supported.") from e
        except yt_dlp.utils.YoutubeDLError as e:
            error_message = utils.remove_ansi_codes(str(e))
            logger.debug(f"Failed to download '{url}': {error_message}")
            if YtErrorMsg.YT_AGE_RESTRICTED in error_message:
                return _retry_with_cookies(url, options, logger)
            if YtErrorMsg.YT_GEO_RESTRICTED in error_message:
                _handle_geo_restriction(url, resource, logger)
                raise ResourceGeoRestrictedError(
                    f"Resource {resource} is geo-restricted."
                ) from e
            if YtErrorMsg.YT_NOT_AVAILABLE in error_message:
                _handle_not_available(url, logger)
                raise ResourceUnavailableError(
                    f"Resource {resource} not available"
                ) from e
            raise


def _retry_with_cookies(url: str, options: YtdlOptions, logger: Log) -> str:
    logger.warning("Age-restricted resource. Retrying with cookies...")
    with yt_dlp.YoutubeDL(options) as ydl:
        try:
            return ydl.prepare_filename(ydl.extract_info(url))
        except yt_dlp.utils.YoutubeDLError as re:
            logger.error(f"Retry failed: {utils.remove_ansi_codes(str(re))}")
            raise


def _handle_geo_restriction(url: str, resource: str, logger: Log) -> None:
    logger.warning("Geo-restricted resource. You can retry after connecting to a VPN.")
    if "youtube" in url and (
        allowed_countries := utils.get_allowed_countries(resource)
    ):
        logger.info(
            "Countries where the resource is available: " + ", ".join(allowed_countries)
        )


def _handle_not_available(url: str, logger: Log) -> None:
    logger.warning(
        f"Resource '{url}' is either faulty or no longer available. Help the community, "
        "find a suitable replacement and comment it on USDB."
    )


def download_image(url: str, logger: Log) -> bytes | None:
    try:
        reply = requests.get(
            url, allow_redirects=True, headers=IMAGE_DOWNLOAD_HEADERS, timeout=60
        )
    except requests.exceptions.SSLError:
        logger.error(
            f"Failed to retrieve {url}. The SSL certificate could not be verified."
        )
        return None
    except requests.RequestException:
        logger.error(
            f"Failed to retrieve {url}. The URL might be invalid, the server may be "
            "down or your internet connection is currently unavailable."
        )
        return None
    if reply.status_code in range(100, 299):
        # 1xx informational response, 2xx success
        return reply.content
    if reply.status_code in range(300, 399):
        # 3xx redirection
        logger.debug(
            f"'{url}' redirects to '{reply.headers["Location"]}'. "
            "Please adapt metatags."
        )
        return reply.content
    if reply.status_code in range(400, 499):
        logger.error(
            f"Client error {reply.status_code}. Failed to download {reply.url}"
        )
    elif reply.status_code in range(500, 599):
        logger.error(
            f"Server error {reply.status_code}. Failed to download {reply.url}"
        )
    return None


def download_and_process_image(
    url: str,
    *,
    target_stem: Path,
    meta_tags: ImageMetaTags | None,
    details: SongDetails,
    kind: ImageKind,
    max_width: CoverMaxSize | None,
    process: bool = True,
) -> Path | None:
    logger = song_logger(details.song_id)
    if not (img_bytes := download_image(url, logger)):
        logger.error(f"#{str(kind).upper()}: file does not exist at url: {url}")
        return None

    if not filetype.is_image(img_bytes):
        logger.error(f"#{str(kind).upper()}: file at {url} is not an image")
        return None

    path = target_stem.with_name(f"{target_stem.name} [{kind.value}].jpg")
    with path.open("wb") as file:
        file.write(img_bytes)

    if process:
        _process_image(meta_tags, max_width, path)
    return path


def _process_image(
    meta_tags: ImageMetaTags | None, max_width: CoverMaxSize | None, path: Path
) -> None:
    processed = False
    with Image.open(path).convert("RGB") as image:
        if meta_tags and meta_tags.image_processing():
            processed = True
            if rotate := meta_tags.rotate:
                image = image.rotate(rotate, resample=Resampling.BICUBIC, expand=True)
            if crop := meta_tags.crop:
                image = image.crop((crop.left, crop.upper, crop.right, crop.lower))
            if resize := meta_tags.resize:
                image = image.resize(
                    (resize.width, resize.height), resample=Resampling.LANCZOS
                )
            if meta_tags.contrast == "auto":
                image = ImageOps.autocontrast(image, cutoff=5)
            elif meta_tags.contrast:
                image = ImageEnhance.Contrast(image).enhance(meta_tags.contrast)
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
