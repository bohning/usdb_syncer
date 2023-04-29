"""Dialog with app settings."""

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QWidget

from usdb_syncer import settings
from usdb_syncer.gui.forms.SettingsDialog import Ui_Dialog
from usdb_syncer.usdb_scraper import SessionManager


class SettingsDialog(Ui_Dialog, QDialog):
    """Dialog with app settings."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self._populate_comboboxes()
        self._load_settings()
        self._browser = self.comboBox_browser.currentData()

    def _populate_comboboxes(self) -> None:
        for encoding in settings.Encoding:
            self.comboBox_encoding.addItem(str(encoding), encoding)
        for newline in settings.Newline:
            self.comboBox_line_endings.addItem(str(newline), newline)
        for container in settings.AudioFormat:
            self.comboBox_audio_format.addItem(str(container), container)
        for bitrate in settings.AudioBitrate:
            self.comboBox_audio_bitrate.addItem(str(bitrate), bitrate)
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
        self.comboBox_audio_bitrate.setCurrentIndex(
            self.comboBox_audio_bitrate.findData(settings.get_audio_bitrate())
        )
        self.checkBox_audio_normalize.setChecked(settings.get_audio_normalize())
        self.checkBox_audio_embed_artwork.setChecked(settings.get_audio_embed_artwork())
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

    def accept(self) -> None:
        self._save_settings()
        if self._browser != self.comboBox_browser.currentData():
            SessionManager.reset_session()
        super().accept()

    def _save_settings(self) -> None:
        settings.set_browser(self.comboBox_browser.currentData())
        settings.set_cover(self.groupBox_cover.isChecked())
        settings.set_cover_max_size(self.cover_max_size.value())
        settings.set_txt(self.groupBox_songfile.isChecked())
        settings.set_encoding(self.comboBox_encoding.currentData())
        settings.set_newline(self.comboBox_line_endings.currentData())
        settings.set_audio(self.groupBox_audio.isChecked())
        settings.set_audio_format(self.comboBox_audio_format.currentData())
        settings.set_audio_bitrate(self.comboBox_audio_bitrate.currentData())
        settings.set_audio_normalize(self.checkBox_audio_normalize.isChecked())
        settings.set_audio_embed_artwork(self.checkBox_audio_embed_artwork.isChecked())
        settings.set_video(self.groupBox_video.isChecked())
        settings.set_video_format(self.comboBox_videocontainer.currentData())
        settings.set_video_format_new(self.comboBox_videoencoder.currentData())
        settings.set_video_reencode(self.groupBox_reencode_video.isChecked())
        settings.set_video_resolution(self.comboBox_videoresolution.currentData())
        settings.set_video_fps(self.comboBox_fps.currentData())
        settings.set_background(self.groupBox_background.isChecked())
        settings.set_background_always(self.checkBox_background_always.isChecked())
