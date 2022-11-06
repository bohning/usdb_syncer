"""Options for downloading songs."""

from dataclasses import dataclass
from enum import Enum

from usdb_dl.typing_helpers import assert_never


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


@dataclass
class TxtOptions:
    """Settings regarding the song txt file to be downloaded."""

    encoding: Encoding
    newline: Newline


@dataclass
class AudioOptions:
    """Settings regarding the audio file to be downloaded."""

    format: AudioContainer
    reencode_format: AudioCodec | None

    def extension(self) -> str | None:
        """The extension of the downloaded file. Unknown if 'bestaudio' is selected and
        not target codec is set.
        """
        if self.reencode_format:
            return self.reencode_format.value
        if self.format is AudioContainer.BEST:
            return None
        return self.format.value


@dataclass
class VideoOptions:
    """Settings regarding the video file to be downloaded."""

    format: VideoContainer
    reencode_format: VideoCodec | None
    max_resolution: VideoResolution
    max_fps: VideoFps

    def ytdl_format(self) -> str:
        return (
            f"bestvideo[ext=mp4][width<={self.max_resolution.width()}]"
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
    browser: Browser
    video_options: VideoOptions | None
    cover: bool
    background_options: BackgroundOptions | None
