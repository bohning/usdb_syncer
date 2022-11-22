"""Dialog to create meta tags."""

from dataclasses import dataclass

from usdb_dl.meta_tags import encode_meta_tag_value
from usdb_dl.utils import extract_youtube_id


@dataclass
class MetaTag:
    """Minimal meta tag tuple."""

    key: str
    value: str

    def __str__(self) -> str:
        return f"{self.key}={self.value}"


@dataclass
class VideoCropTag:
    """How much to crop from the four sides of a video."""

    left: int
    right: int
    top: int
    bottom: int

    def __str__(self) -> str:
        if not any((self.left, self.right, self.top, self.bottom)):
            return ""
        return f"{self.left}-{self.right}-{self.top}-{self.bottom}"


@dataclass
class ImageCropTag:
    """The upper left corner and dimensions of an image for cropping."""

    left: int
    top: int
    width: int
    height: int

    def __str__(self) -> str:
        if not self.width or not self.height:
            return ""
        return f"{self.left}-{self.top}-{self.width}-{self.height}"


@dataclass
class MetaValues:
    """Dataclass for current values in the dialog."""

    video_url: str
    audio_url: str
    video_crop: VideoCropTag
    cover_url: str
    cover_crop: ImageCropTag
    cover_rotation: float
    cover_contrast_auto: bool
    cover_contrast: float
    cover_resize: int
    background_url: str
    background_resize_width: int
    background_resize_height: int
    background_crop: ImageCropTag
    duet: bool
    duet_p1: str
    duet_p2: str
    preview_start: float
    medley_start: int
    medley_end: int

    def meta_tags(self) -> list[str]:
        return [
            str(tag)
            for tag in (
                self._audio_meta_tag(),
                self._video_meta_tag(),
                self._video_crop_meta_tag(),
                *self._cover_url_meta_tags(),
                self._cover_rotation_meta_tag(),
                self._cover_contrast_meta_tag(),
                self._cover_resize_meta_tag(),
                self._cover_crop_meta_tag(),
                *self._background_url_meta_tags(),
                self._background_resize_meta_tag(),
                self._background_crop_meta_tag(),
                *self._player_meta_tags(),
                self._preview_meta_tag(),
                self._medley_meta_tag(),
            )
            if tag is not None
        ]

    def _audio_meta_tag(self) -> MetaTag | None:
        if self.audio_url and self.audio_url != self.video_url:
            return MetaTag(key="a", value=_sanitize_video_url(self.audio_url))
        return None

    def _video_meta_tag(self) -> MetaTag | None:
        if self.video_url:
            return MetaTag(key="v", value=_sanitize_video_url(self.video_url))
        return None

    def _video_crop_meta_tag(self) -> MetaTag | None:
        if self.video_url and (value := str(self.video_crop)):
            return MetaTag(key="v-crop", value=value)
        return None

    def _player_meta_tags(self) -> tuple[MetaTag, ...]:
        if self.duet:
            return (
                MetaTag(key="p1", value=encode_meta_tag_value(self.duet_p1) or "P1"),
                MetaTag(key="p2", value=encode_meta_tag_value(self.duet_p2) or "P2"),
            )
        return tuple()

    def _cover_url_meta_tags(self) -> list[MetaTag]:
        tags = []
        if self.cover_url:
            url, http = _sanitize_image_url(self.cover_url)
            tags.append(MetaTag(key="co", value=url))
            if http:
                tags.append(MetaTag(key="co-protocol", value="http"))
        return tags

    def _cover_rotation_meta_tag(self) -> MetaTag | None:
        if self.cover_url and self.cover_rotation:
            return MetaTag(key="co-rotate", value=str(self.cover_rotation))
        return None

    def _cover_contrast_meta_tag(self) -> MetaTag | None:
        if self.cover_url:
            if self.cover_contrast_auto:
                return MetaTag(key="co-contrast", value="auto")
            if self.cover_contrast != 1:
                return MetaTag(key="co-contrast", value=str(self.cover_contrast))
        return None

    def _cover_resize_meta_tag(self) -> MetaTag | None:
        if self.cover_url and self.cover_resize:
            return MetaTag(key="co-resize", value=f"{self.cover_resize}")
        return None

    def _cover_crop_meta_tag(self) -> MetaTag | None:
        if self.cover_url and (value := str(self.cover_crop)):
            return MetaTag(key="co-crop", value=value)
        return None

    def _background_url_meta_tags(self) -> list[MetaTag]:
        tags = []
        if self.background_url:
            url, http = _sanitize_image_url(self.background_url)
            tags.append(MetaTag(key="bg", value=url))
            if http:
                tags.append(MetaTag(key="bg-protocol", value="http"))
        return tags

    def _background_resize_meta_tag(self) -> MetaTag | None:
        if (
            self.background_url
            and self.background_resize_width
            and self.background_resize_height
        ):
            return MetaTag(
                key="bg-resize",
                value=f"{self.background_resize_width}-{self.background_resize_height}",
            )
        return None

    def _background_crop_meta_tag(self) -> MetaTag | None:
        if self.background_url and (value := str(self.background_crop)):
            return MetaTag(key="bg-crop", value=value)
        return None

    def _preview_meta_tag(self) -> MetaTag | None:
        if self.preview_start:
            return MetaTag(key="preview", value=str(self.preview_start))
        return None

    def _medley_meta_tag(self) -> MetaTag | None:
        if self.medley_start < self.medley_end:
            return MetaTag(key="medley", value=f"{self.medley_start}-{self.medley_end}")
        return None


def video_tag_from_values(values: MetaValues) -> str:
    return "#VIDEO:" + ",".join(values.meta_tags())


def _sanitize_video_url(url: str) -> str:
    """Returns a YouTube id or sanitized URL."""
    return extract_youtube_id(url) or _sanitize_url(url)


def _sanitize_image_url(url: str) -> tuple[str, bool]:
    """Returns a fanart id or sanitized URL and whether it uses HTTP."""
    http = url.startswith("http://")
    url = url.removeprefix("http://").removeprefix("https://images.fanart.tv/fanart/")
    return _sanitize_url(url), http


def _sanitize_url(url: str) -> str:
    """Remove or escape characters with special meaning or which USDB can't handle."""
    return encode_meta_tag_value(url.removeprefix("https://"))
