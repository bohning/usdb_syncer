"""Dialog with app settings."""

import sys
from pathlib import Path
from typing import assert_never

from PySide6 import QtWidgets
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QWidget

from usdb_syncer import SongId, path_template, settings
from usdb_syncer.gui import icons, theme
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
        apply_btn = self.buttonBox.button(QDialogButtonBox.StandardButton.Apply)
        apply_btn.clicked.connect(self.apply)
        self._browser = self.comboBox_browser.currentData()
        self.groupBox_reencode_video.setVisible(False)
        if sys.platform != "win32":
            self.groupBox_vocaluxe.setVisible(False)
        self.pushButton_browse_karedi.clicked.connect(
            lambda: self._set_location(settings.SupportedApps.KAREDI)
        )
        self.pushButton_browse_performous.clicked.connect(
            lambda: self._set_location(settings.SupportedApps.PERFORMOUS)
        )
        self.pushButton_browse_ultrastar_manager.clicked.connect(
            lambda: self._set_location(settings.SupportedApps.ULTRASTAR_MANAGER)
        )
        self.pushButton_browse_usdx.clicked.connect(
            lambda: self._set_location(settings.SupportedApps.USDX)
        )
        self.pushButton_browse_vocaluxe.clicked.connect(
            lambda: self._set_location(settings.SupportedApps.VOCALUXE)
        )
        self.pushButton_browse_yass_reloaded.clicked.connect(
            lambda: self._set_location(settings.SupportedApps.YASS_RELOADED)
        )
        self.comboBox_theme.currentIndexChanged.connect(
            self._set_theme_settings_enabled
        )
        self._set_theme_settings_enabled()

    def _set_theme_settings_enabled(self) -> None:
        hidden = self.comboBox_theme.currentData() == settings.Theme.SYSTEM
        self.label_primary_color.setHidden(hidden)
        self.comboBox_primary_color.setHidden(hidden)
        self.checkBox_colored_background.setHidden(hidden)

    def _set_location(self, app: settings.SupportedApps) -> None:
        path = self._get_executable(app)
        text = str(path) if path is not None else ""
        match app:
            case settings.SupportedApps.KAREDI:
                self.lineEdit_path_karedi.setText(text)
            case settings.SupportedApps.PERFORMOUS:
                self.lineEdit_path_performous.setText(text)
            case settings.SupportedApps.ULTRASTAR_MANAGER:
                self.lineEdit_path_ultrastar_manager.setText(text)
            case settings.SupportedApps.USDX:
                self.lineEdit_path_usdx.setText(text)
            case settings.SupportedApps.VOCALUXE:
                self.lineEdit_path_vocaluxe.setText(text)
            case settings.SupportedApps.YASS_RELOADED:
                self.lineEdit_path_yass_reloaded.setText(text)
            case _ as unreachable:
                assert_never(unreachable)

    def _get_executable(self, app: settings.SupportedApps) -> Path | None:
        filt = "*"
        directory = ""
        match sys.platform:
            case "win32":
                filt = "*.exe"
            case "darwin":
                directory = "/Applications"
                filt = "*.app"
        if app in (settings.SupportedApps.KAREDI, settings.SupportedApps.YASS_RELOADED):
            filt += " *.jar"
        filename = QFileDialog.getOpenFileName(
            self, f"Select {app} executable", directory, filt
        )[0]
        # dialog is hidden by main window on macOS if file picker was cancelled
        self.raise_()
        if filename == "":
            return None
        path = Path(filename)
        if path.suffix != ".app":
            return path
        if (
            full_path := path.joinpath("Contents", "MacOS", app.executable_name())
        ).exists():
            return full_path
        return None

    def _populate_comboboxes(self) -> None:
        combobox_settings = (
            (self.comboBox_theme, settings.Theme),
            (self.comboBox_primary_color, settings.Color),
            (self.comboBox_encoding, settings.Encoding),
            (self.comboBox_line_endings, settings.Newline),
            (self.comboBox_format_version, settings.FormatVersion),
            (self.comboBox_fix_linebreaks, settings.FixLinebreaks),
            (self.comboBox_fix_spaces, settings.FixSpaces),
            (self.comboBox_cover_max_size, settings.CoverMaxSize),
            (self.comboBox_ytdlp_rate_limit, settings.YtdlpRateLimit),
            (self.comboBox_audio_format, settings.AudioFormat),
            (self.comboBox_audio_bitrate, settings.AudioBitrate),
            (self.comboBox_audio_normalization, settings.AudioNormalization),
            (self.comboBox_videocontainer, settings.VideoContainer),
            (self.comboBox_videoencoder, settings.VideoCodec),
            (self.comboBox_videoresolution, settings.VideoResolution),
            (self.comboBox_fps, settings.VideoFps),
        )
        for combobox, setting in combobox_settings:
            for item in setting:
                combobox.addItem(str(item), item)
        for browser in settings.Browser:
            if icon := icons.browser_icon(browser):
                self.comboBox_browser.addItem(icon, str(browser), browser)
            else:
                self.comboBox_browser.addItem(str(browser), browser)

    def _load_settings(self) -> None:
        self.comboBox_theme.setCurrentIndex(
            self.comboBox_theme.findData(settings.get_theme())
        )
        self.comboBox_primary_color.setCurrentIndex(
            self.comboBox_primary_color.findData(settings.get_primary_color())
        )
        self.checkBox_colored_background.setChecked(settings.get_colored_background())
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
        self.comboBox_format_version.setCurrentIndex(
            self.comboBox_format_version.findData(settings.get_version())
        )
        self.comboBox_fix_linebreaks.setCurrentIndex(
            self.comboBox_fix_linebreaks.findData(settings.get_fix_linebreaks())
        )
        self.checkBox_fix_first_words_capitalization.setChecked(
            settings.get_fix_first_words_capitalization()
        )
        self.comboBox_fix_spaces.setCurrentIndex(
            self.comboBox_fix_spaces.findData(settings.get_fix_spaces())
        )
        self.checkBox_fix_quotation_marks.setChecked(settings.get_fix_quotation_marks())
        self.spinBox_throttling_threads.setValue(settings.get_throttling_threads())
        self.comboBox_ytdlp_rate_limit.setCurrentIndex(
            self.comboBox_ytdlp_rate_limit.findData(settings.get_ytdlp_rate_limit())
        )
        self.groupBox_audio.setChecked(settings.get_audio())
        self.comboBox_audio_format.setCurrentIndex(
            self.comboBox_audio_format.findData(settings.get_audio_format())
        )
        self.comboBox_audio_bitrate.setCurrentIndex(
            self.comboBox_audio_bitrate.findData(settings.get_audio_bitrate())
        )
        self.comboBox_audio_normalization.setCurrentIndex(
            self.comboBox_audio_normalization.findData(
                settings.get_audio_normalization()
            )
        )
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
        if (path := settings.get_app_path(settings.SupportedApps.KAREDI)) is not None:
            self.lineEdit_path_karedi.setText(str(path))
        if (
            path := settings.get_app_path(settings.SupportedApps.PERFORMOUS)
        ) is not None:
            self.lineEdit_path_performous.setText(str(path))
        if (
            path := settings.get_app_path(settings.SupportedApps.ULTRASTAR_MANAGER)
        ) is not None:
            self.lineEdit_path_ultrastar_manager.setText(str(path))
        if (path := settings.get_app_path(settings.SupportedApps.USDX)) is not None:
            self.lineEdit_path_usdx.setText(str(path))
        if (path := settings.get_app_path(settings.SupportedApps.VOCALUXE)) is not None:
            self.lineEdit_path_vocaluxe.setText(str(path))
        if (
            path := settings.get_app_path(settings.SupportedApps.YASS_RELOADED)
        ) is not None:
            self.lineEdit_path_yass_reloaded.setText(str(path))
        self.checkBox_discord_allowed.setChecked(settings.get_discord_allowed())

    def _setup_path_template(self) -> None:
        self.edit_path_template.textChanged.connect(self._on_path_template_changed)
        self.edit_path_template.setText(str(settings.get_path_template()))
        self.edit_path_template.setPlaceholderText(PathTemplate.default_str)
        self.button_default_path_template.pressed.connect(self.edit_path_template.clear)
        self.button_insert_placeholder.pressed.connect(
            lambda: self.edit_path_template.insert(
                self.comboBox_placeholder.currentText()
            )
        )
        for item in path_template.PathTemplatePlaceholder:
            self.comboBox_placeholder.addItem(str(item), item)
        for key in path_template.PathTemplateCustomPlaceholder.options():
            self.comboBox_placeholder.addItem(str(key))

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

    def apply(self) -> None:
        self._save_settings()
        if self._browser != self.comboBox_browser.currentData():
            SessionManager.reset_session()

    def accept(self) -> None:
        if not self._save_settings():
            return
        if self._browser != self.comboBox_browser.currentData():
            SessionManager.reset_session()
        super().accept()

    def _save_settings(self) -> bool:
        new_theme = self.comboBox_theme.currentData()
        new_primary_color = self.comboBox_primary_color.currentData()
        colored_background = self.checkBox_colored_background.isChecked()
        settings.set_theme(new_theme)
        settings.set_primary_color(new_primary_color)
        settings.set_colored_background(colored_background)
        theme.apply_theme(new_theme, new_primary_color, colored_background)
        settings.set_browser(self.comboBox_browser.currentData())
        settings.set_cover(self.groupBox_cover.isChecked())
        settings.set_cover_max_size(self.comboBox_cover_max_size.currentData())
        settings.set_txt(self.groupBox_songfile.isChecked())
        settings.set_encoding(self.comboBox_encoding.currentData())
        settings.set_newline(self.comboBox_line_endings.currentData())
        settings.set_version(self.comboBox_format_version.currentData())
        settings.set_fix_linebreaks(self.comboBox_fix_linebreaks.currentData())
        settings.set_fix_first_words_capitalization(
            self.checkBox_fix_first_words_capitalization.isChecked()
        )
        settings.set_fix_spaces(self.comboBox_fix_spaces.currentData())
        settings.set_fix_quotation_marks(self.checkBox_fix_quotation_marks.isChecked())
        settings.set_throttling_threads(self.spinBox_throttling_threads.value())
        settings.set_ytdlp_rate_limit(self.comboBox_ytdlp_rate_limit.currentData())
        settings.set_audio(self.groupBox_audio.isChecked())
        settings.set_audio_format(self.comboBox_audio_format.currentData())
        settings.set_audio_bitrate(self.comboBox_audio_bitrate.currentData())
        settings.set_audio_normalization(
            self.comboBox_audio_normalization.currentData()
        )
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
        settings.set_discord_allowed(self.checkBox_discord_allowed.isChecked())
        if self._path_template:
            settings.set_path_template(self._path_template)
        else:
            QtWidgets.QMessageBox.warning(
                self, "Invalid setting", "Please provide a valid path template!"
            )
            return False
        settings.set_app_path(
            settings.SupportedApps.KAREDI, self.lineEdit_path_karedi.text()
        )
        settings.set_app_path(
            settings.SupportedApps.PERFORMOUS, self.lineEdit_path_performous.text()
        )
        settings.set_app_path(
            settings.SupportedApps.ULTRASTAR_MANAGER,
            self.lineEdit_path_ultrastar_manager.text(),
        )
        settings.set_app_path(
            settings.SupportedApps.USDX, self.lineEdit_path_usdx.text()
        )
        settings.set_app_path(
            settings.SupportedApps.VOCALUXE, self.lineEdit_path_vocaluxe.text()
        )
        settings.set_app_path(
            settings.SupportedApps.YASS_RELOADED,
            self.lineEdit_path_yass_reloaded.text(),
        )
        return True
