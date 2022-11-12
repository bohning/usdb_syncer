"""Options for downloading songs."""

from dataclasses import dataclass

from usdb_dl import settings


@dataclass
class TxtOptions:
    """Settings regarding the song txt file to be downloaded."""

    encoding: settings.Encoding
    newline: settings.Newline


@dataclass
class AudioOptions:
    """Settings regarding the audio file to be downloaded."""

    format: settings.AudioContainer
    reencode_format: settings.AudioCodec | None

    def extension(self) -> str | None:
        """The extension of the downloaded file. Unknown if 'bestaudio' is selected and
        not target codec is set.
        """
        if self.reencode_format:
            return self.reencode_format.value
        if self.format is settings.AudioContainer.BEST:
            return None
        return self.format.value

    def ytdl_format(self) -> str:
        return self.format.ytdl_format()


@dataclass
class VideoOptions:
    """Settings regarding the video file to be downloaded."""

    format: settings.VideoContainer
    reencode_format: settings.VideoCodec | None
    max_resolution: settings.VideoResolution
    max_fps: settings.VideoFps

    def ytdl_format(self) -> str:
        return (
            f"{self.format.ytdl_format()}[width<={self.max_resolution.width()}]"
            f"[height<={self.max_resolution.height()}][fps<={self.max_fps.value}]"
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
    browser: settings.Browser
    video_options: VideoOptions | None
    cover: bool
    background_options: BackgroundOptions | None


def download_options() -> Options:
    return Options(
        song_dir=settings.get_song_dir(),
        txt_options=_txt_options(),
        audio_options=_audio_options(),
        browser=settings.get_browser(),
        video_options=_video_options(),
        cover=settings.get_cover(),
        background_options=_background_options(),
    )


def _txt_options() -> TxtOptions | None:
    if not settings.get_txt():
        return None
    return TxtOptions(encoding=settings.get_encoding(), newline=settings.get_newline())


def _audio_options() -> AudioOptions | None:
    if not settings.get_audio():
        return None
    return AudioOptions(
        format=settings.get_audio_format(),
        reencode_format=settings.get_audio_format_new()
        if settings.get_audio_reencode()
        else None,
    )


def _video_options() -> VideoOptions | None:
    if not settings.get_video():
        return None
    return VideoOptions(
        format=settings.get_video_format(),
        reencode_format=settings.get_video_format_new()
        if settings.get_video_reencode()
        else None,
        max_resolution=settings.get_video_resolution(),
        max_fps=settings.get_video_fps(),
    )


def _background_options() -> BackgroundOptions | None:
    if not settings.get_background():
        return None
    return BackgroundOptions(only_if_no_video=settings.get_background_always())
