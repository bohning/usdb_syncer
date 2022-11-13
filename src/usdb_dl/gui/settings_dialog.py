"""Dialog with app settings."""

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QWidget

from usdb_dl import settings
from usdb_dl.gui.forms.SettingsDialog import Ui_Dialog


class SettingsDialog(Ui_Dialog, QDialog):
    """Dialog with app settings."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self._populate_comboboxes()
        self._load_settings()
        self.accepted.connect(self._save_settings)  # type: ignore

    def _populate_comboboxes(self) -> None:
        for encoding in settings.Encoding:
            self.comboBox_encoding.addItem(str(encoding), encoding)
        for newline in settings.Newline:
            self.comboBox_line_endings.addItem(str(newline), newline)
        for container in settings.AudioContainer:
            self.comboBox_audio_format.addItem(str(container), container)
        for codec in settings.AudioCodec:
            self.comboBox_audio_conversion_format.addItem(str(codec), codec)
        for browser in settings.Browser:
            self.comboBox_browser.addItem(QIcon(browser.icon()), str(browser), browser)
        for video_container in settings.VideoContainer:
            self.comboBox_videocontainer.addItem(str(video_container), video_container)
        for video_codec in settings.VideoCodec:
            self.comboBox_videoencoder.addItem(str(video_codec), video_codec)
        for resolution in settings.VideoResolution:
            self.comboBox_videoresolution.addItem(str(resolution), resolution)
        for fps in settings.VideoFps:
            self.comboBox_fps.addItem(str(fps), fps)

    def _load_settings(self) -> None:
        self.comboBox_browser.setCurrentIndex(
            self.comboBox_browser.findData(settings.get_browser())
        )
        self.groupBox_cover.setChecked(settings.get_cover())
        self.cover_max_size.setValue(settings.get_cover_max_size())
        self.groupBox_songfile.setChecked(settings.get_txt())
        self.comboBox_encoding.setCurrentIndex(
            self.comboBox_encoding.findData(settings.get_encoding())
        )
        self.comboBox_line_endings.setCurrentIndex(
            self.comboBox_line_endings.findData(settings.get_newline())
        )
        self.groupBox_audio.setChecked(settings.get_audio())
        self.comboBox_audio_format.setCurrentIndex(
            self.comboBox_audio_format.findData(settings.get_audio_format())
        )
        self.comboBox_audio_conversion_format.setCurrentIndex(
            self.comboBox_audio_conversion_format.findData(
                settings.get_audio_format_new()
            )
        )
        self.groupBox_reencode_audio.setChecked(settings.get_audio_reencode())
        self.groupBox_video.setChecked(settings.get_video())
        self.comboBox_videocontainer.setCurrentIndex(
            self.comboBox_videocontainer.findData(settings.get_video_format())
        )
        self.comboBox_videoencoder.setCurrentIndex(
            self.comboBox_videoencoder.findData(settings.get_video_format_new())
        )
        self.groupBox_reencode_video.setChecked(settings.get_video_reencode())
        self.comboBox_videoresolution.setCurrentIndex(
            self.comboBox_videoresolution.findData(settings.get_video_resolution())
        )
        self.comboBox_fps.setCurrentIndex(
            self.comboBox_fps.findData(settings.get_video_fps())
        )
        self.groupBox_background.setChecked(settings.get_background())
        self.checkBox_background_always.setChecked(settings.get_background_always())

    def _save_settings(self) -> None:
        settings.set_browser(self.comboBox_browser.currentData())
        settings.set_cover(self.groupBox_cover.isChecked())
        settings.set_cover_max_size(self.cover_max_size.value())
        settings.set_txt(self.groupBox_songfile.isChecked())
        settings.set_encoding(self.comboBox_encoding.currentData())
        settings.set_newline(self.comboBox_line_endings.currentData())
        settings.set_audio(self.groupBox_audio.isChecked())
        settings.set_audio_format(self.comboBox_audio_format.currentData())
        settings.set_audio_format_new(
            self.comboBox_audio_conversion_format.currentData()
        )
        settings.set_audio_reencode(self.groupBox_reencode_audio.isChecked())
        settings.set_video(self.groupBox_video.isChecked())
        settings.set_video_format(self.comboBox_videocontainer.currentData())
        settings.set_video_format_new(self.comboBox_videoencoder.currentData())
        settings.set_video_reencode(self.groupBox_reencode_video.isChecked())
        settings.set_video_resolution(self.comboBox_videoresolution.currentData())
        settings.set_video_fps(self.comboBox_fps.currentData())
        settings.set_background(self.groupBox_background.isChecked())
        settings.set_background_always(self.checkBox_background_always.isChecked())
