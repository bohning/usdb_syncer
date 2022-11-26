"""Dialog to create meta tags."""


from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QWidget

from usdb_syncer.gui.forms.MetaTagsDialog import Ui_Dialog
from usdb_syncer.meta_tags.serializer import (
    ImageCropTag,
    MetaValues,
    VideoCropTag,
    video_tag_from_values,
)


class MetaTagsDialog(Ui_Dialog, QDialog):
    """Dialog to create meta tags."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self._output = "#VIDEO:"
        self._update_output()
        self._connect_signals()

    def _connect_signals(self) -> None:
        self.audio_url.textChanged.connect(self._update_output)

        self.video_url.textChanged.connect(self._update_output)
        self.video_crop_left.valueChanged.connect(self._update_output)
        self.video_crop_right.valueChanged.connect(self._update_output)
        self.video_crop_top.valueChanged.connect(self._update_output)
        self.video_crop_bottom.valueChanged.connect(self._update_output)

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

        self.preview_start.valueChanged.connect(self._update_output)
        self.medley_start.valueChanged.connect(self._update_output)
        self.medley_end.valueChanged.connect(self._update_output)

        self.button_copy_to_clipboard.pressed.connect(self._on_copy_to_clipboard)

    def _meta_values(self) -> MetaValues:
        return MetaValues(
            video_url=self.video_url.text(),
            audio_url=self.audio_url.text(),
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
            preview_start=self.preview_start.value(),
            medley_start=self.medley_start.value(),
            medley_end=self.medley_end.value(),
        )

    def _update_output(self) -> None:
        values = self._meta_values()
        self._output = video_tag_from_values(values)
        self.output.setText(self._output)
        self.char_count.setText(f"{len(self._output)} / 262 characters")

    def _toggle_auto_contrast(self) -> None:
        auto = self.cover_contrast_auto.isChecked()
        self.cover_contrast.setEnabled(not auto)

    def _on_copy_to_clipboard(self) -> None:
        QGuiApplication.clipboard().setText(self._output)