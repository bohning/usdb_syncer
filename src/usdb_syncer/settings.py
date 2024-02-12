"""Persistent app settings.

To ensure consistent default values and avoid key collisions, QSettings should never be
used directly. Instead, new settings should be added to the SettingKey enum and setters
and getters should be added to this module.
"""

from __future__ import annotations

import os
import traceback
from enum import Enum
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, Tuple, TypeVar, assert_never, cast

import browser_cookie3
import keyring
from PySide6.QtCore import QByteArray, QSettings

from usdb_syncer.constants import Usdb
from usdb_syncer.logger import get_logger

_logger = get_logger(__file__)

SYSTEM_USDB = "USDB Syncer/USDB"
NO_KEYRING_BACKEND_WARNING = (
    "Your USDB password cannot be stored or retrieved because no keyring backend is "
    "available. See https://pypi.org/project/keyring for details."
)


def get_usdb_auth() -> Tuple[str, str]:
    username = get_setting(SettingKey.USDB_USER_NAME, "")
    pwd = ""
    try:
        pwd = keyring.get_password(SYSTEM_USDB, username) or ""
    except keyring.core.backend.errors.NoKeyringError as error:
        _logger.debug(error)
        _logger.warning(NO_KEYRING_BACKEND_WARNING)
    return (username, pwd)


def set_usdb_auth(username: str, password: str) -> None:
    set_setting(SettingKey.USDB_USER_NAME, username)
    try:
        keyring.set_password(SYSTEM_USDB, username, password)
    except keyring.core.backend.errors.NoKeyringError as error:
        _logger.debug(error)
        _logger.warning(NO_KEYRING_BACKEND_WARNING)


class SettingKey(Enum):
    """Keys for storing and retrieving settings."""

    SONG_DIR = "song_dir"
    FFMPEG_DIR = "ffmpeg_dir"
    BROWSER = "downloads/browser"
    TXT = "downloads/txt"
    ENCODING = "downloads/encoding"
    NEWLINE = "downloads/newline"
    AUDIO = "downloads/audio"
    AUDIO_FORMAT = "downloads/audio_format"
    AUDIO_BITRATE = "downloads/audio_bitrate"
    AUDIO_NORMALIZE = "downloads/audio_normalize"
    AUDIO_EMBED_ARTWORK = "downloads/audio_embed_artwork"
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
    MAIN_WINDOW_GEOMETRY = "geometry/main_window"
    DOCK_LOG_GEOMETRY = "geometry/dock_log"
    MAIN_WINDOW_STATE = "state/main_window"
    TABLE_VIEW_HEADER_STATE = "list_view/header/state"
    USDB_USER_NAME = "usdb/username"


class Encoding(Enum):
    """Supported encodings for song txts."""

    UTF_8 = "utf_8"
    UTF_8_BOM = "utf_8_sig"
    CP1252 = "cp1252"

    def __str__(self) -> str:
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

    def __str__(self) -> str:
        match self:
            case Newline.LF:
                return "Mac/Linux (LF)"
            case Newline.CRLF:
                return "Windows (CRLF)"
            case _ as unreachable:
                assert_never(unreachable)

    @staticmethod
    def default() -> Newline:
        if os.linesep == Newline.CRLF.value:
            return Newline.CRLF
        return Newline.LF


class CoverMaxSize(Enum):
    """Maximum cover size."""

    PX_3840 = 3840
    PX_1920 = 1920
    PX_1200 = 1200
    PX_1000 = 1000
    PX_640 = 640
    PX_500 = 500

    def __str__(self) -> str:
        match self:
            case CoverMaxSize.PX_3840:
                return "3840x3840 px"
            case CoverMaxSize.PX_1920:
                return "1920x1920 px"
            case CoverMaxSize.PX_1200:
                return "1200x1200 px"
            case CoverMaxSize.PX_1000:
                return "1000x1000 px"
            case CoverMaxSize.PX_640:
                return "640x640 px"
            case CoverMaxSize.PX_500:
                return "500x500 px"
            case _ as unreachable:
                assert_never(unreachable)


class AudioFormat(Enum):
    """Audio containers that can be requested when downloading with ytdl."""

    M4A = "m4a"
    MP3 = "mp3"
    OGG = "ogg"
    OPUS = "opus"

    def __str__(self) -> str:
        match self:
            case AudioFormat.M4A:
                return ".m4a (mp4a)"
            case AudioFormat.MP3:
                return ".mp3 (MPEG)"
            case AudioFormat.OGG:
                return ".ogg (Ogg Vorbis)"
            case AudioFormat.OPUS:
                return ".opus (Ogg Opus)"
            case _ as unreachable:
                assert_never(unreachable)

    def ytdl_format(self) -> str:
        # prefer best audio-only codec; otherwise take a video codec and extract later
        return f"bestaudio[ext={self.value}]/bestaudio/bestaudio*"

    def ytdl_codec(self) -> str:
        match self:
            case AudioFormat.M4A:
                return "m4a"
            case AudioFormat.MP3:
                return "mp3"
            case AudioFormat.OGG:
                return "vorbis"
            case AudioFormat.OPUS:
                return "opus"
            case _ as unreachable:
                assert_never(unreachable)

    def ffmpeg_encoder(self) -> str:
        match self:
            case AudioFormat.M4A:
                return "aac"
            case AudioFormat.MP3:
                return "libmp3lame"
            case AudioFormat.OGG:
                return "libvorbis"
            case AudioFormat.OPUS:
                return "libopus"
            case _ as unreachable:
                assert_never(unreachable)


class AudioBitrate(Enum):
    """Audio bitrate."""

    KBPS_128 = "128 kbps"
    KBPS_160 = "160 kbps"
    KBPS_192 = "192 kbps"
    KBPS_256 = "256 kbps"
    KBPS_320 = "320 kbps"

    def __str__(self) -> str:
        return self.value

    def ytdl_format(self) -> str:
        return self.value.removesuffix(" kbps")

    def ffmpeg_format(self) -> int:
        return int(self.value.removesuffix(" kbps")) * 1000  # in bits/s


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

    def cookies(self) -> CookieJar | None:
        match self:
            case Browser.NONE:
                return None
            case Browser.BRAVE:
                function = browser_cookie3.brave
            case Browser.CHROME:
                function = browser_cookie3.chrome
            case Browser.CHROMIUM:
                function = browser_cookie3.chromium
            case Browser.EDGE:
                function = browser_cookie3.edge
            case Browser.FIREFOX:
                function = browser_cookie3.firefox
            case Browser.OPERA:
                function = browser_cookie3.opera
            case Browser.SAFARI:
                function = browser_cookie3.safari
            case Browser.VIVALDI:
                function = browser_cookie3.vivaldi
            case _ as unreachable:
                assert_never(unreachable)
        try:
            return function(domain_name=Usdb.DOMAIN)
        except Exception:  # pylint: disable=broad-exception-caught
            _logger.debug(traceback.format_exc())
        _logger.warning(f"Failed to retrieve {str(self).capitalize()} cookies.")
        return None

    def cookie_path(self) -> str | None:
        """Retrieve the path to the cookie as returned by browser_cookie3. This seems to
        be more reliable than yt-dlp's cookie handling."""
        try:
            match self:
                case Browser.NONE:
                    path = None
                case Browser.BRAVE:
                    path = browser_cookie3.Brave().cookie_file
                case Browser.CHROME:
                    path = browser_cookie3.Chrome().cookie_file
                case Browser.CHROMIUM:
                    path = browser_cookie3.Chromium().cookie_file
                case Browser.EDGE:
                    path = browser_cookie3.Edge().cookie_file
                case Browser.FIREFOX:
                    path = browser_cookie3.Firefox().cookie_file
                case Browser.OPERA:
                    path = browser_cookie3.Opera().cookie_file
                case Browser.SAFARI:
                    safari = browser_cookie3.Safari()
                    buf = safari.__buffer  # pylint: disable=protected-access
                    path = buf.name if buf else None
                case Browser.VIVALDI:
                    path = browser_cookie3.Vivaldi().cookie_file
                case _ as unreachable:
                    assert_never(unreachable)
        except Exception:  # pylint: disable=broad-exception-caught
            _logger.debug(traceback.format_exc())
            path = None
        return path


class VideoContainer(Enum):
    """Video containers that can be requested when downloading with ytdl."""

    MP4 = "mp4"
    WEBM = "webm"
    BEST = "bestvideo"

    def __str__(self) -> str:
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
            return "bestvideo*"
        return f"bestvideo*[ext={self.value}]"


class VideoCodec(Enum):
    """Video codecs that ytdl can reencode videos to."""

    H264 = "h264"
    H265 = "h265"
    LIBVPX = "libvpx-vp9"
    LIBAOM = "libaom-av1"

    def __str__(self) -> str:
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

    P2160 = "2160p"
    P1440 = "1440p"
    P1080 = "1080p"
    P720 = "720p"
    P480 = "480p"
    P360 = "360p"

    def __str__(self) -> str:
        return self.value

    def width(self) -> int:
        match self:
            case VideoResolution.P2160:
                return 3840
            case VideoResolution.P1440:
                return 2560
            case VideoResolution.P1080:
                return 1920
            case VideoResolution.P720:
                return 1280
            case VideoResolution.P480:
                return 854
            case VideoResolution.P360:
                return 640
            case _ as unreachable:
                assert_never(unreachable)

    def height(self) -> int:
        match self:
            case VideoResolution.P2160:
                return 2160
            case VideoResolution.P1440:
                return 1440
            case VideoResolution.P1080:
                return 1080
            case VideoResolution.P720:
                return 720
            case VideoResolution.P480:
                return 480
            case VideoResolution.P360:
                return 360
            case _ as unreachable:
                assert_never(unreachable)


class VideoFps(Enum):
    """Maximum frames per second."""

    FPS_60 = 60
    FPS_30 = 30

    def __str__(self) -> str:
        return str(self.value)


T = TypeVar("T")


def get_setting(key: SettingKey, default: T) -> T:
    try:
        value = QSettings().value(key.value)
    except (AttributeError, ValueError):
        # setting contains a type incompatible with this version
        return default
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


def get_audio_format() -> AudioFormat:
    return get_setting(SettingKey.AUDIO_FORMAT, AudioFormat.M4A)


def set_audio_format(value: AudioFormat) -> None:
    set_setting(SettingKey.AUDIO_FORMAT, value)


def get_audio_bitrate() -> AudioBitrate:
    return get_setting(SettingKey.AUDIO_BITRATE, AudioBitrate.KBPS_256)


def set_audio_bitrate(value: AudioBitrate) -> None:
    set_setting(SettingKey.AUDIO_BITRATE, value)


def get_audio_normalize() -> bool:
    return get_setting(SettingKey.AUDIO_NORMALIZE, False)


def set_audio_normalize(value: bool) -> None:
    set_setting(SettingKey.AUDIO_NORMALIZE, value)


def get_audio_embed_artwork() -> bool:
    return get_setting(SettingKey.AUDIO_EMBED_ARTWORK, False)


def set_audio_embed_artwork(value: bool) -> None:
    set_setting(SettingKey.AUDIO_EMBED_ARTWORK, value)


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


def get_cover_max_size() -> CoverMaxSize:
    return get_setting(SettingKey.COVER_MAX_SIZE, CoverMaxSize.PX_1920)


def set_cover_max_size(value: CoverMaxSize) -> None:
    set_setting(SettingKey.COVER_MAX_SIZE, value)


def get_browser() -> Browser:
    return get_setting(SettingKey.BROWSER, Browser.CHROME)


def set_browser(value: Browser) -> None:
    set_setting(SettingKey.BROWSER, value)


def get_song_dir() -> Path:
    return get_setting(SettingKey.SONG_DIR, Path("songs").resolve())


def set_song_dir(value: Path) -> None:
    set_setting(SettingKey.SONG_DIR, value)


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
    return get_setting(SettingKey.VIDEO_RESOLUTION_MAX, VideoResolution.P1080)


def set_video_resolution(value: VideoResolution) -> None:
    set_setting(SettingKey.VIDEO_RESOLUTION_MAX, value)


def get_video_fps() -> VideoFps:
    return get_setting(SettingKey.VIDEO_FPS_MAX, VideoFps.FPS_60)


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


def get_ffmpeg_dir() -> str:
    return get_setting(SettingKey.FFMPEG_DIR, "")


def set_ffmpeg_dir(value: str) -> None:
    set_setting(SettingKey.FFMPEG_DIR, value)


def get_geometry_main_window() -> QByteArray:
    return get_setting(SettingKey.MAIN_WINDOW_GEOMETRY, QByteArray())


def set_geometry_main_window(geometry: QByteArray) -> None:
    set_setting(SettingKey.MAIN_WINDOW_GEOMETRY, geometry)


def get_state_main_window() -> QByteArray:
    return get_setting(SettingKey.MAIN_WINDOW_STATE, QByteArray())


def set_state_main_window(state: QByteArray) -> None:
    set_setting(SettingKey.MAIN_WINDOW_STATE, state)


def get_geometry_log_dock() -> QByteArray:
    return get_setting(SettingKey.DOCK_LOG_GEOMETRY, QByteArray())


def set_geometry_log_dock(state: QByteArray) -> None:
    set_setting(SettingKey.DOCK_LOG_GEOMETRY, state)


def get_table_view_header_state() -> QByteArray:
    return get_setting(SettingKey.TABLE_VIEW_HEADER_STATE, QByteArray())


def set_table_view_header_state(state: QByteArray) -> None:
    set_setting(SettingKey.TABLE_VIEW_HEADER_STATE, state)
