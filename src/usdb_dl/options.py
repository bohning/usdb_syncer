"""Options for downloading songs."""

from dataclasses import dataclass


@dataclass
class TxtOptions:
    """Settings regarding the song txt file to be downloaded."""

    encoding: str
    line_endings: str


@dataclass
class AudioOptions:
    """Settings regarding the audio file to be downloaded."""

    format: str
    reencode_format: str | None


@dataclass
class VideoOptions:
    """Settings regarding the video file to be downloaded."""

    format: str
    reencode_format: str | None
    max_resolution: str
    max_fps: str

    def ytdl_format(self) -> str:
        if self.max_resolution == "1080p":
            max_width = 1920
            max_height = 1080
        else:
            max_width = 1280
            max_height = 720
        return (
            f"bestvideo[ext=mp4][width<={max_width}][height<={max_height}]"
            f"[fps<={self.max_fps}]"
        )


@dataclass
class BackgroundOptions:
    """Settings regarding the video file to be downloaded."""

    only_if_no_video: bool

    def download_background(self, has_video: bool) -> bool:
        return not self.only_if_no_video or not has_video


@dataclass
class Options:
    """Settings for downloading songs."""

    song_dir: str
    txt_options: TxtOptions | None
    audio_options: AudioOptions | None
    browser: str
    video_options: VideoOptions | None
    cover: bool
    background_options: BackgroundOptions | None
