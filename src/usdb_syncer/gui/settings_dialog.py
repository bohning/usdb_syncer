"""Dialog with app settings."""

from PySide6 import QtWidgets
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QWidget

from usdb_syncer import SongId, path_template, settings
from usdb_syncer.gui.forms.SettingsDialog import Ui_Dialog
from usdb_syncer.path_template import PathTemplate
from usdb_syncer.usdb_scraper import SessionManager
from usdb_syncer.usdb_song import UsdbSong

_FALLBACK_SONG = UsdbSong(
    song_id=SongId(3715),
    artist="Queen",
    title="Bohemian Rhapsody",
    genre="Genre",
    year=1975,
    creator="IC",
    edition="[SC]-Songs",
    language="English",
    golden_notes=True,
    rating=5,
    views=4050,
    sample_url="",
)


class SettingsDialog(Ui_Dialog, QDialog):
    """Dialog with app settings."""

    _path_template: PathTemplate | None = None

    def __init__(self, parent: QWidget, song: UsdbSong | None) -> None:
        super().__init__(parent=parent)
        self._song = song or _FALLBACK_SONG
        self.setupUi(self)
        self._populate_comboboxes()
        self._load_settings()
        self._setup_path_template()
        self._browser = self.comboBox_browser.currentData()
        self.label_video_embed_artwork.setVisible(False)
        self.checkBox_video_embed_artwork.setVisible(False)
        self.groupBox_reencode_video.setVisible(False)

    def _populate_comboboxes(self) -> None:
        combobox_settings = (
            (self.comboBox_encoding, settings.Encoding),
            (self.comboBox_line_endings, settings.Newline),
            (self.comboBox_cover_max_size, settings.CoverMaxSize),
            (self.comboBox_audio_format, settings.AudioFormat),
            (self.comboBox_audio_bitrate, settings.AudioBitrate),
            (self.comboBox_videocontainer, settings.VideoContainer),
            (self.comboBox_videoencoder, settings.VideoCodec),
            (self.comboBox_videoresolution, settings.VideoResolution),
            (self.comboBox_fps, settings.VideoFps),
        )
        for combobox, setting in combobox_settings:
            for item in setting:
                combobox.addItem(str(item), item)
        for browser in settings.Browser:
            self.comboBox_browser.addItem(QIcon(browser.icon()), str(browser), browser)

    def _load_settings(self) -> None:
        self.comboBox_browser.setCurrentIndex(
            self.comboBox_browser.findData(settings.get_browser())
        )
        self.groupBox_cover.setChecked(settings.get_cover())
        self.comboBox_cover_max_size.setCurrentIndex(
            self.comboBox_cover_max_size.findData(settings.get_cover_max_size())
        )
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
        self.checkBox_video_embed_artwork.setChecked(settings.get_video_embed_artwork())
        self.groupBox_background.setChecked(settings.get_background())
        self.checkBox_background_always.setChecked(settings.get_background_always())

    def _setup_path_template(self) -> None:
        self.edit_path_template.textChanged.connect(self._on_path_template_changed)
        self.edit_path_template.setText(str(settings.get_path_template()))
        self.edit_path_template.setPlaceholderText(PathTemplate.DEFAULT_STR)
        self.button_default_path_template.pressed.connect(self.edit_path_template.clear)
        self.button_insert_placeholder.pressed.connect(
            lambda: self.edit_path_template.insert(
                self.comboBox_placeholder.currentText()
            )
        )
        for item in path_template.PathTemplatePlaceholder:
            self.comboBox_placeholder.addItem(str(item), item)

    def _on_path_template_changed(self, text: str) -> None:
        try:
            self._path_template = (
                PathTemplate.parse(text) if text else PathTemplate.default()
            )
        except path_template.PathTemplateError as error:
            result = str(error)
            self._path_template = None
        else:
            result = str(self._path_template.evaluate(self._song).with_suffix(".txt"))
        self.edit_path_template_result.setText(result)

    def accept(self) -> None:
        if not self._save_settings():
            return
        if self._browser != self.comboBox_browser.currentData():
            SessionManager.reset_session()
        super().accept()

    def _save_settings(self) -> bool:
        settings.set_browser(self.comboBox_browser.currentData())
        settings.set_cover(self.groupBox_cover.isChecked())
        settings.set_cover_max_size(self.comboBox_cover_max_size.currentData())
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
        settings.set_video_embed_artwork(self.checkBox_video_embed_artwork.isChecked())
        settings.set_background(self.groupBox_background.isChecked())
        settings.set_background_always(self.checkBox_background_always.isChecked())
        if self._path_template:
            settings.set_path_template(self._path_template)
        else:
            QtWidgets.QMessageBox.warning(
                self, "Invalid setting", "Please provide a valid path template!"
            )
            return False
        return True
