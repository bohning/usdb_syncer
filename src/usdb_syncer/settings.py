"""Persistent app settings.

To ensure consistent default values and avoid key collisions, QSettings should never be
used directly. Instead, new settings should be added to the SettingKey enum and setters
and getters should be added to this module.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from enum import Enum, StrEnum, auto
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, ClassVar, TypeVar, assert_never, cast

import keyring
import rookiepy
from PySide6.QtCore import QByteArray, QSettings

from usdb_syncer import path_template, utils
from usdb_syncer.constants import Usdb
from usdb_syncer.logger import logger

SYSTEM_USDB = "USDB Syncer/USDB"
NO_KEYRING_BACKEND_WARNING = (
    "Your USDB password cannot be stored or retrieved because no keyring backend is "
    "available. See https://pypi.org/project/keyring for details."
)


def get_usdb_auth() -> tuple[str, str]:
    username = _Settings.get(SettingKey.USDB_USER_NAME, "")
    pwd = ""
    try:
        pwd = keyring.get_password(SYSTEM_USDB, username) or ""
    except keyring.core.backend.errors.NoKeyringError as error:
        logger.debug(error)
        logger.warning(NO_KEYRING_BACKEND_WARNING)
    return (username, pwd)


def set_usdb_auth(username: str, password: str) -> None:
    _Settings.set(SettingKey.USDB_USER_NAME, username)
    try:
        keyring.set_password(SYSTEM_USDB, username, password)
    except keyring.core.backend.errors.NoKeyringError as error:
        logger.debug(error)
        logger.warning(NO_KEYRING_BACKEND_WARNING)


def ffmpeg_is_available() -> bool:
    if shutil.which("ffmpeg"):
        return True
    if (path := get_ffmpeg_dir()) and path not in os.environ["PATH"]:
        # first run; restore path from settings
        utils.add_to_system_path(path)
        if shutil.which("ffmpeg"):
            return True
    return False


class _TemporarySettings:
    """Temporary settings for the USDB Syncer.

    This class is used to store temporary settings in memory.
    It should not be used directly, as it is not thread-safe.
    """

    _temporary_settings: ClassVar[dict[SettingKey, Any]] = {}

    @classmethod
    def remove(cls, key: SettingKey) -> None:
        """Remove a temporary setting."""
        cls._temporary_settings.pop(key, None)

    @classmethod
    def set(cls, key: SettingKey, value: Any) -> None:
        """Set a temporary setting."""
        cls._temporary_settings[key] = value

    @classmethod
    def get(cls, key: SettingKey) -> Any:
        """Get a temporary setting."""
        return cls._temporary_settings.get(key, None)


T = TypeVar("T")


class _Settings:
    """Settings for the USDB Syncer.

    This class is a singleton that provides access to the settings of the USDB Syncer.
    """

    _lock = threading.RLock()

    @classmethod
    def set(cls, key: SettingKey, value: Any, temp: bool = False) -> None:
        if temp:
            cls._set_temporary(key, value)
        else:
            cls._set_permanent(key, value)

    @classmethod
    def _set_temporary(cls, key: SettingKey, value: Any) -> None:
        with cls._lock:
            _TemporarySettings.set(key, value)

    @classmethod
    def _set_permanent(cls, key: SettingKey, value: Any) -> None:
        with cls._lock:
            _TemporarySettings.remove(key)

            if isinstance(value, bool):
                # Qt stores bools as "true" and "false" otherwise
                value = int(value)
            QSettings().setValue(key.value, value)

    @classmethod
    def get(cls, key: SettingKey, default: T) -> T:
        with cls._lock:
            if temp := _TemporarySettings.get(key):
                return temp

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
                    if ret_type is bool:
                        value = int(value)
                    # MyPy doesn't understand any of this, but it should be safe
                    return cast(T, ret_type(value))  # type: ignore[call-arg]
                except (ValueError, TypeError):
                    pass
            return default

    @classmethod
    def reset(cls) -> None:
        """Reset QSettings to default."""
        QSettings().clear()


class SettingKey(Enum):
    """Keys for storing and retrieving settings."""

    SONG_DIR = "song_dir"
    FFMPEG_DIR = "ffmpeg_dir"
    BROWSER = "downloads/browser"
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
    AUDIO_NORMALIZATION = "downloads/audio_normalization"
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
    DISCORD_ALLOWED = "downloads/discord_allowed"
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
    REPORT_PDF_PAGESIZE = "report/pdf_pagesize"
    REPORT_PDF_ORIENTATION = "report/pdf_orientation"
    REPORT_PDF_MARGIN = "report/pdf_margin"
    REPORT_PDF_COLUMNS = "report/pdf_columns"
    REPORT_PDF_FONTSIZE = "report/pdf_fontsize"
    REPORT_JSON_INDENT = "report/json_indent"
    VIEW_THEME = "view/theme"
    VIEW_PRIMARY_COLOR = "view/primary_color"
    VIEW_COLORED_BACKGROUND = "view/colored_background"


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


class AudioNormalization(Enum):
    """Audio normalization."""

    DISABLE = None
    REPLAYGAIN = "ReplayGain"
    NORMALIZE = "Normalize (rewrites file)"

    def __str__(self) -> str:
        if self.value is not None:
            return self.value
        return "disabled"


class Browser(Enum):
    """Browsers to use cookies from."""

    NONE = None
    ARC = "arc"
    BRAVE = "brave"
    CHROME = "chrome"
    CHROMIUM = "chromium"
    EDGE = "edge"
    FIREFOX = "firefox"
    LIBREWOLF = "librewolf"
    OCTO_BROWSER = "octo browser"
    OPERA = "opera"
    OPERA_GX = "opera gx"
    SAFARI = "safari"
    VIVALDI = "vivaldi"

    def __str__(self) -> str:
        if self is Browser.NONE:
            return "None"
        return self.value.capitalize()

    def cookies(self) -> CookieJar | None:  # noqa: C901
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
            return rookiepy.to_cookiejar(function([Usdb.DOMAIN]))
        except Exception:  # noqa: BLE001
            logger.exception(None)
        logger.warning(f"Failed to retrieve {self!s} cookies.")
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


class Theme(Enum):
    """Application theme."""

    SYSTEM = "System"
    DARK = "Dark"

    def __str__(self) -> str:
        return self.value


class Color(Enum):
    """Colors for GUI customization."""

    RED = "Red"
    PINK = "Pink"
    PURPLE = "Purple"
    DEEPPURPLE = "Deep purple"
    INDIGO = "Indigo"
    BLUE = "Blue"
    LIGHTBLUE = "Light blue"
    CYAN = "Cyan"
    TEAL = "Teal"
    GREEN = "Green"
    LIGHTGREEN = "Light green"
    LIME = "Lime"
    YELLOW = "Yellow"
    AMBER = "Amber"
    ORANGE = "Orange"
    DEEPORANGE = "Deep orange"
    BROWN = "Brown"
    GRAY = "Gray"
    BLUEGRAY = "Blue gray"

    def __str__(self) -> str:
        return self.value


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
            utils.start_process_detached(cmd)
        except FileNotFoundError:
            logger.error(
                f"Failed to launch {self} from '{executable!s}', file not found. "
                "Please check the executable path in the settings."
            )
        except OSError:
            logger.exception(
                f"Failed to launch {self} from '{executable!s}', I/O error."
            )
        except subprocess.SubprocessError:
            logger.exception(
                f"Failed to launch {self} from '{executable!s}', subprocess error."
            )


class ReportPDFPagesize(Enum):
    """Supported PDF page sizes."""

    A3 = "A3"
    A4 = "A4"
    A5 = "A5"
    LETTER = "Letter"
    LEGAL = "Legal"

    def __str__(self) -> str:
        return str(self.value)


class ReportPDFOrientation(Enum):
    """Supported PDF page orientations."""

    PORTRAIT = "Portrait"
    LANDSCAPE = "Landscape"

    def __str__(self) -> str:
        return str(self.value)


def reset() -> None:
    _Settings.reset()


def get_throttling_threads() -> int:
    return _Settings.get(SettingKey.THROTTLING_THREADS, 0)


def set_throttling_threads(value: int, temp: bool = False) -> None:
    _Settings.set(SettingKey.THROTTLING_THREADS, value, temp)


def get_ytdlp_rate_limit() -> YtdlpRateLimit:
    return _Settings.get(SettingKey.YTDLP_RATE_LIMIT, YtdlpRateLimit.DISABLE)


def set_ytdlp_rate_limit(value: YtdlpRateLimit, temp: bool = False) -> None:
    _Settings.set(SettingKey.YTDLP_RATE_LIMIT, value, temp)


def get_audio() -> bool:
    return _Settings.get(SettingKey.AUDIO, True)


def set_audio(value: bool, temp: bool = False) -> None:
    _Settings.set(SettingKey.AUDIO, value, temp)


def get_audio_format() -> AudioFormat:
    return _Settings.get(SettingKey.AUDIO_FORMAT, AudioFormat.M4A)


def set_audio_format(value: AudioFormat, temp: bool = False) -> None:
    _Settings.set(SettingKey.AUDIO_FORMAT, value, temp)


def get_audio_bitrate() -> AudioBitrate:
    return _Settings.get(SettingKey.AUDIO_BITRATE, AudioBitrate.KBPS_256)


def set_audio_bitrate(value: AudioBitrate, temp: bool = False) -> None:
    _Settings.set(SettingKey.AUDIO_BITRATE, value, temp)


def get_audio_normalization() -> AudioNormalization:
    return _Settings.get(SettingKey.AUDIO_NORMALIZATION, AudioNormalization.DISABLE)


def set_audio_normalization(value: AudioNormalization, temp: bool = False) -> None:
    _Settings.set(SettingKey.AUDIO_NORMALIZATION, value, temp)


def get_audio_embed_artwork() -> bool:
    return _Settings.get(SettingKey.AUDIO_EMBED_ARTWORK, False)


def set_audio_embed_artwork(value: bool, temp: bool = False) -> None:
    _Settings.set(SettingKey.AUDIO_EMBED_ARTWORK, value, temp)


def get_encoding() -> Encoding:
    return _Settings.get(SettingKey.ENCODING, Encoding.UTF_8)


def set_encoding(value: Encoding, temp: bool = False) -> None:
    _Settings.set(SettingKey.ENCODING, value, temp)


def get_newline() -> Newline:
    return _Settings.get(SettingKey.NEWLINE, Newline.default())


def set_newline(value: Newline, temp: bool = False) -> None:
    _Settings.set(SettingKey.NEWLINE, value, temp)


def get_version() -> FormatVersion:
    return _Settings.get(SettingKey.FORMAT_VERSION, FormatVersion.V1_0_0)


def set_version(value: FormatVersion, temp: bool = False) -> None:
    _Settings.set(SettingKey.FORMAT_VERSION, value, temp)


def get_txt() -> bool:
    return _Settings.get(SettingKey.TXT, True)


def set_txt(value: bool, temp: bool = False) -> None:
    _Settings.set(SettingKey.TXT, value, temp)


def get_fix_linebreaks() -> FixLinebreaks:
    return _Settings.get(SettingKey.FIX_LINEBREAKS, FixLinebreaks.YASS_STYLE)


def set_fix_linebreaks(value: FixLinebreaks, temp: bool = False) -> None:
    _Settings.set(SettingKey.FIX_LINEBREAKS, value, temp)


def get_fix_first_words_capitalization() -> bool:
    return _Settings.get(SettingKey.FIX_FIRST_WORDS_CAPITALIZATION, True)


def set_fix_first_words_capitalization(value: bool, temp: bool = False) -> None:
    _Settings.set(SettingKey.FIX_FIRST_WORDS_CAPITALIZATION, value, temp)


def get_fix_spaces() -> FixSpaces:
    return _Settings.get(SettingKey.FIX_SPACES, FixSpaces.AFTER)


def set_fix_spaces(value: FixSpaces, temp: bool = False) -> None:
    _Settings.set(SettingKey.FIX_SPACES, value, temp)


def get_fix_quotation_marks() -> bool:
    return _Settings.get(SettingKey.FIX_QUOTATION_MARKS, True)


def set_fix_quotation_marks(value: bool, temp: bool = False) -> None:
    _Settings.set(SettingKey.FIX_QUOTATION_MARKS, value, temp)


def get_cover() -> bool:
    return _Settings.get(SettingKey.COVER, True)


def set_cover(value: bool, temp: bool = False) -> None:
    _Settings.set(SettingKey.COVER, value, temp)


def get_cover_max_size() -> CoverMaxSize:
    return _Settings.get(SettingKey.COVER_MAX_SIZE, CoverMaxSize.PX_1920)


def set_cover_max_size(value: CoverMaxSize, temp: bool = False) -> None:
    _Settings.set(SettingKey.COVER_MAX_SIZE, value, temp)


def get_browser() -> Browser:
    return _Settings.get(SettingKey.BROWSER, Browser.CHROME)


def set_browser(value: Browser, temp: bool = False) -> None:
    _Settings.set(SettingKey.BROWSER, value, temp)


def get_song_dir() -> Path:
    return _Settings.get(SettingKey.SONG_DIR, Path("songs").resolve())


def set_song_dir(value: Path, temp: bool = False) -> None:
    _Settings.set(SettingKey.SONG_DIR, value, temp)


def get_video() -> bool:
    return _Settings.get(SettingKey.VIDEO, True)


def set_video(value: bool, temp: bool = False) -> None:
    _Settings.set(SettingKey.VIDEO, value, temp)


def get_video_format() -> VideoContainer:
    return _Settings.get(SettingKey.VIDEO_FORMAT, VideoContainer.MP4)


def set_video_format(value: VideoContainer, temp: bool = False) -> None:
    _Settings.set(SettingKey.VIDEO_FORMAT, value, temp)


def get_video_reencode() -> bool:
    return _Settings.get(SettingKey.VIDEO_REENCODE, False)


def set_video_reencode(value: bool, temp: bool = False) -> None:
    _Settings.set(SettingKey.VIDEO_REENCODE, value, temp)


def get_video_format_new() -> VideoCodec:
    return _Settings.get(SettingKey.VIDEO_FORMAT_NEW, VideoCodec.H264)


def set_video_format_new(value: VideoCodec, temp: bool = False) -> None:
    _Settings.set(SettingKey.VIDEO_FORMAT_NEW, value, temp)


def get_video_resolution() -> VideoResolution:
    return _Settings.get(SettingKey.VIDEO_RESOLUTION_MAX, VideoResolution.P1080)


def set_video_resolution(value: VideoResolution, temp: bool = False) -> None:
    _Settings.set(SettingKey.VIDEO_RESOLUTION_MAX, value, temp)


def get_video_fps() -> VideoFps:
    return _Settings.get(SettingKey.VIDEO_FPS_MAX, VideoFps.FPS_60)


def set_video_fps(value: VideoFps, temp: bool = False) -> None:
    _Settings.set(SettingKey.VIDEO_FPS_MAX, value, temp)


def get_video_embed_artwork() -> bool:
    return _Settings.get(SettingKey.VIDEO_EMBED_ARTWORK, False)


def set_video_embed_artwork(value: bool, temp: bool = False) -> None:
    _Settings.set(SettingKey.VIDEO_EMBED_ARTWORK, value, temp)


def get_background() -> bool:
    return _Settings.get(SettingKey.BACKGROUND, True)


def set_background(value: bool, temp: bool = False) -> None:
    _Settings.set(SettingKey.BACKGROUND, value, temp)


def get_background_always() -> bool:
    return _Settings.get(SettingKey.BACKGROUND_ALWAYS, True)


def set_background_always(value: bool, temp: bool = False) -> None:
    _Settings.set(SettingKey.BACKGROUND_ALWAYS, value, temp)


def get_discord_allowed() -> bool:
    return _Settings.get(SettingKey.DISCORD_ALLOWED, False)


def set_discord_allowed(value: bool, temp: bool = False) -> None:
    _Settings.set(SettingKey.DISCORD_ALLOWED, value, temp)


def get_ffmpeg_dir() -> str:
    return _Settings.get(SettingKey.FFMPEG_DIR, "")


def set_ffmpeg_dir(value: str, temp: bool = False) -> None:
    _Settings.set(SettingKey.FFMPEG_DIR, value, temp)


def get_geometry_main_window() -> QByteArray:
    return _Settings.get(SettingKey.MAIN_WINDOW_GEOMETRY, QByteArray())


def set_geometry_main_window(geometry: QByteArray, temp: bool = False) -> None:
    _Settings.set(SettingKey.MAIN_WINDOW_GEOMETRY, geometry, temp)


def get_state_main_window() -> QByteArray:
    return _Settings.get(SettingKey.MAIN_WINDOW_STATE, QByteArray())


def set_state_main_window(state: QByteArray, temp: bool = False) -> None:
    _Settings.set(SettingKey.MAIN_WINDOW_STATE, state, temp)


def get_geometry_log_dock() -> QByteArray:
    return _Settings.get(SettingKey.DOCK_LOG_GEOMETRY, QByteArray())


def set_geometry_log_dock(state: QByteArray, temp: bool = False) -> None:
    _Settings.set(SettingKey.DOCK_LOG_GEOMETRY, state, temp)


def get_table_view_header_state() -> QByteArray:
    return _Settings.get(SettingKey.TABLE_VIEW_HEADER_STATE, QByteArray())


def set_table_view_header_state(state: QByteArray, temp: bool = False) -> None:
    _Settings.set(SettingKey.TABLE_VIEW_HEADER_STATE, state, temp)


def get_path_template() -> path_template.PathTemplate:
    return _Settings.get(SettingKey.PATH_TEMPLATE, path_template.PathTemplate.default())


def set_path_template(template: path_template.PathTemplate, temp: bool = False) -> None:
    _Settings.set(SettingKey.PATH_TEMPLATE, template, temp)


def get_theme() -> Theme:
    return _Settings.get(SettingKey.VIEW_THEME, Theme.SYSTEM)


def set_theme(theme: Theme) -> None:
    _Settings.set(SettingKey.VIEW_THEME, theme)


def get_primary_color() -> Color:
    return _Settings.get(SettingKey.VIEW_PRIMARY_COLOR, Color.RED)


def set_primary_color(primary_color: Color) -> None:
    _Settings.set(SettingKey.VIEW_PRIMARY_COLOR, primary_color)


def get_colored_background() -> bool:
    return _Settings.get(SettingKey.VIEW_COLORED_BACKGROUND, False)


def set_colored_background(colored_background: bool) -> None:
    _Settings.set(SettingKey.VIEW_COLORED_BACKGROUND, colored_background)


def get_app_path(app: SupportedApps) -> Path | None:
    match app:
        case SupportedApps.KAREDI:
            path = _Settings.get(SettingKey.APP_PATH_KAREDI, "")
        case SupportedApps.PERFORMOUS:
            path = _Settings.get(SettingKey.APP_PATH_PERFORMOUS, "")
        case SupportedApps.ULTRASTAR_MANAGER:
            path = _Settings.get(SettingKey.APP_PATH_ULTRASTAR_MANAGER, "")
        case SupportedApps.USDX:
            path = _Settings.get(SettingKey.APP_PATH_USDX, "")
        case SupportedApps.VOCALUXE:
            path = _Settings.get(SettingKey.APP_PATH_VOCALUXE, "")
        case SupportedApps.YASS_RELOADED:
            path = _Settings.get(SettingKey.APP_PATH_YASS_RELOADED, "")
        case _ as unreachable:
            assert_never(unreachable)
    return Path(path) if path != "" else None


def set_app_path(app: SupportedApps, path: str, temp: bool = False) -> None:
    setting_key = None
    match app:
        case SupportedApps.KAREDI:
            setting_key = SettingKey.APP_PATH_KAREDI
        case SupportedApps.PERFORMOUS:
            setting_key = SettingKey.APP_PATH_PERFORMOUS
        case SupportedApps.ULTRASTAR_MANAGER:
            setting_key = SettingKey.APP_PATH_ULTRASTAR_MANAGER
        case SupportedApps.USDX:
            setting_key = SettingKey.APP_PATH_USDX
        case SupportedApps.VOCALUXE:
            setting_key = SettingKey.APP_PATH_VOCALUXE
        case SupportedApps.YASS_RELOADED:
            setting_key = SettingKey.APP_PATH_YASS_RELOADED
        case _ as unreachable:
            assert_never(unreachable)

    _Settings.set(setting_key, path, temp)


def get_report_pdf_pagesize() -> ReportPDFPagesize:
    return _Settings.get(SettingKey.REPORT_PDF_PAGESIZE, ReportPDFPagesize.A4)


def set_report_pdf_pagesize(pagesize: ReportPDFPagesize, temp: bool = False) -> None:
    _Settings.set(SettingKey.REPORT_PDF_PAGESIZE, pagesize, temp)


def get_report_pdf_orientation() -> ReportPDFOrientation:
    return _Settings.get(
        SettingKey.REPORT_PDF_ORIENTATION, ReportPDFOrientation.PORTRAIT
    )


def set_report_pdf_orientation(
    orientation: ReportPDFOrientation, temp: bool = False
) -> None:
    _Settings.set(SettingKey.REPORT_PDF_ORIENTATION, orientation, temp)


def get_report_pdf_margin() -> int:
    return _Settings.get(SettingKey.REPORT_PDF_MARGIN, 20)


def set_report_pdf_margin(margin: int, temp: bool = False) -> None:
    _Settings.set(SettingKey.REPORT_PDF_MARGIN, margin, temp)


def get_report_pdf_columns() -> int:
    return _Settings.get(SettingKey.REPORT_PDF_COLUMNS, 2)


def set_report_pdf_columns(columns: int, temp: bool = False) -> None:
    _Settings.set(SettingKey.REPORT_PDF_COLUMNS, columns, temp)


def get_report_pdf_fontsize() -> int:
    return _Settings.get(SettingKey.REPORT_PDF_FONTSIZE, 10)


def set_report_pdf_fontsize(fontsize: int, temp: bool = False) -> None:
    _Settings.set(SettingKey.REPORT_PDF_FONTSIZE, fontsize, temp)


def get_report_json_indent() -> int:
    return _Settings.get(SettingKey.REPORT_JSON_INDENT, 4)


def set_report_json_indent(indent: int, temp: bool = False) -> None:
    _Settings.set(SettingKey.REPORT_JSON_INDENT, indent, temp)
