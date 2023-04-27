"""Options for downloading songs."""

from dataclasses import dataclass
from pathlib import Path

from usdb_syncer import settings


@dataclass(frozen=True)
class TxtOptions:
    """Settings regarding the song txt file to be downloaded."""

    encoding: settings.Encoding
    newline: settings.Newline


@dataclass(frozen=True)
class AudioOptions:
    """Settings regarding the audio file to be downloaded."""

    format: settings.AudioFormat
    bitrate: settings.AudioBitrate
    normalize: bool
    embed_artwork: bool

    def ytdl_format(self) -> str:
        return self.format.ytdl_format()


@dataclass(frozen=True)
class VideoOptions:
    """Settings regarding the video file to be downloaded."""

    format: settings.VideoContainer
    reencode_format: settings.VideoCodec | None
    max_resolution: settings.VideoResolution
    max_fps: settings.VideoFps

    def ytdl_format(self) -> str:
        fmt = self.format.ytdl_format()
        width = f"[width<={self.max_resolution.width()}]"
        height = f"[height<={self.max_resolution.height()}]"
        fps = f"[fps<={self.max_fps.value}]"
        # fps filter always fails for some platforms, so skip it as a fallback
        return f"{fmt}{width}{height}{fps}/{fmt}{width}{height}"


@dataclass(frozen=True)
class CoverOptions:
    """Settings regarding the cover image to be downloaded."""

    max_size: int | None


@dataclass(frozen=True)
class BackgroundOptions:
    """Settings regarding the background image to be downloaded."""

    even_with_video: bool

    def download_background(self, has_video: bool) -> bool:
        return not has_video or self.even_with_video


@dataclass(frozen=True)
class Options:
    """Settings for downloading songs."""

    song_dir: Path
    txt_options: TxtOptions | None
    audio_options: AudioOptions | None
    browser: settings.Browser
    video_options: VideoOptions | None
    cover: CoverOptions | None
    background_options: BackgroundOptions | None


def download_options() -> Options:
    return Options(
        song_dir=settings.get_song_dir(),
        txt_options=_txt_options(),
        audio_options=_audio_options(),
        browser=settings.get_browser(),
        video_options=_video_options(),
        cover=_cover_options(),
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
        bitrate=settings.get_audio_bitrate(),
        normalize=settings.get_audio_normalize(),
        embed_artwork=settings.get_audio_embed_artwork(),
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


def _cover_options() -> CoverOptions | None:
    if not settings.get_cover():
        return None
    return CoverOptions(max_size=settings.get_cover_max_size() or None)


def _background_options() -> BackgroundOptions | None:
    if not settings.get_background():
        return None
    return BackgroundOptions(even_with_video=settings.get_background_always())
