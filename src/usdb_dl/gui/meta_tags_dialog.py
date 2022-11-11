"""Dialog to create meta tags."""

from dataclasses import dataclass

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QWidget
from pytube import extract
from pytube.exceptions import RegexMatchError

from usdb_dl.gui.forms.MetaTagsDialog import Ui_Dialog


@dataclass
class MetaTag:
    """Minimal meta tag tuple."""

    key: str
    value: str

    def __str__(self) -> str:
        return f"{self.key}={self.value}"


@dataclass
class TrimPoint:
    """The start or end point for trimming a video."""

    mins: int
    secs: float
    use_frames: bool
    frames: int

    def __str__(self) -> str:
        if self.use_frames:
            if self.frames:
                return str(self.frames)
        elif self.mins:
            return f"{self.mins}:{self.secs}"
        elif self.secs:
            return str(self.secs)
        return ""


@dataclass
class VideoCropTag:
    """How much to crop from the four sides of a video."""

    left: int
    right: int
    top: int
    bottom: int

    def __str__(self) -> str:
        if not all((self.left, self.right, self.top, self.bottom)):
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
class UiValues:
    """Dataclass for current values in the dialog."""

    video_url: str
    audio_url: str
    video_trim_start: TrimPoint
    video_trim_end: TrimPoint
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

    def meta_tags(self) -> list[str]:
        return [
            str(tag)
            for tag in (
                self._audio_meta_tag(),
                self._video_meta_tag(),
                self._video_crop_meta_tag(),
                self._video_trim_meta_tag(),
                *self._cover_url_meta_tags(),
                self._cover_rotation_meta_tag(),
                self._cover_contrast_meta_tag(),
                self._cover_resize_meta_tag(),
                self._cover_crop_meta_tag(),
                *self._background_url_meta_tags(),
                self._background_resize_meta_tag(),
                self._background_crop_meta_tag(),
                *self._player_meta_tags(),
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

    def _video_trim_meta_tag(self) -> MetaTag | None:
        if self.video_url:
            start = str(self.video_trim_start)
            end = str(self.video_trim_end)
            if start or end:
                return MetaTag(key="v-trim", value=f"{start}-{end}")
        return None

    def _player_meta_tags(self) -> tuple[MetaTag, ...]:
        if self.duet:
            return (
                MetaTag(key="p1", value=self.duet_p1 or "P1"),
                MetaTag(key="p2", value=self.duet_p2 or "P2"),
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


class MetaTagsDialog(Ui_Dialog, QDialog):
    """Dialog to create meta tags."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self._output = "#VIDEO:"

        self.audio_url.textChanged.connect(self._update_output)

        self.video_url.textChanged.connect(self._update_output)
        self.video_trim_start_mins.valueChanged.connect(self._update_output)
        self.video_trim_start_secs.valueChanged.connect(self._update_output)
        self.video_trim_use_start_frames.toggled.connect(self._update_output)
        self.video_trim_use_start_frames.toggled.connect(self._toggle_start_trim_units)
        self.video_trim_start_frames.valueChanged.connect(self._update_output)
        self.video_trim_end_mins.valueChanged.connect(self._update_output)
        self.video_trim_end_secs.valueChanged.connect(self._update_output)
        self.video_trim_use_end_frames.toggled.connect(self._update_output)
        self.video_trim_use_end_frames.toggled.connect(self._toggle_end_trim_units)
        self.video_trim_end_frames.valueChanged.connect(self._update_output)

        self.cover_url.textChanged.connect(self._update_output)
        self.cover_rotation.valueChanged.connect(self._update_output)
        self.cover_contrast.valueChanged.connect(self._update_output)
        self.cover_contrast_auto.toggled.connect(self._update_output)
        self.cover_contrast_auto.toggled.connect(self._toggle_auto_contrast)
        self.cover_resize.valueChanged.connect(self._update_output)
        self.cover_crop_left.valueChanged.connect(self._update_output)
        self.cover_crop_top.valueChanged.connect(self._update_output)
        self.cover_crop_width.valueChanged.connect(self._update_output)
        self.cover_crop_height.valueChanged.connect(self._update_output)

        self.background_url.textChanged.connect(self._update_output)
        self.background_resize_width.valueChanged.connect(self._update_output)
        self.background_resize_height.valueChanged.connect(self._update_output)
        self.background_crop_left.valueChanged.connect(self._update_output)
        self.background_crop_top.valueChanged.connect(self._update_output)
        self.background_crop_width.valueChanged.connect(self._update_output)
        self.background_crop_height.valueChanged.connect(self._update_output)

        self.duet.toggled.connect(self._update_output)
        self.duet_p1.textChanged.connect(self._update_output)
        self.duet_p2.textChanged.connect(self._update_output)

        self.button_copy_to_clipboard.pressed.connect(self._on_copy_to_clipboard)

    def _ui_values(self) -> UiValues:
        return UiValues(
            video_url=self.video_url.text(),
            audio_url=self.audio_url.text(),
            video_trim_start=TrimPoint(
                mins=self.video_trim_start_mins.value(),
                secs=self.video_trim_start_secs.value(),
                use_frames=self.video_trim_use_start_frames.isChecked(),
                frames=self.video_trim_start_frames.value(),
            ),
            video_trim_end=TrimPoint(
                mins=self.video_trim_end_mins.value(),
                secs=self.video_trim_end_secs.value(),
                use_frames=self.video_trim_use_end_frames.isChecked(),
                frames=self.video_trim_end_frames.value(),
            ),
            video_crop=VideoCropTag(
                left=self.video_crop_left.value(),
                right=self.video_crop_right.value(),
                top=self.video_crop_top.value(),
                bottom=self.video_crop_bottom.value(),
            ),
            cover_url=self.cover_url.text(),
            cover_rotation=self.cover_rotation.value(),
            cover_resize=self.cover_resize.value(),
            cover_contrast_auto=self.cover_contrast_auto.isChecked(),
            cover_contrast=self.cover_contrast.value(),
            cover_crop=ImageCropTag(
                left=self.cover_crop_left.value(),
                top=self.cover_crop_top.value(),
                width=self.cover_crop_width.value(),
                height=self.cover_crop_height.value(),
            ),
            background_url=self.background_url.text(),
            background_resize_width=self.background_resize_width.value(),
            background_resize_height=self.background_resize_height.value(),
            background_crop=ImageCropTag(
                left=self.background_crop_left.value(),
                top=self.background_crop_top.value(),
                width=self.background_crop_width.value(),
                height=self.background_crop_height.value(),
            ),
            duet=self.duet.isChecked(),
            duet_p1=self.duet_p1.text(),
            duet_p2=self.duet_p2.text(),
        )

    def _update_output(self) -> None:
        values = self._ui_values()
        self._output = "#VIDEO:" + ",".join(values.meta_tags())
        self.output.setText(self._output)
        self.char_count.setText(f"{len(self._output)} / 170 characters")

    def _toggle_start_trim_units(self) -> None:
        frames = self.video_trim_use_start_frames.isChecked()
        self.video_trim_start_mins.setEnabled(not frames)
        self.video_trim_start_secs.setEnabled(not frames)
        self.video_trim_start_frames.setEnabled(frames)

    def _toggle_end_trim_units(self) -> None:
        frames = self.video_trim_use_end_frames.isChecked()
        self.video_trim_end_mins.setEnabled(not frames)
        self.video_trim_end_secs.setEnabled(not frames)
        self.video_trim_end_frames.setEnabled(frames)

    def _toggle_auto_contrast(self) -> None:
        auto = self.cover_contrast_auto.isChecked()
        self.cover_contrast.setEnabled(not auto)

    def _on_copy_to_clipboard(self) -> None:
        QGuiApplication.clipboard().setText(self._output)


def _sanitize_video_url(url: str) -> str:
    """Returns a YouTube id or sanitized URL."""
    try:
        return extract.video_id(url)
    except RegexMatchError:
        return _sanitize_url(url)


def _sanitize_image_url(url: str) -> tuple[str, bool]:
    """Returns a fanart id or sanitized URL and whether it uses HTTP."""
    http = url.startswith("http://")
    url = url.removeprefix("http://").removeprefix("https://images.fanart.tv/fanart/")
    return _sanitize_url(url), http


def _sanitize_url(url: str) -> str:
    """Remove or escape `/` and `:`, which USDB can't handle."""
    return url.removeprefix("https://").replace("/", "%2F").replace(":", "%3A")
