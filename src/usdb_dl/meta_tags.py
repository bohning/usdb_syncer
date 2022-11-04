"""Logic and dataclasses for meta tags from a txts video tag."""

import logging
from dataclasses import dataclass
from typing import Literal

_logger: logging.Logger = logging.getLogger(__file__)


class CropMetaTags:
    """Meta tags for cropping media."""

    left: int
    upper: int
    right: int
    lower: int

    def __init__(self, crop_tag: str) -> None:
        self.left, self.upper, width, height = map(int, crop_tag.split("-"))
        self.right = self.left + width
        self.lower = self.upper + height


class ResizeMetaTags:
    """Meta tags for resizing media."""

    width: int
    height: int

    def __init__(self, resize_tag: str) -> None:
        self.width, self.height = map(int, resize_tag.split("-"))


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
        if "/" in self.source:
            return f"{self.protocol}://{self.source}"
        return f"{self.protocol}://images.fanart.tv/fanart/{self.source}"

    def image_processing(self) -> bool:
        """True if there is data for image processing."""
        return any((self.rotate, self.crop, self.resize, self.contrast))


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

    def __init__(self, video_tag: str) -> None:
        for pair in video_tag.split(","):
            if "=" not in pair:
                continue
            key, value = pair.split("=", maxsplit=1)
            match key:
                case "v":
                    self.video = value
                case "v-trim", "v-crop":
                    # currently not used
                    pass
                case "a":
                    self.audio = value
                case "co":
                    self.cover = ImageMetaTags(source=value)
                case "co-protocol" if self.cover:
                    self.cover.protocol = value
                case "co-rotate" if self.cover:
                    self.cover.rotate = float(value)
                case "co-crop" if self.cover:
                    self.cover.crop = CropMetaTags(value)
                case "co-resize" if self.cover:
                    self.cover.resize = ResizeMetaTags(value)
                case "co-contrast" if self.cover:
                    self.cover.contrast = "auto" if value == "auto" else float(value)
                case "bg":
                    self.background = ImageMetaTags(source=value)
                case "bg-protocol" if self.background:
                    self.background.protocol = value
                case "bg-crop" if self.background:
                    self.background.crop = CropMetaTags(value)
                case "bg-resize" if self.background:
                    self.background.resize = ResizeMetaTags(value)
                case "p1":
                    self.player1 = value
                case "p2":
                    self.player2 = value
                case _:
                    _logger.warning(
                        f"Invalid key/value pair '{pair}' found in #VIDEO tag '{video_tag}'"
                    )

    def is_duet(self) -> bool:
        return self.player1 is not None and self.player2 is not None
