"""Functions for downloading and processing media."""

import json
import locale
import os
import re
import shutil
import subprocess
import tempfile
from enum import Enum
from typing import Union

import filetype
import requests
import yt_dlp
from PIL import Image, ImageEnhance, ImageOps

from usdb_syncer.download_options import AudioOptions, VideoOptions
from usdb_syncer.logger import Log, get_logger
from usdb_syncer.meta_tags.deserializer import ImageMetaTags
from usdb_syncer.settings import Browser
from usdb_syncer.typing_helpers import assert_never
from usdb_syncer.usdb_scraper import SongDetails

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


def url_from_video_resouce(resource: str) -> str:
    if "://" in resource:
        return resource
    if "/" in resource:
        return f"https://{resource}"
    return f"https://www.youtube.com/watch?v={resource}"


def normalize_loudness(path: str, logger: Log) -> None:
    """normalize audio file loudness

    Parameters:
        path: the (unnormalized) audio file path

    Details:
        Uses ffmpeg's loudnorm filter to measure paramters and apply correction of
        (perceived) loudness in accordance with EBU R128 in tow passes,
        see https://trac.ffmpeg.org/wiki/AudioVolume

        according to https://wiki.tnonline.net/w/Blog/Audio_normalization_with_FFmpeg:
        - I: set integrated loudness target
            - Range is -70.0 - -5.0.
            - Default value is -24.0.
            - For EBU R128 normalization a target of -23dB should be used.
        - LRA: set loudness range target.
            - Range is 1.0 - 20.0.
            - Default value is 7.0.
        - TP: set maximum true peak.
            - Range is -9.0 - +0.0.
            - Default value is -2.0.
    """
    default_lra = 7

    # 1st pass, no output file created, read out loudnorm parameters
    command = [
        "ffmpeg",
        # quiet output
        "-hide_banner",
        "-nostats",
        # input file
        "-i",
        path,
        # loudness normalization
        "-af",
        f"loudnorm=I=-23:LRA={default_lra}:TP=-2:print_format=json",
        # no output file
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(command, check=True, stdout=None, stderr=subprocess.PIPE)

    # parse parameters from 1st pass stdout
    json_output = re.sub(
        r"^.*({[^}]*}).*$",
        r"\1",
        result.stderr.decode(locale.getpreferredencoding()).replace(os.linesep, ""),
    )
    data = json.loads(json_output)

    measured_i = data["input_i"]
    measured_lra = data["input_lra"]
    measured_tp = data["input_tp"]
    measured_thresh = data["input_thresh"]
    offset = data["target_offset"]

    # use measured_lra, if bigger than default_lra
    lra = measured_lra if float(measured_lra) > default_lra else default_lra

    # temporary copy of file
    # Note: delete=False required on windows to prevent PermissionError: [Errno 13] Permission denied
    with tempfile.NamedTemporaryFile(delete=False, dir=os.path.dirname(path)) as tmp:
        shutil.copy2(path, tmp.name)

        # 2nd pass, generate output file, read loudnorm parameters for normalization type
        command = [
            "ffmpeg",
            # quiet output
            "-hide_banner",
            "-nostats",
            # input file
            "-i",
            tmp.name,
            # loudness normalization
            "-af",
            f"loudnorm=I=-23:LRA={lra}:tp=-2:"
            f"measured_I={measured_i}:measured_LRA={measured_lra}:"
            f"measured_tp={measured_tp}:measured_thresh={measured_thresh}:offset={offset}:"
            f"linear=true:print_format=json",
            # overwrite if output file exists
            "-y",
            # output file
            path,
        ]
        result = subprocess.run(
            command, check=True, stdout=None, stderr=subprocess.PIPE
        )

    # remove temporary file, required because of delete=False
    os.unlink(tmp.name)

    # parse parameters from 2nd pass stdout
    json_output = re.sub(
        r"^.*({[^}]*}).*$",
        r"\1",
        result.stderr.decode(locale.getpreferredencoding()).replace(os.linesep, ""),
    )
    data = json.loads(json_output)

    normalization_type = data["normalization_type"]
    logger.info(f"normalization type: {normalization_type}")
    if normalization_type.lower() != "linear":
        logger.warning(f"non-linear loudness normalization: {normalization_type}")

    logger.info("normalization done")


def download_video(
    resource: str,
    options: AudioOptions | VideoOptions,
    browser: Browser,
    path_stem: str,
    logger: Log,
) -> str | None:
    """Download video from resource to path and process it according to options.

    Parameters:
        resource: URL or YouTube id
        options: parameters for downloading and processing
        browser: browser to use cookies from
        path_stem: the target on the file system *without* an extension

    Returns:
        the extension of the successfully downloaded file or None
    """
    url = url_from_video_resouce(resource)
    ext = None
    ydl_opts: dict[str, Union[str, bool, tuple, list]] = {
        "format": options.ytdl_format(),
        "outtmpl": f"{path_stem}.%(ext)s",
        "keepvideo": False,
        "verbose": False,
    }
    if browser.value:
        ydl_opts["cookiesfrombrowser"] = (browser.value,)
    if isinstance(options, AudioOptions):
        postprocessor = {
            "key": "FFmpegExtractAudio",
            "preferredquality": "320",
            "preferredcodec": options.format.value,
        }
        ydl_opts["postprocessors"] = [postprocessor]
        # `prepare_filename()` does not take into account postprocessing, so note the
        # file extension
        ext = options.format.value

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            filename = ydl.prepare_filename(ydl.extract_info(f"{url}"))
        except yt_dlp.utils.YoutubeDLError:
            logger.debug(f"error downloading video url: {url}")
            return None

    actual_file_ext = ext or os.path.splitext(filename)[1][1:]
    if isinstance(options, AudioOptions):
        path = f"{path_stem}.{actual_file_ext}"
        try:
            normalize_loudness(path, logger)
        except Exception as error:
            logger.debug("loudness normalization failed")
            raise error

    return actual_file_ext


def download_image(url: str, logger: Log) -> bytes | None:
    try:
        reply = requests.get(
            url, allow_redirects=True, headers=IMAGE_DOWNLOAD_HEADERS, timeout=60
        )
    except requests.RequestException:
        logger.error(
            f"Failed to retrieve {url}. The server may be down or your internet "
            "connection is currently unavailable."
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
    filename_stem: str,
    meta_tags: ImageMetaTags | None,
    details: SongDetails,
    pathname: str,
    kind: ImageKind,
    max_width: int | None,
) -> str | None:
    logger = get_logger(__file__, details.song_id)
    if not (url := _get_image_url(meta_tags, details, kind, logger)):
        return None
    if not (img_bytes := download_image(url, logger)):
        logger.error(f"#{str(kind).upper()}: file does not exist at url: {url}")
        return None

    if not filetype.is_image(img_bytes):
        logger.error(f"#{str(kind).upper()}: file at {url} is no image")
        return None

    fname = f"{filename_stem} [{kind.value}].jpg"
    path = os.path.join(pathname, fname)
    with open(path, "wb") as file:
        file.write(img_bytes)

    _process_image(meta_tags, max_width, path)
    return fname


def _get_image_url(
    meta_tags: ImageMetaTags | None, details: SongDetails, kind: ImageKind, logger: Log
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


def _process_image(
    meta_tags: ImageMetaTags | None, max_width: int | None, path: str
) -> None:
    processed = False
    with Image.open(path).convert("RGB") as image:
        if meta_tags and meta_tags.image_processing():
            processed = True
            if rotate := meta_tags.rotate:
                image = image.rotate(rotate, resample=Image.BICUBIC, expand=True)
            if crop := meta_tags.crop:
                image = image.crop((crop.left, crop.upper, crop.right, crop.lower))
            if resize := meta_tags.resize:
                image = image.resize(
                    (resize.width, resize.height), resample=Image.LANCZOS
                )
            if meta_tags.contrast == "auto":
                image = ImageOps.autocontrast(image, cutoff=5)
            elif meta_tags.contrast:
                image = ImageEnhance.Contrast(image).enhance(meta_tags.contrast)
        if max_width and max_width < image.width:
            processed = True
            height = round(image.height * max_width / image.width)
            image = image.resize((max_width, height), resample=Image.LANCZOS)

        if processed:
            image.save(path, "jpeg", quality=100, subsampling=0)
