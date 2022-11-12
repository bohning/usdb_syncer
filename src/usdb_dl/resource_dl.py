"""Functions for downloading and processing media."""

import os
from enum import Enum
from typing import Union

import requests
import yt_dlp
from PIL import Image, ImageEnhance, ImageOps

from usdb_dl import note_utils
from usdb_dl.download_options import AudioOptions, VideoOptions
from usdb_dl.logger import SongLogger, get_logger
from usdb_dl.meta_tags.deserializer import ImageMetaTags
from usdb_dl.settings import Browser
from usdb_dl.typing_helpers import assert_never
from usdb_dl.usdb_scraper import SongDetails

# from moviepy.editor import VideoFileClip
# import subprocess

IMAGE_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"
    )
}


class ImageKind(Enum):
    """Types of images used for songs."""

    COVER = "CO"
    BACKGROUND = "BG"

    def __str__(self) -> str:  # pylint: disable=invalid-str-returned
        match self:
            case ImageKind.COVER:
                return "cover"
            case ImageKind.BACKGROUND:
                return "background"
            case _ as unreachable:
                assert_never(unreachable)


def download_video(
    resource: str,
    options: AudioOptions | VideoOptions,
    browser: Browser,
    path_base: str,
    logger: SongLogger,
) -> str | None:
    """Download video from resource to path and process it according to options.

    Parameters:
        resource: URL or YouTube id
        options: parameters for downloading and processing
        browser: browser to use cookies from
        path_base: the target on the file system *without* an extension

    Returns:
        the extension of the successfully downloaded file or None
    """
    url = f"https://{'' if '/' in resource else 'www.youtube.com/watch?v='}{resource}"
    ydl_opts: dict[str, Union[str, bool, tuple, list]] = {
        # currently fails for archive.org, where yt_dlp can't read codecs
        # could use "best" as a fallback
        "format": options.ytdl_format(),
        "outtmpl": f"{path_base}.%(ext)s",
        "keepvideo": False,
        "verbose": False,
    }
    if browser.value:
        ydl_opts["cookiesfrombrowser"] = (browser.value,)
    if isinstance(options, AudioOptions) and options.reencode_format:
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": options.reencode_format.value,
                "preferredquality": "320",
            }
        ]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            filename = ydl.prepare_filename(ydl.extract_info(f"{url}"))
        except yt_dlp.utils.YoutubeDLError:
            logger.error(f"error downloading video url: {url}")
            return None

    return os.path.splitext(filename)[1][1:]


def download_image(url: str, logger: SongLogger) -> bytes | None:
    try:
        reply = requests.get(
            url, allow_redirects=True, headers=IMAGE_DOWNLOAD_HEADERS, timeout=60
        )
    except:
        logger.error(
            f"Failed to retrieve {url}. The server may be down or your internet "
            "connection is currently unavailable."
        )
        return None
    if reply.status_code in range(100, 199):
        # 1xx informational response
        return reply.content
    if reply.status_code in range(200, 299):
        # 2xx success
        return reply.content
    if reply.status_code in range(300, 399):
        # 3xx redirection
        logger.warning(
            f"Redirection to {reply.next.url if reply.next else 'unknown'}. "
            "Please update the template file."
        )
        return reply.content
    if reply.status_code in range(400, 499):
        # 4xx client errors
        logger.error(
            f"Client error {reply.status_code}. Failed to download {reply.url}"
        )
        return None
    if reply.status_code in range(500, 599):
        # 5xx server errors
        logger.error(
            f"Server error {reply.status_code}. Failed to download {reply.url}"
        )
        return None
    return None


def download_and_process_image(
    header: dict[str, str],
    meta_tags: ImageMetaTags | None,
    details: SongDetails,
    pathname: str,
    kind: ImageKind,
) -> bool:
    logger = get_logger(__file__, details.song_id)
    if not (url := _get_image_url(meta_tags, details, kind, logger)):
        return False
    if not (img_bytes := download_image(url, logger)):
        logger.error(f"#{str(kind).upper()}: file does not exist at url: {url}")
        return False
    fname = f"{note_utils.generate_filename(header)} [{kind.value}].jpg"
    path = os.path.join(pathname, fname)
    with open(path, "wb") as file:
        file.write(img_bytes)
    if meta_tags and meta_tags.image_processing():
        _process_image(meta_tags, path)
    return True


def _get_image_url(
    meta_tags: ImageMetaTags | None,
    details: SongDetails,
    kind: ImageKind,
    logger: SongLogger,
) -> str | None:
    url = None
    if meta_tags:
        url = meta_tags.source_url()
        logger.debug(f"downloading {kind} from #VIDEO params: {url}")
    elif kind is ImageKind.COVER and details.cover_url:
        url = details.cover_url
        logger.warning(
            "no cover resource in #VIDEO tag, so fallback to small usdb cover!"
        )
    else:
        logger.warning(f"no {kind} resource found")
    return url


def _process_image(meta_tags: ImageMetaTags, path: str) -> None:
    with Image.open(path).convert("RGB") as image:
        if rotate := meta_tags.rotate:
            image = image.rotate(rotate, resample=Image.BICUBIC, expand=True)
            # TODO: ensure quadratic cover
        if crop := meta_tags.crop:
            image = image.crop((crop.left, crop.upper, crop.right, crop.lower))
        if resize := meta_tags.resize:
            image = image.resize((resize.width, resize.height), resample=Image.LANCZOS)
        if meta_tags.contrast == "auto":
            image = ImageOps.autocontrast(image, cutoff=5)
        elif meta_tags.contrast:
            image = ImageEnhance.Contrast(image).enhance(meta_tags.contrast)

            # save post-processed cover
        image.save(path, "jpeg", quality=100, subsampling=0)
