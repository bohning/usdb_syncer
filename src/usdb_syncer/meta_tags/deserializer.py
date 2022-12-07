"""Logic and dataclasses for meta tags from a txts video tag."""

from dataclasses import dataclass
from typing import Callable, Literal, TypeVar

from usdb_syncer.logger import Log
from usdb_syncer.meta_tags import decode_meta_tag_value


class MetaTagParseError(Exception):
    """Raised when a meta tag cannot be parsed."""


class CropMetaTags:
    """Meta tags for cropping media."""

    left: int
    upper: int
    right: int
    lower: int

    def __init__(self, value: str) -> None:
        try:
            self.left, self.upper, width, height = map(int, value.split("-"))
        except ValueError as err:
            raise MetaTagParseError(
                f"invalid value for crop meta tag: '{value}'"
            ) from err
        self.right = self.left + width
        self.lower = self.upper + height


class ResizeMetaTags:
    """Meta tags for resizing media."""

    width: int
    height: int

    def __init__(self, value: str) -> None:
        try:
            if "-" in value:
                self.width, self.height = map(int, value.split("-"))
            else:
                self.width = self.height = int(value)
        except ValueError as err:
            raise MetaTagParseError(
                f"invalid value for resize meta tag: '{value}'"
            ) from err


@dataclass
class ImageMetaTags:
    """Meta tags relating to the cover or background image."""

    source: str
    protocol: str = "https"
    rotate: float | None = None
    crop: CropMetaTags | None = None
    resize: ResizeMetaTags | None = None
    contrast: Literal["auto"] | float | None = None

    def source_url(self) -> str:
        if "://" in self.source:
            return self.source
        if "/" in self.source:
            return f"{self.protocol}://{self.source}"
        return f"{self.protocol}://images.fanart.tv/fanart/{self.source}"

    def image_processing(self) -> bool:
        """True if there is data for image processing."""
        return any((self.rotate, self.crop, self.resize, self.contrast))


class MedleyTag:
    """A tag with medley start and end."""

    start: int
    end: int

    def __init__(self, value: str) -> None:
        try:
            self.start, self.end = map(int, value.split("-"))
        except ValueError as err:
            raise MetaTagParseError(
                f"invalid value for medley meta tag: '{value}'"
            ) from err


class MetaTags:
    """Additional resource parameters from an overloaded video tag. Such an overloaded
    tag could look like:
    #VIDEO:a=example,co=foobar.jpg,bg=background.jpg
    """

    video: str | None = None
    audio: str | None = None
    cover: ImageMetaTags | None = None
    background: ImageMetaTags | None = None
    player1: str | None = None
    player2: str | None = None
    preview: float | None = None
    medley: MedleyTag | None = None

    def __init__(self, video_tag: str, logger: Log) -> None:
        if not "=" in video_tag:
            # probably a regular video file name and not a meta tag
            return
        for pair in video_tag.split(","):
            if "=" not in pair:
                logger.warning(f"missing key or value for meta tag: '{pair}'")
                continue
            key, value = pair.split("=", maxsplit=1)
            value = decode_meta_tag_value(value)
            match key:
                case "v":
                    self.video = value
                case "v-trim" | "v-crop":
                    # currently not used
                    pass
                case "a":
                    self.audio = value
                case "co":
                    self.cover = ImageMetaTags(source=value)
                case "co-protocol" if self.cover:
                    self.cover.protocol = value
                case "co-rotate" if self.cover:
                    self.cover.rotate = _try_parse_meta_tag(float, value, logger)
                case "co-crop" if self.cover:
                    self.cover.crop = _try_parse_meta_tag(CropMetaTags, value, logger)
                case "co-resize" if self.cover:
                    self.cover.resize = _try_parse_meta_tag(
                        ResizeMetaTags, value, logger
                    )
                case "co-contrast" if self.cover:
                    self.cover.contrast = _try_parse_contrast(value, logger)
                case "bg":
                    self.background = ImageMetaTags(source=value)
                case "bg-protocol" if self.background:
                    self.background.protocol = value
                case "bg-crop" if self.background:
                    self.background.crop = _try_parse_meta_tag(
                        CropMetaTags, value, logger
                    )
                case "bg-resize" if self.background:
                    self.background.resize = _try_parse_meta_tag(
                        ResizeMetaTags, value, logger
                    )
                case "p1":
                    self.player1 = value
                case "p2":
                    self.player2 = value
                case "preview":
                    self.preview = _try_parse_meta_tag(float, value, logger)
                case "medley":
                    self.medley = _try_parse_meta_tag(MedleyTag, value, logger)
                case _:
                    logger.warning(f"unknown key for meta tag: '{pair}'")

    def is_audio_only(self) -> bool:
        """True if a resource is explicitly set for audio only."""
        return bool(self.audio and not self.video)


T = TypeVar("T")


def _try_parse_meta_tag(cls: Callable[[str], T], value: str, logger: Log) -> T | None:
    try:
        return cls(value)
    except MetaTagParseError as err:
        logger.warning(str(err))
    except ValueError:
        if cls in (float, int):
            logger.warning(f"invalid number for meta tag: '{value}'")
        else:
            logger.warning(f"invalid value for meta tag: '{value}'")
    return None


def _try_parse_contrast(value: str, logger: Log) -> Literal["auto"] | float | None:
    if value == "auto":
        return "auto"
    try:
        return float(value)
    except ValueError:
        logger.warning(f"invalid value for contrast meta tag: '{value}'")
    return None
