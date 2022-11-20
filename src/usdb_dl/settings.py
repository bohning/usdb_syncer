"""Persistent app settings.

To ensure consistent default values and avoid key collisions, QSettings should never be
used directly. Instead, new settings should be added to the SettingKey enum and setters
and getters should be added to this module.
"""

import os
from enum import Enum
from typing import Any, TypeVar, cast

from PySide6.QtCore import QSettings

from usdb_dl.typing_helpers import assert_never


class SettingKey(Enum):
    """Keys for storing and retrieving settings."""

    SONG_DIR = "song_dir"
    BROWSER = "downloads/browser"
    TXT = "downloads/txt"
    ENCODING = "downloads/encoding"
    NEWLINE = "downloads/newline"
    AUDIO = "downloads/audio"
    AUDIO_FORMAT = "downloads/audio_format"
    AUDIO_REENCODE = "downloads/audio_reencode"
    AUDIO_FORMAT_NEW = "downloads/audio_format_new"
    VIDEO = "downloads/video"
    VIDEO_FORMAT = "downloads/video_format"
    VIDEO_REENCODE = "downloads/video_reencode"
    VIDEO_FORMAT_NEW = "downloads/video_format_new"
    VIDEO_RESOLUTION_MAX = "downloads/video_resolution_max"
    VIDEO_FPS_MAX = "downloads/video_fps_max"
    COVER = "downloads/cover"
    COVER_MAX_SIZE = "downloads/cover_max_size"
    BACKGROUND = "downloads/background"
    BACKGROUND_ALWAYS = "downloads/background_always"


class Encoding(Enum):
    """Supported encodings for song txts."""

    UTF_8 = "utf_8"
    UTF_8_BOM = "utf_8_sig"
    CP1252 = "cp1252"

    def __str__(self) -> str:  # pylint: disable=invalid-str-returned
        match self:
            case Encoding.UTF_8:
                return "UTF-8"
            case Encoding.UTF_8_BOM:
                return "UTF-8 BOM"
            case Encoding.CP1252:
                return "CP1252"
            case _ as unreachable:
                assert_never(unreachable)


class Newline(Enum):
    """Supported line endings for song txts."""

    LF = "\n"
    CRLF = "\r\n"

    def __str__(self) -> str:  # pylint: disable=invalid-str-returned
        match self:
            case Newline.LF:
                return "Mac/Linux (LF)"
            case Newline.CRLF:
                return "Windows (CRLF)"
            case _ as unreachable:
                assert_never(unreachable)

    @staticmethod
    def default() -> "Newline":
        if os.linesep == Newline.CRLF.value:
            return Newline.CRLF
        return Newline.LF


class AudioContainer(Enum):
    """Audio containers that can be requested when downloading with ytdl."""

    M4A = "m4a"
    WEBM = "webm"
    BEST = "best"

    def __str__(self) -> str:  # pylint: disable=invalid-str-returned
        match self:
            case AudioContainer.M4A:
                return ".m4a (mp4a)"
            case AudioContainer.WEBM:
                return ".webm (opus)"
            case AudioContainer.BEST:
                return "Best available"
            case _ as unreachable:
                assert_never(unreachable)

    def ytdl_format(self) -> str:
        if self is AudioContainer.BEST:
            return "bestaudio"
        return f"bestaudio[ext={self.value}]"


class AudioCodec(Enum):
    """Audio codecs that ytdl can reencode downloaded videos to."""

    MP3 = "mp3"
    OGG = "ogg"
    OPUS = "opus"

    def __str__(self) -> str:  # pylint: disable=invalid-str-returned
        match self:
            case AudioCodec.MP3:
                return ".mp3 (MPEG)"
            case AudioCodec.OGG:
                return ".ogg (Vorbis)"
            case AudioCodec.OPUS:
                return ".opus (Opus)"
            case _ as unreachable:
                assert_never(unreachable)


class Browser(Enum):
    """Browsers to use cookies from."""

    NONE = None
    BRAVE = "brave"
    CHROME = "chrome"
    CHROMIUM = "chromium"
    EDGE = "edge"
    FIREFOX = "firefox"
    OPERA = "opera"
    SAFARI = "safari"
    VIVALDI = "vivaldi"

    def __str__(self) -> str:
        if self is Browser.NONE:
            return "None"
        return self.value.capitalize()

    def icon(self) -> str:
        match self:
            case Browser.NONE:
                return ""
            case Browser.BRAVE:
                return ":/icons/brave.png"
            case Browser.CHROME:
                return ":/icons/chrome.png"
            case Browser.CHROMIUM:
                return ":/icons/chromium.png"
            case Browser.EDGE:
                return ":/icons/edge.png"
            case Browser.FIREFOX:
                return ":/icons/firefox.png"
            case Browser.OPERA:
                return ":/icons/opera.png"
            case Browser.SAFARI:
                return ":/icons/safari.png"
            case Browser.VIVALDI:
                return ":/icons/vivaldi.png"
            case _ as unreachable:
                assert_never(unreachable)


class VideoContainer(Enum):
    """Video containers that can be requested when downloading with ytdl."""

    MP4 = "mp4"
    WEBM = "webm"
    BEST = "bestvideo"

    def __str__(self) -> str:  # pylint: disable=invalid-str-returned
        match self:
            case VideoContainer.MP4:
                return ".mp4"
            case VideoContainer.WEBM:
                return ".webm"
            case VideoContainer.BEST:
                return "Best available"
            case _ as unreachable:
                assert_never(unreachable)

    def ytdl_format(self) -> str:
        if self is VideoContainer.BEST:
            return "bestvideo"
        return f"bestvideo[ext={self.value}]"


class VideoCodec(Enum):
    """Video codecs that ytdl can reencode videos to."""

    H264 = "h264"
    H265 = "h265"
    LIBVPX = "libvpx-vp9"
    LIBAOM = "libaom-av1"

    def __str__(self) -> str:  # pylint: disable=invalid-str-returned
        match self:
            case VideoCodec.H264:
                return "h264"
            case VideoCodec.H265:
                return "h265"
            case VideoCodec.LIBVPX:
                return "libvpx-vp9"
            case VideoCodec.LIBAOM:
                return "libaom-av1"
            case _ as unreachable:
                assert_never(unreachable)


class VideoResolution(Enum):
    """Maximum video resolution."""

    _1080P = "1080p"
    _7200P = "720p"

    def __str__(self) -> str:
        return self.value

    def width(self) -> int:
        match self:
            case VideoResolution._1080P:
                return 1920
            case VideoResolution._7200P:
                return 1280
            case _ as unreachable:
                assert_never(unreachable)

    def height(self) -> int:
        match self:
            case VideoResolution._1080P:
                return 1080
            case VideoResolution._7200P:
                return 720
            case _ as unreachable:
                assert_never(unreachable)


class VideoFps(Enum):
    """Maximum frames per second."""

    _60 = 60
    _30 = 30

    def __str__(self) -> str:
        return str(self.value)


T = TypeVar("T")


def get_setting(key: SettingKey, default: T) -> T:
    value = QSettings().value(key.value)
    if isinstance(value, type(default)):
        return value
    if isinstance(default, bool) and isinstance(value, int):
        # we store bools as ints because Qt doesn't store raw bools
        return cast(T, bool(value))
    return default


def set_setting(key: SettingKey, value: Any) -> None:
    if isinstance(value, bool):
        # Qt stores bools as "true" and "false" otherwise
        value = int(value)
    QSettings().setValue(key.value, value)


def get_audio() -> bool:
    return get_setting(SettingKey.AUDIO, True)


def set_audio(value: bool) -> None:
    set_setting(SettingKey.AUDIO, value)


def get_audio_format() -> AudioContainer:
    return get_setting(SettingKey.AUDIO_FORMAT, AudioContainer.M4A)


def set_audio_format(value: AudioContainer) -> None:
    set_setting(SettingKey.AUDIO_FORMAT, value)


def get_audio_format_new() -> AudioCodec:
    return get_setting(SettingKey.AUDIO_FORMAT_NEW, AudioCodec.MP3)


def set_audio_format_new(value: AudioCodec) -> None:
    set_setting(SettingKey.AUDIO_FORMAT_NEW, value)


def get_audio_reencode() -> bool:
    return get_setting(SettingKey.AUDIO_REENCODE, False)


def set_audio_reencode(value: bool) -> None:
    set_setting(SettingKey.AUDIO_REENCODE, value)


def get_newline() -> Newline:
    return get_setting(SettingKey.NEWLINE, Newline.default())


def set_newline(value: Newline) -> None:
    set_setting(SettingKey.NEWLINE, value)


def get_encoding() -> Encoding:
    return get_setting(SettingKey.ENCODING, Encoding.UTF_8)


def set_encoding(value: Encoding) -> None:
    set_setting(SettingKey.ENCODING, value)


def get_txt() -> bool:
    return get_setting(SettingKey.TXT, True)


def set_txt(value: bool) -> None:
    set_setting(SettingKey.TXT, value)


def get_cover() -> bool:
    return get_setting(SettingKey.COVER, True)


def set_cover(value: bool) -> None:
    set_setting(SettingKey.COVER, value)


def get_cover_max_size() -> int:
    return get_setting(SettingKey.COVER_MAX_SIZE, 1920)


def set_cover_max_size(value: int) -> None:
    set_setting(SettingKey.COVER_MAX_SIZE, value)


def get_browser() -> Browser:
    return get_setting(SettingKey.BROWSER, Browser.NONE)


def set_browser(value: Browser) -> None:
    set_setting(SettingKey.BROWSER, value)


def get_song_dir() -> str:
    return get_setting(SettingKey.SONG_DIR, os.path.join(os.getcwd(), "songs"))


def set_song_dir(value: str) -> None:
    set_setting(SettingKey.SONG_DIR, os.path.join(os.getcwd(), value))


def get_video() -> bool:
    return get_setting(SettingKey.VIDEO, True)


def set_video(value: bool) -> None:
    set_setting(SettingKey.VIDEO, value)


def get_video_format() -> VideoContainer:
    return get_setting(SettingKey.VIDEO_FORMAT, VideoContainer.MP4)


def set_video_format(value: VideoContainer) -> None:
    set_setting(SettingKey.VIDEO_FORMAT, value)


def get_video_reencode() -> bool:
    return get_setting(SettingKey.VIDEO_REENCODE, False)


def set_video_reencode(value: bool) -> None:
    set_setting(SettingKey.VIDEO_REENCODE, value)


def get_video_format_new() -> VideoCodec:
    return get_setting(SettingKey.VIDEO_FORMAT_NEW, VideoCodec.H264)


def set_video_format_new(value: VideoCodec) -> None:
    set_setting(SettingKey.VIDEO_FORMAT_NEW, value)


def get_video_resolution() -> VideoResolution:
    return get_setting(
        SettingKey.VIDEO_RESOLUTION_MAX,
        VideoResolution._1080P,  # pylint: disable=protected-access
    )


def set_video_resolution(value: VideoResolution) -> None:
    set_setting(SettingKey.VIDEO_RESOLUTION_MAX, value)


def get_video_fps() -> VideoFps:
    return get_setting(
        SettingKey.VIDEO_FPS_MAX, VideoFps._60  # pylint: disable=protected-access
    )


def set_video_fps(value: VideoFps) -> None:
    set_setting(SettingKey.VIDEO_FPS_MAX, value)


def get_background() -> bool:
    return get_setting(SettingKey.BACKGROUND, True)


def set_background(value: bool) -> None:
    set_setting(SettingKey.BACKGROUND, value)


def get_background_always() -> bool:
    return get_setting(SettingKey.BACKGROUND_ALWAYS, True)


def set_background_always(value: bool) -> None:
    set_setting(SettingKey.BACKGROUND_ALWAYS, value)