"""Persistent app settings.

To ensure consistent default values and avoid key collisions, QSettings should never be
used directly. Instead, new settings should be added to the SettingKey enum and setters
and getters should be added to this module.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import traceback
from enum import Enum, StrEnum, auto
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, TypeVar, assert_never, cast

import rookiepy
from PySide6.QtCore import QByteArray, QSettings

from usdb_syncer import constants, path_template, utils
from usdb_syncer.logger import logger


def ffmpeg_is_available() -> bool:
    if shutil.which("ffmpeg"):
        return True
    if (path := get_ffmpeg_dir()) and path not in os.environ["PATH"]:
        # first run; restore path from settings
        utils.add_to_system_path(path)
        if shutil.which("ffmpeg"):
            return True
    return False


class SettingKey(Enum):
    """Keys for storing and retrieving settings."""

    SONG_DIR = "song_dir"
    FFMPEG_DIR = "ffmpeg_dir"
    BROWSER = "downloads/browser"
    COOKIES_FROM_BROWSER = "cookies_from_browser"
    TXT = "downloads/txt"
    ENCODING = "downloads/encoding"
    NEWLINE = "downloads/newline"
    FORMAT_VERSION = "downloads/format_version"
    FIX_LINEBREAKS = "fixes/linebreaks"
    FIX_FIRST_WORDS_CAPITALIZATION = "fixes/firstwordscapitalization"
    FIX_SPACES = "fixes/spaces"
    FIX_QUOTATION_MARKS = "fixes/quotation_marks"
    THROTTLING_THREADS = "downloads/throttling_threads"
    YTDLP_RATE_LIMIT = "downloads/ytdlp_rate_limit"
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
    VIDEO_EMBED_ARTWORK = "downloads/video_embed_artwork"
    COVER = "downloads/cover"
    COVER_MAX_SIZE = "downloads/cover_max_size"
    BACKGROUND = "downloads/background"
    BACKGROUND_ALWAYS = "downloads/background_always"
    MAIN_WINDOW_GEOMETRY = "geometry/main_window"
    DOCK_LOG_GEOMETRY = "geometry/dock_log"
    MAIN_WINDOW_STATE = "state/main_window"
    TABLE_VIEW_HEADER_STATE = "list_view/header/state"
    USDB_USER_NAME = "usdb/username"
    PATH_TEMPLATE = "files/path_template"
    APP_PATH_KAREDI = "app_paths/karedi"
    APP_PATH_PERFORMOUS = "app_paths/performous"
    APP_PATH_ULTRASTAR_MANAGER = "app_paths/ultrastar_manager"
    APP_PATH_USDX = "app_paths/usdx"
    APP_PATH_VOCALUXE = "app_paths/vocaluxe"
    APP_PATH_YASS_RELOADED = "app_paths/yass_reloaded"


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
                return "UTF-8 BOM (legacy support for older Vocaluxe versions)"
            case Encoding.CP1252:
                return "CP1252 (legacy support for older USDX CMD)"
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


class FormatVersion(Enum):
    """Supported format versions for song txts."""

    V1_0_0 = "1.0.0"
    V1_1_0 = "1.1.0"
    V1_2_0 = "1.2.0"

    def __str__(self) -> str:
        return str(self.value)


class FixLinebreaks(Enum):
    """Supported variants for fixing linebreak timings."""

    DISABLE = 0
    USDX_STYLE = 1
    YASS_STYLE = 2

    def __str__(self) -> str:
        match self:
            case FixLinebreaks.DISABLE:
                return "disable"
            case FixLinebreaks.USDX_STYLE:
                return "USDX style"
            case FixLinebreaks.YASS_STYLE:
                return "YASS style"
            case _ as unreachable:
                assert_never(unreachable)


class FixSpaces(Enum):
    """Supported variants for fixing spaces."""

    DISABLE = 0
    AFTER = 1
    BEFORE = 2

    def __str__(self) -> str:
        match self:
            case FixSpaces.DISABLE:
                return "disable"
            case FixSpaces.AFTER:
                return "after words"
            case FixSpaces.BEFORE:
                return "before words"
            case _ as unreachable:
                assert_never(unreachable)


class CoverMaxSize(Enum):
    """Maximum cover size."""

    DISABLE = 0
    PX_1920 = 1920
    PX_1000 = 1000
    PX_640 = 640

    def __str__(self) -> str:
        match self:
            case CoverMaxSize.DISABLE:
                return "disable"
            case CoverMaxSize.PX_1920:
                return "1920x1920 px"
            case CoverMaxSize.PX_1000:
                return "1000x1000 px"
            case CoverMaxSize.PX_640:
                return "640x640 px"
            case _ as unreachable:
                assert_never(unreachable)


class YtdlpRateLimit(Enum):
    """Rate limits for yt-dlp (B/s)."""

    DISABLE = None
    KIBS_500 = 500 * 1024
    KIBS_1000 = 1000 * 1024
    KIBS_2000 = 2000 * 1024
    KIBS_3000 = 3000 * 1024
    KIBS_4000 = 4000 * 1024

    def __str__(self) -> str:
        if self.value is not None:
            return f"{self.value // 1024} KiB/s"
        return "disabled"


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


class CookieFormat(Enum):
    """Format options for retrieved cookies."""

    COOKIELIST = auto()
    COOKIEJAR = auto()
    NETSCAPE = auto()


class Browser(Enum):
    """Browsers to use cookies from."""

    NONE = None
    ARC = "Arc"
    BRAVE = "Brave"
    CHROME = "Chrome"
    CHROMIUM = "Chromium"
    EDGE = "Edge"
    FIREFOX = "Firefox"
    LIBREWOLF = "Librewolf"
    OCTO_BROWSER = "Octo Browser"
    OPERA = "Opera"
    OPERA_GX = "Opera GX"
    SAFARI = "Safari"
    VIVALDI = "Vivaldi"

    def __str__(self) -> str:
        if self is Browser.NONE:
            return "None"
        return self.value

    def icon(self) -> str:
        match self:
            case Browser.NONE:
                return ""
            case Browser.ARC:
                return ":/icons/arc.png"
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
            case Browser.LIBREWOLF:
                return ":/icons/librewolf.png"
            case Browser.OCTO_BROWSER:
                return ":/icons/octo_browser.png"
            case Browser.OPERA:
                return ":/icons/opera.png"
            case Browser.OPERA_GX:
                return ":/icons/opera_gx.png"
            case Browser.SAFARI:
                return ":/icons/safari.png"
            case Browser.VIVALDI:
                return ":/icons/vivaldi.png"
            case _ as unreachable:
                assert_never(unreachable)

    def cookies(
        self, fmt: CookieFormat
    ) -> rookiepy.CookieList | CookieJar | str | None:
        match self:
            case Browser.NONE:
                return None
            case Browser.ARC:
                function = rookiepy.arc
            case Browser.BRAVE:
                function = rookiepy.brave
            case Browser.CHROME:
                function = rookiepy.chrome
            case Browser.CHROMIUM:
                function = rookiepy.chromium
            case Browser.EDGE:
                function = rookiepy.edge
            case Browser.FIREFOX:
                function = rookiepy.firefox
            case Browser.LIBREWOLF:
                function = rookiepy.librewolf
            case Browser.OCTO_BROWSER:
                function = rookiepy.octo_browser
            case Browser.OPERA:
                function = rookiepy.opera
            case Browser.OPERA_GX:
                function = rookiepy.opera_gx
            case Browser.SAFARI:
                function = rookiepy.safari
            case Browser.VIVALDI:
                function = rookiepy.vivaldi
            case _ as unreachable:
                assert_never(unreachable)
        try:
            match fmt:
                case CookieFormat.COOKIELIST:
                    return function(constants.COOKIE_DOMAINS)
                case CookieFormat.COOKIEJAR:
                    return rookiepy.to_cookiejar(function(constants.COOKIE_DOMAINS))
                case CookieFormat.NETSCAPE:
                    return rookiepy.to_netscape(function(constants.COOKIE_DOMAINS))
        except Exception:  # pylint: disable=broad-exception-caught
            logger.warning(
                f"Retrieving cookies from {str(self)} failed. "
                "You can export your browser cookies manually and load them "
                "in the settings."
            )
            logger.debug(traceback.format_exc())
        logger.warning(f"Failed to retrieve {str(self)} cookies.")
        return None


class VideoContainer(Enum):
    """Video containers that can be requested when downloading with ytdl."""

    BEST = "bestvideo"
    MP4 = "mp4"
    MP4_AV1 = "mp4_av1"
    MP4_AVC = "mp4_avc"
    MP4_VP9 = "mp4_vp9"
    WEBM = "webm"

    def __str__(self) -> str:
        match self:
            case VideoContainer.BEST:
                return "Best available container/codec"
            case VideoContainer.MP4:
                return ".mp4 (best available codec)"
            case VideoContainer.MP4_AV1:
                return ".mp4 (AV1 codec)"
            case VideoContainer.MP4_AVC:
                return ".mp4 (AVC/H.264 codec)"
            case VideoContainer.MP4_VP9:
                return ".mp4 (VP9 codec)"
            case VideoContainer.WEBM:
                return ".webm (VP9 codec)"
            case _ as unreachable:
                assert_never(unreachable)

    def ytdl_ext(self) -> str | None:
        match self:
            case VideoContainer.BEST:
                return None
            case (
                VideoContainer.MP4
                | VideoContainer.MP4_AV1
                | VideoContainer.MP4_AVC
                | VideoContainer.MP4_VP9
            ):
                return VideoContainer.MP4.value
            case VideoContainer.WEBM:
                return self.value
            case _ as unreachable:
                assert_never(unreachable)

    def ytdl_vcodec(self) -> str | None:
        match self:
            case VideoContainer.BEST:
                return None
            case VideoContainer.MP4 | VideoContainer.WEBM:
                return None
            case VideoContainer.MP4_AV1:
                return "av01"
            case VideoContainer.MP4_AVC:
                return "^(avc|h264)"
            case VideoContainer.MP4_VP9:
                return "^vp0?9"
            case _ as unreachable:
                assert_never(unreachable)


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


class SupportedApps(StrEnum):
    """Supported third-party apps to be launched from the USDB Syncer."""

    KAREDI = auto()
    PERFORMOUS = auto()
    ULTRASTAR_MANAGER = auto()
    USDX = auto()
    VOCALUXE = auto()
    YASS_RELOADED = auto()

    def __str__(self) -> str:
        match self:
            case SupportedApps.KAREDI:
                return "Karedi"
            case SupportedApps.PERFORMOUS:
                return "Performous"
            case SupportedApps.ULTRASTAR_MANAGER:
                return "UltraStar Manager"
            case SupportedApps.USDX:
                return "UltraStar Deluxe"
            case SupportedApps.VOCALUXE:
                return "Vocaluxe"
            case SupportedApps.YASS_RELOADED:
                return "YASS Reloaded"
            case _ as unreachable:
                assert_never(unreachable)

    def executable_name(self) -> str:
        match self:
            case SupportedApps.KAREDI:
                return "Karedi"
            case SupportedApps.PERFORMOUS:
                return "performous"
            case SupportedApps.ULTRASTAR_MANAGER:
                return "UltraStar-Manager"
            case SupportedApps.USDX:
                return "ultrastardx"
            case SupportedApps.VOCALUXE:
                return "Vocaluxe"
            case SupportedApps.YASS_RELOADED:
                return "yass"
            case _ as unreachable:
                assert_never(unreachable)

    def songpath_parameter(self) -> str:
        match self:
            case SupportedApps.KAREDI:
                return ""
            case SupportedApps.PERFORMOUS:
                return ""
            case SupportedApps.ULTRASTAR_MANAGER:
                return "-songpath"
            case SupportedApps.USDX:
                return "-songpath"
            case SupportedApps.VOCALUXE:
                return "-SongFolder"
            case SupportedApps.YASS_RELOADED:
                return ""
            case _ as unreachable:
                assert_never(unreachable)

    def open_app(self, path: Path) -> None:
        logger.debug(f"Starting {self} with '{path}'.")
        executable = get_app_path(self)
        if executable is None:
            return
        if executable.suffix == ".jar":
            cmd = ["java", "-jar", str(executable), str(path)]
        else:
            cmd = [str(executable), self.songpath_parameter(), str(path)]
        try:
            # We are not using a context manager here so that the app is launched
            # without blocking the syncer.
            subprocess.Popen(cmd)  # pylint: disable=consider-using-with
        except FileNotFoundError:
            logger.error(
                f"Failed to launch {self} from '{str(executable)}', file not found. "
                "Please check the executable path in the settings."
            )
        except OSError:
            logger.error(
                f"Failed to launch {self} from '{str(executable)}', I/O error."
            )
            logger.debug(traceback.format_exc())
        except subprocess.SubprocessError:
            logger.error(
                f"Failed to launch {self} from '{str(executable)}', subprocess error."
            )
            logger.debug(traceback.format_exc())


T = TypeVar("T")


def get_setting(key: SettingKey, default: T) -> T:
    try:
        value = QSettings().value(key.value)
    except (AttributeError, ValueError):
        # setting contains a type incompatible with this version
        return default
    if isinstance(value, ret_type := type(default)):
        return value
    if isinstance(default, bool) and isinstance(value, int):
        # we store bools as ints because Qt doesn't store raw bools
        return cast(T, bool(value))
    if isinstance(value, str) and ret_type in (int, float, bool):
        # in INI files (default on Linux) numeric values are stored as strings
        try:
            if ret_type == bool:
                value = int(value)
            return ret_type(value)  # type: ignore
        except (ValueError, TypeError):
            pass
    return default


def set_setting(key: SettingKey, value: Any) -> None:
    if isinstance(value, bool):
        # Qt stores bools as "true" and "false" otherwise
        value = int(value)
    QSettings().setValue(key.value, value)


def get_throttling_threads() -> int:
    return get_setting(SettingKey.THROTTLING_THREADS, 0)


def set_throttling_threads(value: int) -> None:
    set_setting(SettingKey.THROTTLING_THREADS, value)


def get_ytdlp_rate_limit() -> YtdlpRateLimit:
    return get_setting(SettingKey.YTDLP_RATE_LIMIT, YtdlpRateLimit.DISABLE)


def set_ytdlp_rate_limit(value: YtdlpRateLimit) -> None:
    set_setting(SettingKey.YTDLP_RATE_LIMIT, value)


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


def get_encoding() -> Encoding:
    return get_setting(SettingKey.ENCODING, Encoding.UTF_8)


def set_encoding(value: Encoding) -> None:
    set_setting(SettingKey.ENCODING, value)


def get_newline() -> Newline:
    return get_setting(SettingKey.NEWLINE, Newline.default())


def set_newline(value: Newline) -> None:
    set_setting(SettingKey.NEWLINE, value)


def get_version() -> FormatVersion:
    return get_setting(SettingKey.FORMAT_VERSION, FormatVersion.V1_0_0)


def set_version(value: FormatVersion) -> None:
    set_setting(SettingKey.FORMAT_VERSION, value)


def get_txt() -> bool:
    return get_setting(SettingKey.TXT, True)


def set_txt(value: bool) -> None:
    set_setting(SettingKey.TXT, value)


def get_fix_linebreaks() -> FixLinebreaks:
    return get_setting(SettingKey.FIX_LINEBREAKS, FixLinebreaks.YASS_STYLE)


def set_fix_linebreaks(value: FixLinebreaks) -> None:
    set_setting(SettingKey.FIX_LINEBREAKS, value)


def get_fix_first_words_capitalization() -> bool:
    return get_setting(SettingKey.FIX_FIRST_WORDS_CAPITALIZATION, True)


def set_fix_first_words_capitalization(value: bool) -> None:
    set_setting(SettingKey.FIX_FIRST_WORDS_CAPITALIZATION, value)


def get_fix_spaces() -> FixSpaces:
    return get_setting(SettingKey.FIX_SPACES, FixSpaces.AFTER)


def set_fix_spaces(value: FixSpaces) -> None:
    set_setting(SettingKey.FIX_SPACES, value)


def get_fix_quotation_marks() -> bool:
    return get_setting(SettingKey.FIX_QUOTATION_MARKS, True)


def set_fix_quotation_marks(value: bool) -> None:
    set_setting(SettingKey.FIX_QUOTATION_MARKS, value)


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
    """Returns the stored song diretory, which may be overwritten by an environment
    variable.
    """
    if path := os.environ.get("SONG_DIR"):
        return Path(path)
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


def get_video_embed_artwork() -> bool:
    return get_setting(SettingKey.VIDEO_EMBED_ARTWORK, False)


def set_video_embed_artwork(value: bool) -> None:
    set_setting(SettingKey.VIDEO_EMBED_ARTWORK, value)


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


def get_path_template() -> path_template.PathTemplate:
    return get_setting(SettingKey.PATH_TEMPLATE, path_template.PathTemplate.default())


def set_path_template(template: path_template.PathTemplate) -> None:
    set_setting(SettingKey.PATH_TEMPLATE, template)


def get_app_path(app: SupportedApps) -> Path | None:
    match app:
        case SupportedApps.KAREDI:
            path = get_setting(SettingKey.APP_PATH_KAREDI, "")
        case SupportedApps.PERFORMOUS:
            path = get_setting(SettingKey.APP_PATH_PERFORMOUS, "")
        case SupportedApps.ULTRASTAR_MANAGER:
            path = get_setting(SettingKey.APP_PATH_ULTRASTAR_MANAGER, "")
        case SupportedApps.USDX:
            path = get_setting(SettingKey.APP_PATH_USDX, "")
        case SupportedApps.VOCALUXE:
            path = get_setting(SettingKey.APP_PATH_VOCALUXE, "")
        case SupportedApps.YASS_RELOADED:
            path = get_setting(SettingKey.APP_PATH_YASS_RELOADED, "")
        case _ as unreachable:
            assert_never(unreachable)
    return Path(path) if path != "" else None


def set_app_path(app: SupportedApps, path: str) -> None:
    match app:
        case SupportedApps.KAREDI:
            set_setting(SettingKey.APP_PATH_KAREDI, path)
        case SupportedApps.PERFORMOUS:
            set_setting(SettingKey.APP_PATH_PERFORMOUS, path)
        case SupportedApps.ULTRASTAR_MANAGER:
            set_setting(SettingKey.APP_PATH_ULTRASTAR_MANAGER, path)
        case SupportedApps.USDX:
            set_setting(SettingKey.APP_PATH_USDX, path)
        case SupportedApps.VOCALUXE:
            set_setting(SettingKey.APP_PATH_VOCALUXE, path)
        case SupportedApps.YASS_RELOADED:
            set_setting(SettingKey.APP_PATH_YASS_RELOADED, path)
        case _ as unreachable:
            assert_never(unreachable)


def get_cookies_from_browser() -> bool:
    return get_setting(SettingKey.COOKIES_FROM_BROWSER, True)


def set_cookies_from_browser(value: bool) -> None:
    set_setting(SettingKey.COOKIES_FROM_BROWSER, value)
