"""Dataclasses and parse logic for meta tags from a txt's video tag."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import attrs

from usdb_syncer.logger import Log
from usdb_syncer.meta_tags.escaping import decode_meta_tag_value


@attrs.define
class CropMetaTags:
    """Meta tags for cropping media."""

    left: int
    upper: int
    right: int
    lower: int

    @classmethod
    def try_parse(cls, value: str, logger: Log) -> CropMetaTags | None:
        try:
            left, upper, width, height = map(int, value.split("-"))
        except ValueError:
            logger.warning(f"invalid value for crop meta tag: '{value}'")
            return None
        return cls(left, upper, left + width, upper + height)


@attrs.define
class ResizeMetaTags:
    """Meta tags for resizing media."""

    width: int
    height: int

    @classmethod
    def try_parse(cls, value: str, logger: Log) -> ResizeMetaTags | None:
        try:
            if "-" in value:
                width, height = map(int, value.split("-"))
            else:
                width = height = int(value)
        except ValueError:
            logger.warning(f"invalid value for resize meta tag: '{value}'")
            return None
        return cls(width, height)


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


@attrs.define
class MedleyTag:
    """A tag with medley start and end."""

    start: int
    end: int

    @classmethod
    def try_parse(cls, value: str, logger: Log) -> MedleyTag | None:
        try:
            start, end = map(int, value.split("-"))
        except ValueError:
            logger.warning(f"invalid value for medley meta tag: '{value}'")
            return None
        return cls(start, end)


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

    @classmethod
    def parse(cls, video_tag: str, logger: Log) -> MetaTags:
        tags = cls()
        if not "=" in video_tag:
            # probably a regular video file name and not a meta tag
            return tags
        for pair in video_tag.split(","):
            if "=" not in pair:
                logger.warning(f"missing key or value for meta tag: '{pair}'")
                continue
            key, value = pair.split("=", maxsplit=1)
            tags._parse_key_value_pair(key, value, logger)
        return tags

    def _parse_key_value_pair(self, key: str, value: str, logger: Log) -> None:
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
                self.cover.rotate = _try_parse_float(value, logger)
            case "co-crop" if self.cover:
                self.cover.crop = CropMetaTags.try_parse(value, logger)
            case "co-resize" if self.cover:
                self.cover.resize = ResizeMetaTags.try_parse(value, logger)
            case "co-contrast" if self.cover:
                self.cover.contrast = _try_parse_contrast(value, logger)
            case "bg":
                self.background = ImageMetaTags(source=value)
            case "bg-protocol" if self.background:
                self.background.protocol = value
            case "bg-crop" if self.background:
                self.background.crop = CropMetaTags.try_parse(value, logger)
            case "bg-resize" if self.background:
                self.background.resize = ResizeMetaTags.try_parse(value, logger)
            case "p1":
                self.player1 = value
            case "p2":
                self.player2 = value
            case "preview":
                self.preview = _try_parse_float(value, logger)
            case "medley":
                self.medley = MedleyTag.try_parse(value, logger)
            case _:
                logger.warning(f"unknown key for meta tag: '{key}={value}'")

    def is_audio_only(self) -> bool:
        """True if a resource is explicitly set for audio only."""
        return bool(self.audio and not self.video)


def _try_parse_float(value: str, logger: Log) -> float | None:
    try:
        return float(value)
    except ValueError:
        logger.warning(f"invalid number for meta tag: '{value}'")
        return None


def _try_parse_contrast(value: str, logger: Log) -> Literal["auto"] | float | None:
    if value == "auto":
        return "auto"
    try:
        return float(value)
    except ValueError:
        logger.warning(f"invalid value for contrast meta tag: '{value}'")
    return None
