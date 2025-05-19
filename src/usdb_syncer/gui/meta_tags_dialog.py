"""Dialog to create meta tags."""

import re
from typing import Literal

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QWidget

from usdb_syncer.gui.forms.MetaTagsDialog import Ui_Dialog
from usdb_syncer.meta_tags import (
    CropMetaTags,
    ImageMetaTags,
    MedleyTag,
    MetaTags,
    ResizeMetaTags,
)
from usdb_syncer.utils import extract_vimeo_id, extract_youtube_id

URL_TAG_NAMES = ("cover_url", "background_url", "audio_url", "video_url")


class MetaTagsDialog(Ui_Dialog, QDialog):
    """Dialog to create meta tags."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self._connect_signals()
        self._shortened_urls: dict[str, str] = {}

    def _connect_signals(self) -> None:
        for signal in (
            self.audio_url.textChanged,
            self.video_url.textChanged,
            self.cover_url.textChanged,
            self.cover_rotation.valueChanged,
            self.cover_contrast.valueChanged,
            self.cover_contrast_auto.toggled,
            self.cover_contrast_auto.toggled,
            self.cover_resize.valueChanged,
            self.cover_crop_left.valueChanged,
            self.cover_crop_top.valueChanged,
            self.cover_crop_width.valueChanged,
            self.cover_crop_height.valueChanged,
            self.background_url.textChanged,
            self.background_resize_width.valueChanged,
            self.background_resize_height.valueChanged,
            self.background_crop_left.valueChanged,
            self.background_crop_top.valueChanged,
            self.background_crop_width.valueChanged,
            self.background_crop_height.valueChanged,
            self.duet.toggled,
            self.duet_p1.textChanged,
            self.duet_p2.textChanged,
            self.preview_start.valueChanged,
            self.medley_start.valueChanged,
            self.medley_end.valueChanged,
            self.tags.textChanged,
        ):
            signal.connect(lambda: self.output.setText(f"#VIDEO:{self._meta_tags()}"))

        self.button_copy_to_clipboard.pressed.connect(self._on_copy_to_clipboard)

    def _audio_source(self) -> str | None:
        if not (source := self.audio_url.text()) or source == self.video_url.text():
            return None
        return _sanitize_video_url(source)

    def _cover_meta_tags(self) -> ImageMetaTags | None:
        if not (cover_source := _sanitize_image_url(self.cover_url.text())):
            return None
        return ImageMetaTags(
            source=cover_source,
            rotate=round(self.cover_rotation.value(), 2) or None,
            crop=self._cover_crop_meta_tag(),
            resize=self._cover_resize_meta_tag(),
            contrast=self._contrast(),
        )

    def _contrast(self) -> Literal["auto"] | float | None:
        if self.cover_contrast_auto.isChecked():
            return "auto"
        if (contrast := round(self.cover_contrast.value(), 2)) == 1:
            return None
        return contrast

    def _cover_crop_meta_tag(self) -> CropMetaTags | None:
        if not (width := self.cover_crop_width.value()) or not (
            height := self.cover_crop_height.value()
        ):
            return None
        left = self.cover_crop_left.value()
        upper = self.cover_crop_top.value()
        return CropMetaTags(
            left=left, upper=upper, right=left + width, lower=upper + height
        )

    def _cover_resize_meta_tag(self) -> ResizeMetaTags | None:
        if resize_value := self.cover_resize.value():
            return ResizeMetaTags(resize_value, resize_value)
        return None

    def _background_meta_tags(self) -> ImageMetaTags | None:
        if not (bg_source := _sanitize_image_url(self.background_url.text())):
            return None
        return ImageMetaTags(
            source=bg_source,
            crop=self._background_crop_meta_tag(),
            resize=self._background_resize_meta_tag(),
        )

    def _background_crop_meta_tag(self) -> CropMetaTags | None:
        if not (width := self.background_crop_width.value()) or not (
            height := self.background_crop_height.value()
        ):
            return None
        left = self.background_crop_left.value()
        upper = self.background_crop_top.value()
        return CropMetaTags(
            left=left, upper=upper, right=left + width, lower=upper + height
        )

    def _background_resize_meta_tag(self) -> ResizeMetaTags | None:
        if not (width := self.background_resize_width.value()) or not (
            height := self.background_resize_height.value()
        ):
            return None
        return ResizeMetaTags(width, height)

    def _medley_tag(self) -> MedleyTag | None:
        if (start := self.medley_start.value()) < (end := self.medley_end.value()):
            return MedleyTag(start, end)
        return None

    def _p1_meta_tag(self) -> str | None:
        if self.duet.isChecked():
            return self.duet_p1.text() or "P1"
        return None

    def _p2_meta_tag(self) -> str | None:
        if self.duet.isChecked():
            return self.duet_p2.text() or "P2"
        return None

    def _meta_tags(self) -> MetaTags:
        return MetaTags(
            audio=self._audio_source(),
            video=_sanitize_video_url(self.video_url.text()) or None,
            cover=self._cover_meta_tags(),
            background=self._background_meta_tags(),
            player1=self._p1_meta_tag(),
            player2=self._p2_meta_tag(),
            preview=round(self.preview_start.value(), 3) or None,
            medley=self._medley_tag(),
            tags=self.tags.text() or None,
        )

    def _toggle_auto_contrast(self) -> None:
        auto = self.cover_contrast_auto.isChecked()
        self.cover_contrast.setEnabled(not auto)

    def _on_copy_to_clipboard(self) -> None:
        QGuiApplication.clipboard().setText(self.output.text())


def _sanitize_video_url(url: str) -> str:
    """Returns a YouTube id, Vimeo id or sanitized URL."""
    return extract_youtube_id(url) or extract_vimeo_id(url) or url


def _sanitize_image_url(url: str) -> str:
    """Returns a fanart id or sanitized URL and whether it uses HTTP."""
    if "fanart.tv" in url:
        return url.removeprefix("https://images.fanart.tv/fanart/")
    if "m.media-amazon.com" in url:
        pattern = r"\._.*[^_\s]_"
        return re.sub(pattern, "", url)

    return url
