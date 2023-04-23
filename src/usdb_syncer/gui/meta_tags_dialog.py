"""Dialog to create meta tags."""

from typing import Callable

from pyshorteners import Shortener
from pyshorteners.exceptions import (
    BadAPIResponseException,
    BadURLException,
    ExpandingErrorException,
    ShorteningErrorException,
)
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
from usdb_syncer.utils import extract_youtube_id

MAX_LEN = 255
URL_TAG_NAMES = ("cover_url", "background_url", "audio_url", "video_url")


class MetaTagsDialog(Ui_Dialog, QDialog):
    """Dialog to create meta tags."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self._output = "#VIDEO:"
        self._update_output()
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
        ):
            signal.connect(self._update_output)

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
            rotate=self.cover_rotation.value() or None,
            crop=self._cover_crop_meta_tag(),
            resize=self._cover_resize_meta_tag(),
            contrast="auto"
            if self.cover_contrast_auto.isChecked()
            else self.cover_contrast.value() or None,
        )

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
            video=_sanitize_video_url(self.video_url.text()) or None,
            audio=self._audio_source(),
            cover=self._cover_meta_tags(),
            background=self._background_meta_tags(),
            player1=self._p1_meta_tag(),
            player2=self._p2_meta_tag(),
            preview=self.preview_start.value() or None,
            medley=self._medley_tag(),
        )

    def _update_output(self) -> None:
        values = self._meta_tags()
        while True:
            self._output = f"#VIDEO:{values}"
            if len(self._output) <= MAX_LEN:
                break
            if not self._try_shorten_url(values):
                break
        self.output.setText(self._output)
        self.char_count.setText(f"{len(self._output)} / {MAX_LEN} characters")
        self.button_copy_to_clipboard.setEnabled(len(self._output) <= MAX_LEN)

    def _toggle_auto_contrast(self) -> None:
        auto = self.cover_contrast_auto.isChecked()
        self.cover_contrast.setEnabled(not auto)

    def _on_copy_to_clipboard(self) -> None:
        QGuiApplication.clipboard().setText(self._output)

    def _try_shorten_url(self, tags: MetaTags) -> bool:
        """True if some URL was shortened."""
        for url, setter in _urls_and_setters(tags):
            if cached := self._shortened_urls.get(url, ""):
                setter(cached)
                return True
            if len(url) < 30:
                continue
            if shortened := _try_shorten_url(url):
                self._shortened_urls[url] = shortened
                setter(shortened)
                return True
        return False


def _urls_and_setters(tags: MetaTags) -> list[tuple[str, Callable[[str], None]]]:
    """Returns meta tag urls by length in ascending order and a setter for each."""
    urls = []
    if tags.audio:
        urls.append((tags.audio, lambda s: setattr(tags, "audio", s)))
    if tags.video:
        urls.append((tags.video, lambda s: setattr(tags, "video", s)))
    if tags.cover:
        urls.append((tags.cover.source, lambda s: setattr(tags.cover, "source", s)))
    if background := tags.background:
        urls.append((background.source, lambda s: setattr(background, "source", s)))
    urls.sort(key=lambda u: len(u[0]), reverse=True)
    return urls


def _try_shorten_url(url: str) -> str:
    try:
        short = Shortener().tinyurl.short(url).removeprefix("https://")
    except (
        BadAPIResponseException,
        BadURLException,
        ExpandingErrorException,
        ShorteningErrorException,
    ):
        return ""
    if len(short) < len(url):
        return short
    return ""


def _sanitize_video_url(url: str) -> str:
    """Returns a YouTube id or sanitized URL."""
    return extract_youtube_id(url) or url


def _sanitize_image_url(url: str) -> str:
    """Returns a fanart id or sanitized URL and whether it uses HTTP."""
    return url.removeprefix("https://images.fanart.tv/fanart/")
