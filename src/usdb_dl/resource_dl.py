import logging
import os

import requests
import yt_dlp
from PIL import Image, ImageEnhance, ImageOps

from usdb_dl import note_utils

# from moviepy.editor import VideoFileClip
# import subprocess


def download_and_process_audio(
    header, audio_resource, audio_dl_format, audio_target_codec, dl_browser, pathname
):
    if not audio_resource:
        logging.warning("\t- no audio resource in #VIDEO tag")
        return False, ""

    if "/" in audio_resource:
        audio_url = f"https://{audio_resource}"
    else:
        audio_url = f"https://www.youtube.com/watch?v={audio_resource}"

    logging.debug(f"\t- downloading audio from #VIDEO params: {audio_url}")

    audio_filename = os.path.join(pathname, note_utils.generate_filename(header))

    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": f"{audio_filename}" + ".%(ext)s",
        "keepvideo": False,
        "verbose": False,
    }

    if dl_browser != "none":
        ydl_opts["cookiesfrombrowser"] = (f"{dl_browser}",)

    ext = ""
    if audio_dl_format != "bestaudio":
        ext = audio_dl_format
        if not "/" in audio_resource:
            ydl_opts[
                "format"
            ] = f"bestaudio[ext={ext}]"  # ext only seems to work for Youtube
        else:
            ydl_opts["format"] = f"bestaudio"  # not for e.g. UM
            ydl_opts["outtmpl"] = f"{audio_filename}.m4a"

    if audio_target_codec:
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": f"{audio_target_codec}",
                "preferredquality": "320",
            }
        ]

        ext = audio_target_codec
        if audio_target_codec == "vorbis":
            ext = "ogg"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # ydl.download([video_url])
            filename = ydl.prepare_filename(ydl.extract_info(f"{audio_url}"))
        except:
            logging.error(f"\t#VIDEO: error downloading video url: {audio_url}")
            return False, ""

    if audio_dl_format == "bestaudio" and not audio_target_codec:
        ext = os.path.splitext(filename)[1][1:]

    return True, ext


def download_and_process_video(
    header, video_resource, video_params, resource_params, dl_browser, pathname
):
    if video_params["resolution"] == "1080p":
        video_max_width = 1920
        video_max_height = 1080
    else:
        video_max_width = 1280
        video_max_height = 720
    video_max_fps = video_params["fps"]
    video_target_container = video_params["container"]
    video_reencode_allow = video_params[
        "allow_reencode"
    ]  # True # if False, ffmpeg will not be used to trim or crop and subsequently reencode videos (uses US #START/#END tags)
    video_reencode_encoder = video_params[
        "encoder"
    ]  # "libx264" #"libvpx-vp9" #"libaom-av1" #"libx264"
    video_reencode_crf = (
        23  # 0–51 (0=lossless/huge file size, 23=default, 51=worst quality possible)
    )
    video_reencode_preset = "ultrafast"  # ultrafast, superfast, veryfast, faster, fast, medium (default preset), slow, slower, veryslow

    if "/" in video_resource:
        video_url = f"https://{video_resource}"
    else:
        video_url = f"https://www.youtube.com/watch?v={video_resource}"

    logging.debug(f"\t- downloading video from #VIDEO params: {video_url}")

    video_filename = os.path.join(pathname, note_utils.generate_filename(header))

    ydl_opts = {
        # "format":  f"bestvideo[ext=mp4][width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]+bestaudio[ext=m4a]/best[ext=mp4][width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]/best[width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]",
        "format": f"bestvideo[ext=mp4][width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]",
        # "format":  f"bestvideo[width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]+bestaudio",
        # "format":  f"bestvideo[width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]",
        # "outtmpl": os.path.join(dir, f"{artist} - {title}" + ".%(ext)s"),
        "outtmpl": f"{video_filename}" + ".%(ext)s",
        "keepvideo": False,
        "verbose": False,
    }

    if dl_browser != "none":
        ydl_opts["cookiesfrombrowser"] = (f"{dl_browser}",)

    if "/" in video_resource:  # not Youtube
        ydl_opts["format"] = f"bestvideo"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([video_url])
            vfn = ydl.prepare_filename(ydl.extract_info("{}".format(video_url)))
        except:
            logging.error(f"\t#VIDEO: error downloading video url: {video_url}")
            pass

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


def download_image(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"
        }
        reply = requests.get(url, allow_redirects=True, headers=headers)
    except:
        logging.error(
            f"Failed to retrieve {url}. The server may be down or your internet connection is currently unavailable."
        )
        return False, False
    else:
        if reply.status_code in range(100, 199):
            # 1xx informational response
            return True, reply.content
        elif reply.status_code in range(200, 299):
            # 2xx success
            return True, reply.content
        elif reply.status_code in range(300, 399):
            # 3xx redirection
            logging.warning(
                f"\tRedirection to {reply._next.url}. Please update the template file."
            )
            return True, reply.content
        elif reply.status_code in range(400, 499):
            # 4xx client errors
            logging.error(
                f"\tClient error {reply.status_code}. Failed to download {reply.url}"
            )
            return False, reply.content
        elif reply.status_code in range(500, 599):
            # 5xx server errors
            logging.error(
                f"\tServer error {reply.status_code}. Failed to download {reply.url}"
            )
            return False, reply.content


def download_and_process_cover(header, cover_params, details, pathname):
    if not cover_params.get("co") and not details.get("cover_url"):
        logging.warning("\t- no cover resource in #VIDEO tag and no cover in usdb")
        return

    cover_extension = ".jpg"
    cover_filename = note_utils.generate_filename(header) + f" [CO]{cover_extension}"

    if partial_url := cover_params.get("co"):
        protocol = "https://"
        if p := cover_params.get("co-protocol"):
            if p == "http":
                protocol = "http://"

        if "/" in cover_params["co"]:
            cover_url = f"{protocol}{partial_url}"
        else:
            cover_url = f"{protocol}images.fanart.tv/fanart/{partial_url}"
        logging.debug(f"\t- downloading cover from #VIDEO params: {cover_url}")
    else:
        logging.warning(
            f"\t- no cover resource in #VIDEO tag, so fallback to small usdb cover!"
        )
        cover_url = details.get("cover_url")

    success, cover = download_image(cover_url)

    if success:
        open(os.path.join(pathname, cover_filename), "wb").write(cover)

        if (
            cover_params.get("co-rotate")
            or cover_params.get("co-crop")
            or cover_params.get("co-resize")
            or cover_params.get("co-contrast")
        ):
            with Image.open(os.path.join(pathname, cover_filename)).convert(
                "RGB"
            ) as cover:
                # rotate (optional)
                angle = cover_params.get("co-rotate")
                if angle:
                    cover = cover.rotate(
                        float(angle), resample=Image.BICUBIC, expand=True
                    )

                # crop (optional)
                # TODO: ensure quadratic cover
                cover_crop = cover_params.get("co-crop")
                if cover_crop:
                    (
                        cover_crop_left,
                        cover_crop_upper,
                        cover_width,
                        cover_height,
                    ) = cover_crop.split("-")
                    cover_crop_right = int(cover_crop_left) + int(cover_width)
                    cover_crop_lower = int(cover_crop_upper) + int(cover_height)
                    cover = cover.crop(
                        (
                            int(cover_crop_left),
                            int(cover_crop_upper),
                            cover_crop_right,
                            cover_crop_lower,
                        )
                    )

                # resize (optional)
                cover_resize = cover_params.get("co-resize")
                if cover_resize:
                    width, height = cover_resize.split("-")
                    cover = cover.resize(
                        (int(width), int(height)), resample=Image.LANCZOS
                    )

                # increase contrast (optional)
                cover_contrast = cover_params.get("co-contrast")
                if cover_contrast:
                    if cover_contrast == "auto":
                        cover = ImageOps.autocontrast(cover, cutoff=5)
                    else:
                        cover = ImageEnhance.Contrast(cover).enhance(
                            float(cover_contrast)
                        )

                # save post-processed cover
                cover.save(
                    os.path.join(pathname, cover_filename),
                    "jpeg",
                    quality=100,
                    subsampling=0,
                )
        return True
    else:
        logging.error(f"\t#COVER: file does not exist at url: {cover_url}")
        return False


def download_and_process_background(header, background_params, pathname):
    if not background_params.get("bg"):
        logging.warning("\t- no background resource in #VIDEO-tag")
        return

    background_extension = ".jpg"

    background_filename = (
        note_utils.generate_filename(header) + f" [BG]{background_extension}"
    )

    protocol = "https://"
    if p := background_params.get("bg-protocol"):
        if p == "http":
            protocol = "http://"

    if "/" in background_params["bg"]:
        background_url = f"{protocol}{background_params['bg']}"
    else:
        background_url = f"{protocol}images.fanart.tv/fanart/{background_params['bg']}"

    logging.debug(f"\t- downloading background from #VIDEO params: {background_url}")

    success, background = download_image(background_url)

    if success:
        open(os.path.join(pathname, background_filename), "wb").write(background)

        if background_params.get("bg-crop") or background_params.get("bg-resize"):
            with Image.open(background_filename).convert("RGB") as background:
                # resize (optional)
                background_resize = background_params.get("bg-resize")
                if background_resize:
                    width, height = background_resize.split("-")
                    background = background.resize(
                        (int(width), int(height)), resample=Image.LANCZOS
                    )

                # crop (optional)
                background_crop = background_params.get("bg-crop")
                if background_crop:
                    (
                        background_crop_left,
                        background_crop_upper,
                        background_width,
                        background_height,
                    ) = background_crop.split("-")
                    background_crop_right = int(background_crop_left) + int(
                        background_width
                    )
                    background_crop_lower = int(background_crop_upper) + int(
                        background_height
                    )
                    background = background.crop(
                        (
                            int(background_crop_left),
                            int(background_crop_upper),
                            background_crop_right,
                            background_crop_lower,
                        )
                    )

                # save post-processed background
                background.save(background_filename, "jpeg", quality=100, subsampling=0)
        return True
    else:
        logging.error(f"\t#BACKGROUND: file does not exist at url: {background_url}")
        return False
