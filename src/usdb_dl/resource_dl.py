"""Functions for downloading and processing media."""

import logging
import os
from enum import Enum
from typing import Union

import requests
import yt_dlp
from PIL import Image, ImageEnhance, ImageOps

from usdb_dl import note_utils
from usdb_dl.meta_tags import ImageMetaTags
from usdb_dl.options import AudioOptions, Browser, VideoOptions
from usdb_dl.typing_helpers import assert_never
from usdb_dl.usdb_scraper import SongDetails

# from moviepy.editor import VideoFileClip
# import subprocess


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


def download_and_process_audio(
    header: dict[str, str],
    audio_resource: str,
    audio_options: AudioOptions,
    browser: Browser,
    pathname: str,
) -> tuple[bool, str]:
    if not audio_resource:
        logging.warning("\t- no audio resource in #VIDEO tag")
        return False, ""
    if "/" in audio_resource:
        logging.warning("\t- only YouTube videos are currently supported")
        return False, ""

    audio_url = f"https://www.youtube.com/watch?v={audio_resource}"

    logging.debug(f"\t- downloading audio from #VIDEO params: {audio_url}")

    audio_filename = os.path.join(pathname, note_utils.generate_filename(header))

    ydl_opts: dict[str, Union[str, bool, tuple, list]] = {
        "format": audio_options.format.ytdl_format(),
        "outtmpl": f"{audio_filename}.%(ext)s",
        "keepvideo": False,
        "verbose": False,
    }
    if browser.value:
        ydl_opts["cookiesfrombrowser"] = (browser.value,)
    if audio_options.reencode_format:
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_options.reencode_format.value,
                "preferredquality": "320",
            }
        ]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # ydl.download([video_url])
            filename = ydl.prepare_filename(ydl.extract_info(f"{audio_url}"))
        except:
            logging.error(f"\t#VIDEO: error downloading video url: {audio_url}")
            return False, ""

    ext = audio_options.extension() or os.path.splitext(filename)[1][1:]

    return True, ext


def download_and_process_video(
    header: dict[str, str],
    video_resource: str,
    video_options: VideoOptions,
    browser: Browser,
    pathname: str,
) -> bool:
    # _video_target_container = video_options["container"]
    # _video_reencode_allow = video_options[
    #    "allow_reencode"
    # ]  # True # if False, ffmpeg will not be used to trim or crop and subsequently reencode videos (uses US #START/#END tags)
    # _video_reencode_encoder = video_options[
    #    "encoder"
    # ]  # "libx264" #"libvpx-vp9" #"libaom-av1" #"libx264"
    # _video_reencode_crf = (
    #    23  # 0–51 (0=lossless/huge file size, 23=default, 51=worst quality possible)
    # )
    # _video_reencode_preset = "ultrafast"  # ultrafast, superfast, veryfast, faster, fast, medium (default preset), slow, slower, veryslow

    if "/" in video_resource:
        logging.warning("\t- only YouTube videos are currently supported")
        return False

    video_url = f"https://www.youtube.com/watch?v={video_resource}"

    logging.debug(f"\t- downloading video from #VIDEO params: {video_url}")

    video_filename = os.path.join(pathname, note_utils.generate_filename(header))

    ydl_opts = {
        # "format":  f"bestvideo[ext=mp4][width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]+bestaudio[ext=m4a]/best[ext=mp4][width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]/best[width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]",
        "format": video_options.ytdl_format(),
        # "format":  f"bestvideo[width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]+bestaudio",
        # "format":  f"bestvideo[width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]",
        # "outtmpl": os.path.join(dir, f"{artist} - {title}" + ".%(ext)s"),
        "outtmpl": f"{video_filename}" + ".%(ext)s",
        "keepvideo": False,
        "verbose": False,
    }

    if browser.value:
        ydl_opts["cookiesfrombrowser"] = (browser.value,)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([video_url])
            _vfn = ydl.prepare_filename(ydl.extract_info(video_url))
        except:
            logging.error(f"\t#VIDEO: error downloading video url: {video_url}")

    ######

    # Trim
    """ trim = resource_params.get("v-trim")
    start_time = None
    end_time = None
    if trim:
        start_time, end_time = trim.split("-")
        framerate = VideoFileClip(vfn).subclip(0, 10).fps
        
        if ":" in start_time:
            hours, minutes, seconds = start_time.split(":")
            start_time = int(hours)*3600 + int(minutes)*60 + float(seconds)
        elif "." in start_time:
            pass
        elif start_time == "":
            pass
        else:
            start_time = round(float(start_time) / framerate, 3)
        
        if ":" in end_time:
            hours, minutes, seconds = end_time.split(":")
            end_time = int(hours)*3600 + int(minutes)*60 + float(seconds)
        elif "." in end_time:
            pass
        elif end_time == "":
            pass
        else:
            end_time = round(float(end_time) / framerate, 3)
            
        logging.info(f"\t- video: trimming video from {start_time} to {end_time}")

    # Crop
    crop = resource_params.get("v-crop")

    if trim or crop:
        if video_reencode_allow:
            dst = vfn
            src = vfn.replace(".", "_unprocessed.")
            os.rename(dst, src)
            
            logging.info("\t\tFFMPEG postprocessing required...")    
            
            ffmpeg_trim_crop_cmd = "ffmpeg"

            if trim:
                if start_time:
                    ffmpeg_trim_crop_cmd += " -ss " + str(start_time)
                if end_time:
                    ffmpeg_trim_crop_cmd += " -to " + str(end_time)

            ffmpeg_trim_crop_cmd += " -i \"" + src + "\""

            if crop:
                left, right, top, bottom = crop.split("-")
                ffmpeg_trim_crop_cmd += f" -vf \"crop=iw-{left}-{right}:ih-{top}-{bottom}:{left}:{top}\""

            #ffmpeg_trim_crop_cmd += f" -c:v {video_reencode_encoder} -crf {video_reencode_crf} -preset {video_reencode_preset} -c:a copy \"" + dst + "\""
            ffmpeg_trim_crop_cmd += f" -c:v {video_reencode_encoder} -threads 4 -crf {video_reencode_crf} -preset {video_reencode_preset} -c:a copy \"" + dst + "\""
            logging.info(ffmpeg_trim_crop_cmd)
            logging.info("\tprocessing video file...")
            subprocess.run(ffmpeg_trim_crop_cmd, shell=True, check=True)
            logging.info("\tprocessing video file finished!")
            os.remove(src)
            # reduce #GAP by trimmed part 
            header["#GAP"] = str(int(float(header["#GAP"]) - float(start_time) * 1000))
        else:
            logging.info("\t- video: trim/crop required, but disabled.")
            if trim:
                logging.info("\t- video: trimming required, but reencode is disabled. Using appropriate #START tag to fix this.")
                if start_time:
                    header["#START"] = str(start_time) # # START is in seconds!
            if crop:
                logging.info("\t- video: cropping required, but reencode is disabled. Black bars will not be cropped.") """

    ######

    # TODO: check if download was successful, only then return True
    return True


def download_image(url: str) -> tuple[bool, bytes]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"
        }
        reply = requests.get(url, allow_redirects=True, headers=headers, timeout=60)
    except:
        logging.error(
            f"Failed to retrieve {url}. The server may be down or your internet connection is currently unavailable."
        )
        return False, bytes(0)
    if reply.status_code in range(100, 199):
        # 1xx informational response
        return True, reply.content
    if reply.status_code in range(200, 299):
        # 2xx success
        return True, reply.content
    if reply.status_code in range(300, 399):
        # 3xx redirection
        logging.warning(
            f"\tRedirection to {reply.next.url if reply.next else 'unknown'}. Please update the template file."
        )
        return True, reply.content
    if reply.status_code in range(400, 499):
        # 4xx client errors
        logging.error(
            f"\tClient error {reply.status_code}. Failed to download {reply.url}"
        )
        return False, reply.content
    if reply.status_code in range(500, 599):
        # 5xx server errors
        logging.error(
            f"\tServer error {reply.status_code}. Failed to download {reply.url}"
        )
        return False, reply.content
    return False, bytes(0)


def download_and_process_image(
    header: dict[str, str],
    meta_tags: ImageMetaTags | None,
    details: SongDetails,
    pathname: str,
    kind: ImageKind,
) -> bool:
    if not (url := _get_image_url(meta_tags, details, kind)):
        return False
    success, img_bytes = download_image(url)
    if not success:
        logging.error(f"\t#{str(kind).upper()}: file does not exist at url: {url}")
        return False
    fname = f"{note_utils.generate_filename(header)} [{kind.value}].jpg"
    path = os.path.join(pathname, fname)
    with open(path, "wb") as file:
        file.write(img_bytes)
    if meta_tags and meta_tags.image_processing():
        _process_image(meta_tags, path)
    return True


def _get_image_url(
    meta_tags: ImageMetaTags | None, details: SongDetails, kind: ImageKind
) -> str | None:
    url = None
    if meta_tags:
        url = meta_tags.source_url()
        logging.debug(f"\t- downloading {kind} from #VIDEO params: {url}")
    elif kind is ImageKind.COVER and details.cover_url:
        url = details.cover_url
        logging.warning(
            "\t- no cover resource in #VIDEO tag, so fallback to small usdb cover!"
        )
    else:
        logging.warning(f"\t- no {kind} resource found")
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
