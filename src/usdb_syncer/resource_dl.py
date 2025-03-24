"""Functions for downloading and processing media."""

import io
import os
import traceback
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import assert_never

import filetype
import requests
import yt_dlp
from ffmpeg_normalize import FFmpegNormalize
from mutagen.id3 import ID3, TXXX
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis
from PIL import Image, ImageEnhance, ImageOps
from PIL.Image import Resampling

from usdb_syncer import utils
from usdb_syncer.constants import YtErrorMsg
from usdb_syncer.download_options import AudioOptions, VideoOptions
from usdb_syncer.logger import Log, song_logger
from usdb_syncer.meta_tags import ImageMetaTags
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

DEFAULT_TARGET_LEVEL_RG_DB = -18.0
DEFAULT_TARGET_LEVEL_R128_DB = -23.0
DEFAULT_TARGET_LOUDNESS_RANGE = 7.0
DEFAULT_TRUE_PEAK = -2.0

YtdlOptions = dict[str, str | bool | tuple | list | int]


class ResourceDLError(Enum):
    """Errors that can occur when downloading a resource."""

    RESOURCE_INVALID = "resource invalid"
    RESOURCE_UNSUPPORTED = "resource unsupported"
    RESOURCE_GEO_RESTRICTED = "resource geo-restricted"
    RESOURCE_UNAVAILABLE = "resource unavailable"
    RESOURCE_DL_FAILED = "resource download failed"


@dataclass
class ResourceDLResult:
    """The result of a download operation."""

    extension: str | None = None
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
    resource: str, options: AudioOptions, browser: Browser, path_stem: Path, logger: Log
) -> ResourceDLResult:
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
    if not dl_result.extension:
        return dl_result
    match options.normalization:
        case AudioNormalization.DISABLE:
            pass
        case AudioNormalization.REPLAYGAIN:
            # audio file already has the target format -> only write replay gain tags
            _normalize(options, path_stem, options.format.value, logger)
        case AudioNormalization.NORMALIZE:
            # audio file is re-encoded to target format during normalization
            _normalize(options, path_stem, dl_result.extension, logger)
        case _ as unreachable:
            assert_never(unreachable)

    # either way, the resulting file is in target format, so we have to correct the
    # extension before returning dl_result
    dl_result.extension = options.format.value
    return dl_result


def _normalize(
    options: AudioOptions, path_stem: Path, input_ext: str, logger: Log
) -> None:
    input_file = f"{path_stem}.{input_ext}"
    output_ext = options.format.value
    target_level = (
        DEFAULT_TARGET_LEVEL_R128_DB
        if output_ext == "opus"
        else DEFAULT_TARGET_LEVEL_RG_DB
    )
    if options.normalization == AudioNormalization.REPLAYGAIN:
        # we do not want to actually rewrite the file, so we use NUL
        extra_output_options = ["-f", "null"]
        output_file = os.devnull
    else:
        extra_output_options = []
        output_file = f"{path_stem}.{output_ext}"

    normalizer = _create_normalizer(options, target_level, extra_output_options)
    normalizer.add_media_file(input_file, output_file)
    normalizer.run_normalization()

    if options.normalization == AudioNormalization.REPLAYGAIN:
        _write_replaygain_tags(normalizer, input_file, target_level, logger)


def _create_normalizer(
    options: AudioOptions, target_level: float, extra_output_options: list[str]
) -> FFmpegNormalize:
    normalizer = FFmpegNormalize(
        normalization_type="ebu",  # default: "ebu"
        target_level=target_level,
        print_stats=True,  # set to False?
        keep_lra_above_loudness_range_target=True,  # needed for linear normalization
        loudness_range_target=DEFAULT_TARGET_LOUDNESS_RANGE,
        true_peak=DEFAULT_TRUE_PEAK,
        dynamic=False,  # default: False
        audio_codec=options.format.ffmpeg_encoder(),
        audio_bitrate=options.bitrate.ffmpeg_format(),
        sample_rate=None,  # default
        debug=True,  # set to False?
        progress=True,  # set to False?
        extra_output_options=extra_output_options,
    )

    return normalizer


def _write_replaygain_tags(
    normalizer: FFmpegNormalize, audio_file: str, target_level: float, logger: Log
) -> None:
    """Writes ReplayGain values to audio file metadata."""

    # extract stats from 2-pass normalization, then set replay gain values to audio file
    stats_iterable = normalizer.media_files[0].get_stats()
    stats = next(iter(stats_iterable), None)
    if not stats:
        logger.error("Normalization failed: no stats")
        return
    ebu_pass2 = stats.get("ebu_pass2")
    if not ebu_pass2:
        logger.error("Normalization failed: no EBU Pass 2 normalization stats")
        return
    input_i = ebu_pass2.get("input_i")  # Integrated loudness
    input_tp = ebu_pass2.get("input_tp")  # True peak

    if input_i is None or input_tp is None:
        logger.error("Normalization failed: no loudness or true peak stats")
        return
    track_gain = target_level - input_i  # dB
    track_peak = 10 ** (input_tp / 20)  # Linear scale

    try:
        match Path(audio_file).suffix:
            case ".m4a":
                _write_replaygain_tags_m4a(audio_file, track_gain, track_peak)
            case ".mp3":
                _write_replaygain_tags_mp3(audio_file, track_gain, track_peak)
            case ".ogg":
                _write_replaygain_tags_ogg(audio_file, track_gain, track_peak)
            case ".opus":
                _write_replaygain_tags_opus(audio_file, track_gain)

        logger.info(f"ReplayGain tags written to {audio_file}")

    except Exception:  # pylint: disable=broad-exception-caught
        logger.debug(traceback.format_exc())
        logger.error(f"Failed to write audio tags to file '{audio_file}'!")
    else:
        logger.debug(f"Audio tags written to file '{audio_file}'.")


def _write_replaygain_tags_m4a(
    audio_file: str, track_gain: float, track_peak: float
) -> None:
    mp4 = MP4(audio_file)
    if not mp4.tags:
        mp4.add_tags()
    if not mp4.tags:
        return
    mp4.tags["----:com.apple.iTunes:REPLAYGAIN_TRACK_GAIN"] = [
        f"{track_gain:.2f} dB".encode()
    ]
    mp4.tags["----:com.apple.iTunes:REPLAYGAIN_TRACK_PEAK"] = [
        f"{track_peak:.6f}".encode()
    ]
    mp4.save()


def _write_replaygain_tags_mp3(
    audio_file: str, track_gain: float, track_peak: float
) -> None:
    mp3 = MP3(audio_file, ID3=ID3)
    if not mp3.tags:
        return
    mp3.tags.add(TXXX(desc="REPLAYGAIN_TRACK_GAIN", text=[f"{track_gain:.2f} dB"]))
    mp3.tags.add(TXXX(desc="REPLAYGAIN_TRACK_PEAK", text=[f"{track_peak:.6f}"]))
    mp3.save()


def _write_replaygain_tags_ogg(
    audio_file: str, track_gain: float, track_peak: float
) -> None:
    ogg = OggVorbis(audio_file)
    ogg["REPLAYGAIN_TRACK_GAIN"] = [f"{track_gain:.2f} dB"]
    ogg["REPLAYGAIN_TRACK_PEAK"] = [f"{track_peak:.6f}"]
    ogg.save()


def _write_replaygain_tags_opus(audio_file: str, track_gain: float) -> None:
    opus = OggOpus(audio_file)
    # See https://datatracker.ietf.org/doc/html/rfc7845#section-5.2.1
    opus["R128_TRACK_GAIN"] = [str(round(256 * track_gain))]
    opus.save()


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
    return _download_resource(resource, ydl_opts, logger)


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


def _download_resource(
    resource: str, options: YtdlOptions, logger: Log
) -> ResourceDLResult:
    if (url := video_url_from_resource(resource)) is None:
        return ResourceDLResult(error=ResourceDLError.RESOURCE_INVALID)

    options_without_cookies = options.copy()
    options_without_cookies.pop("cookiesfrombrowser", None)

    with yt_dlp.YoutubeDL(options_without_cookies) as ydl:
        try:
            filename = ydl.prepare_filename(ydl.extract_info(url))
            ext = os.path.splitext(filename)[1][1:]
            return ResourceDLResult(extension=ext)
        except yt_dlp.utils.UnsupportedError:
            return ResourceDLResult(error=ResourceDLError.RESOURCE_UNSUPPORTED)
        except yt_dlp.utils.YoutubeDLError as e:
            error_message = utils.remove_ansi_codes(str(e))
            logger.debug(f"Failed to download '{url}': {error_message}")
            if YtErrorMsg.YT_AGE_RESTRICTED in error_message:
                dl_result = _retry_with_cookies(url, options, logger)
                return ResourceDLResult(extension=dl_result.extension)
            if YtErrorMsg.YT_GEO_RESTRICTED in error_message:
                _handle_geo_restriction(url, resource, logger)
                return ResourceDLResult(error=ResourceDLError.RESOURCE_GEO_RESTRICTED)
            if YtErrorMsg.YT_UNAVAILABLE in error_message:
                _handle_unavailable(url, logger)
                return ResourceDLResult(error=ResourceDLError.RESOURCE_UNAVAILABLE)
            raise


def _retry_with_cookies(
    url: str, options: YtdlOptions, logger: Log
) -> ResourceDLResult:
    logger.warning("Age-restricted resource. Retrying with cookies...")
    with yt_dlp.YoutubeDL(options) as ydl:
        try:
            filename = ydl.prepare_filename(ydl.extract_info(url))
            ext = os.path.splitext(filename)[1][1:]
            return ResourceDLResult(extension=ext)
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


def _handle_unavailable(url: str, logger: Log) -> None:
    logger.warning(
        f"Resource '{url}' is no longer available. Please support the community, find a "
        "suitable replacement resource and comment it on USDB."
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
    with Image.open(io.BytesIO(img_bytes)).convert("RGB") as img:
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
