"""Functions for downloading and processing media."""

import os
import tempfile
from enum import Enum
from pathlib import Path
from typing import Union, assert_never

import filetype
import requests
import yt_dlp
from ffmpeg_normalize import FFmpegNormalize
from PIL import Image, ImageEnhance, ImageOps
from PIL.Image import Resampling

from usdb_syncer import settings
from usdb_syncer.download_options import AudioOptions, CookieOptions, VideoOptions
from usdb_syncer.logger import Log, song_logger
from usdb_syncer.meta_tags import ImageMetaTags
from usdb_syncer.settings import CookieFormat, CoverMaxSize, YtdlpRateLimit
from usdb_syncer.usdb_scraper import SongDetails
from usdb_syncer.utils import video_url_from_resource

IMAGE_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
}

YtdlOptions = dict[str, Union[str, bool, tuple, list, int]]


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
    cookie_options: CookieOptions,
    path_stem: Path,
    logger: Log,
) -> str | None:
    """Download audio from resource to path and process it according to options.

    Parameters:
        resource: URL or YouTube id
        options: parameters for downloading and processing
        cookie_options: parameters for cookie retrieval
        path_stem: the target on the file system *without* an extension

    Returns:
        the extension of the successfully downloaded file or None
    """
    ydl_opts = _ytdl_options(
        options.ytdl_format(), cookie_options, path_stem, options.rate_limit
    )
    if not options.normalize:
        postprocessor = {
            "key": "FFmpegExtractAudio",
            "preferredquality": options.bitrate.ytdl_format(),
            "preferredcodec": options.format.ytdl_codec(),
        }
        ydl_opts["postprocessors"] = [postprocessor]

    if not (filename := _download_resource(ydl_opts, resource, logger)):
        return None

    if options.normalize:
        _normalize(options, path_stem, filename)

    return options.format.value


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
    resource: str,
    options: VideoOptions,
    cookie_options: CookieOptions,
    path_stem: Path,
    logger: Log,
) -> str | None:
    """Download video from resource to path and process it according to options.

    Parameters:
        resource: URL or YouTube id
        options: parameters for downloading and processing
        cookie_options: parameters for cookie retrieval
        path_stem: the target on the file system *without* an extension

    Returns:
        the extension of the successfully downloaded file or None
    """
    ydl_opts = _ytdl_options(
        options.ytdl_format(), cookie_options, path_stem, options.rate_limit
    )
    if filename := _download_resource(ydl_opts, resource, logger):
        return os.path.splitext(filename)[1][1:]
    return None


def _ytdl_options(
    format_: str,
    cookie_options: CookieOptions,
    target_stem: Path,
    ratelimit: YtdlpRateLimit,
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
    if cookie_options.cookies_from_browser and cookie_options.browser:
        if cookies := cookie_options.browser.cookies(
            "youtube.com", CookieFormat.NETSCAPE
        ):
            with tempfile.NamedTemporaryFile(delete=False, mode="w") as cookie_file:
                cookie_file.write(str(cookies))
            options["cookiefile"] = cookie_file.name
    if not cookie_options.cookies_from_browser:
        if cookies := settings.get_cookies():
            with tempfile.NamedTemporaryFile(delete=False, mode="w") as cookie_file:
                cookie_file.write(cookies)
            options["cookiefile"] = str(cookie_file.name)
    return options


def _download_resource(options: YtdlOptions, resource: str, logger: Log) -> str | None:
    if (url := video_url_from_resource(resource)) is None:
        logger.debug(f"invalid audio/video resource: {resource}")
        return None

    options_without_cookies = options.copy()
    options_without_cookies.pop("cookiefile", None)
    with yt_dlp.YoutubeDL(options_without_cookies) as ydl:
        try:
            return ydl.prepare_filename(ydl.extract_info(url))
        except yt_dlp.utils.YoutubeDLError as e:
            logger.debug(f"error downloading video url: {url}")
            # Check if the error is due to age restriction
            if "confirm your age" in str(e).lower():
                logger.debug("Age-restricted resource. Retrying with cookies ...")
                try:
                    with yt_dlp.YoutubeDL(options) as ydl:
                        return ydl.prepare_filename(ydl.extract_info(url))
                except yt_dlp.utils.YoutubeDLError as retry_error:
                    logger.error(f"Retry failed: {retry_error}")
                    return None
            else:
                return None


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
    if reply.status_code in range(100, 399):
        # 1xx informational response, 2xx success, 3xx redirection
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
        logger.error(f"#{str(kind).upper()}: file at {url} is no image")
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
