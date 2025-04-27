"""Dataclasses and parse logic for meta tags from a txt's video tag."""

from __future__ import annotations

from typing import Literal

import attrs

from usdb_syncer.logger import Logger

# Characters that have special meaning for the meta tag syntax and therefore
# must be escaped. Escaping is done with percent encoding.
META_TAG_ESCAPES = ((",", "%2C"),)


def encode_meta_tag_value(meta_tag: str) -> str:
    """Escape special characters inside the value part of a meta tag."""
    for char, escape in META_TAG_ESCAPES:
        meta_tag = meta_tag.replace(char, escape)
    return meta_tag


def decode_meta_tag_value(meta_tag: str) -> str:
    """Unescape special characters inside the value part of a meta tag."""

    for char, escape in META_TAG_ESCAPES:
        meta_tag = meta_tag.replace(escape, char)
    return meta_tag


@attrs.define
class CropMetaTags:
    """Meta tags for cropping media."""

    left: int
    upper: int
    right: int
    lower: int

    @classmethod
    def try_parse(cls, value: str, logger: Logger) -> CropMetaTags | None:
        try:
            left, upper, width, height = map(int, value.split("-"))
        except ValueError:
            logger.warning(f"invalid value for crop meta tag: '{value}'")
            return None
        return cls(left, upper, left + width, upper + height)

    def to_str(self, prefix: str) -> str:
        width = self.right - self.left
        height = self.lower - self.upper
        value = f"{self.left}-{self.upper}-{width}-{height}"
        return _key_value_str(f"{prefix}-crop", value) or ""


@attrs.define
class ResizeMetaTags:
    """Meta tags for resizing media."""

    width: int
    height: int

    @classmethod
    def try_parse(cls, value: str, logger: Logger) -> ResizeMetaTags | None:
        try:
            if "-" in value:
                width, height = map(int, value.split("-"))
            else:
                width = height = int(value)
        except ValueError:
            logger.warning(f"invalid value for resize meta tag: '{value}'")
            return None
        return cls(width, height)

    def to_str(self, prefix: str) -> str:
        if self.width != self.height:
            value = f"{self.width}-{self.height}"
        else:
            value = str(self.width)
        return _key_value_str(f"{prefix}-resize", value) or ""


@attrs.define
class ImageMetaTags:
    """Meta tags relating to the cover or background image."""

    source: str
    rotate: float | None = None
    crop: CropMetaTags | None = None
    resize: ResizeMetaTags | None = None
    contrast: Literal["auto"] | float | None = None

    def source_url(self, logger: Logger) -> str:
        if "://" in self.source:
            if "fanart.tv" in self.source:
                logger.debug(
                    "Metatags contain a full fanart.tv URL instead of a fanart id only."
                )
                self.source = self.source.replace(
                    "images.fanart.tv", "assets.fanart.tv"
                )
            return self.source
        if "/" in self.source:
            logger.debug(f"{self.source} is missing the protocol.")
            return f"https://{self.source}"
        return f"https://assets.fanart.tv/fanart/{self.source}"

    def image_processing(self) -> bool:
        """True if there is data for image processing."""
        return any((self.rotate, self.crop, self.resize, self.contrast))

    def to_str(self, prefix: str) -> str:
        return _join_tags(
            _key_value_str(prefix, self.source),
            _key_value_str(f"{prefix}-rotate", self.rotate),
            self.crop.to_str(prefix) if self.crop else None,
            self.resize.to_str(prefix) if self.resize else None,
            _key_value_str(f"{prefix}-contrast", self.contrast),
        )


@attrs.define
class MedleyTag:
    """A tag with medley start and end."""

    start: int
    end: int

    @classmethod
    def try_parse(cls, value: str, logger: Logger) -> MedleyTag | None:
        try:
            start, end = map(int, value.split("-"))
        except ValueError:
            logger.warning(f"invalid value for medley meta tag: '{value}'")
            return None
        return cls(start, end)

    def __str__(self) -> str:
        return _key_value_str("medley", f"{self.start}-{self.end}") or ""


@attrs.define
class MetaTags:
    """Additional resource parameters from an overloaded video tag. Such an overloaded
    tag could look like:
    #VIDEO:a=example,co=foobar.jpg,bg=background.jpg
    """

    audio: str | None = None
    video: str | None = None
    cover: ImageMetaTags | None = None
    background: ImageMetaTags | None = None
    player1: str | None = None
    player2: str | None = None
    preview: float | None = None
    medley: MedleyTag | None = None
    tags: str | None = None

    @classmethod
    def parse(cls, video_tag: str, logger: Logger) -> MetaTags:
        meta_tags = cls()
        if "=" not in video_tag:
            # probably a regular video file name and not a meta tag
            return meta_tags
        for pair in video_tag.split(","):
            if "=" not in pair:
                logger.warning(f"missing key or value for meta tag: '{pair}'")
                continue
            key, value = pair.split("=", maxsplit=1)
            meta_tags._parse_key_value_pair(key, value, logger)
        return meta_tags

    def _parse_key_value_pair(  # noqa: C901
        self, key: str, value: str, logger: Logger
    ) -> None:
        value = decode_meta_tag_value(value)
        match key:
            case "v":
                self.video = value
            case "v-trim" | "v-crop" | "co-protocol" | "bg-protocol":
                logger.debug(f"Unused meta tag found: {key}={value}")
            case "a":
                self.audio = value
            case "co":
                self.cover = ImageMetaTags(source=value)
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
            case "tags":
                self.tags = value
            case _:
                logger.warning(f"unknown key for meta tag: '{key}={value}'")

    def is_audio_only(self) -> bool:
        """True if a resource is explicitly set for audio only."""
        return bool(self.audio and not self.video)

    def __str__(self) -> str:
        return _join_tags(
            _key_value_str("a", self.audio),
            _key_value_str("v", self.video),
            self.cover.to_str("co") if self.cover else None,
            self.background.to_str("bg") if self.background else None,
            _key_value_str("p1", self.player1),
            _key_value_str("p2", self.player2),
            _key_value_str("preview", self.preview),
            str(self.medley) if self.medley else None,
            _key_value_str("tags", self.tags),
        )


def _key_value_str(key: str, value: str | float | None) -> str | None:
    return None if value is None else f"{key}={encode_meta_tag_value(str(value))}"


def _join_tags(*meta_tags: str | None) -> str:
    return ",".join(filter(None, meta_tags))


def _try_parse_float(value: str, logger: Logger) -> float | None:
    try:
        return float(value)
    except ValueError:
        logger.warning(f"invalid number for meta tag: '{value}'")
        return None


def _try_parse_contrast(value: str, logger: Logger) -> Literal["auto"] | float | None:
    if value == "auto":
        return "auto"
    try:
        return float(value)
    except ValueError:
        logger.warning(f"invalid value for contrast meta tag: '{value}'")
    return None
