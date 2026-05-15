"""Dialog with app settings."""

from __future__ import annotations

import enum
import sys
from pathlib import Path
from typing import ClassVar, assert_never

import platformdirs
from PySide6 import QtWidgets
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QWidget

from usdb_syncer import SongId, events, path_template, separation, settings
from usdb_syncer.gui import gui_utils, icons, notification, theme
from usdb_syncer.gui.forms.SettingsDialog import Ui_Dialog
from usdb_syncer.path_template import PathTemplate
from usdb_syncer.usdb_scraper import SessionManager
from usdb_syncer.usdb_song import UsdbSong

_FALLBACK_SONG = UsdbSong(
    song_id=SongId(3715),
    usdb_mtime=0,
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


class _ProviderState(enum.Enum):
    """State of the stem separation provider."""

    NOT_SELECTED = enum.auto()
    SELECTED = enum.auto()


class SettingsDialog(Ui_Dialog, QDialog):
    """Dialog with app settings."""

    _instance: ClassVar[SettingsDialog | None] = None
    _last_tab_index: ClassVar[int] = 0
    _path_template: PathTemplate | None = None
    _separation_manager: separation.SeparationManager | None = None
    _separation_manager_command: str | None = None
    _provider_state: _ProviderState = _ProviderState.NOT_SELECTED

    def __init__(self, parent: QWidget, song: UsdbSong | None) -> None:
        super().__init__(parent=parent)
        gui_utils.cleanup_on_close(self)
        self._song = song or _FALLBACK_SONG
        self.setupUi(self)
        # restore last tab
        self.tabWidget.setCurrentIndex(SettingsDialog._last_tab_index)
        self.tabWidget.currentChanged.connect(self._on_tab_changed)
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
        self.pushButton_browse_tune_perfect.clicked.connect(
            lambda: self._set_location(settings.SupportedApps.TUNE_PERFECT)
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

        self.button_select_separation_provider.clicked.connect(
            self._on_select_separation_provider
        )
        self.comboBox_theme.currentIndexChanged.connect(
            self._set_theme_settings_enabled
        )
        self._set_theme_settings_enabled()
        self.groupBox_audio.toggled.connect(self._update_stem_separation_enabled)
        self.groupBox_stem_separation.toggled.connect(
            self._update_stem_separation_enabled
        )
        self.comboBox_format_version.currentIndexChanged.connect(
            self._handle_format_dependent_settings
        )
        self._handle_format_dependent_settings()

    @classmethod
    def load(cls, parent: QtWidgets.QWidget, song: UsdbSong | None) -> None:
        if cls._instance:
            cls._instance._song = song or _FALLBACK_SONG
            cls._instance.raise_()
        else:
            cls._instance = cls(parent, song)
            cls._instance.show()

    def _connect_stem_separation(self, command: list[str]) -> None:
        # Kill any previous probing subprocess
        if self._separation_manager is not None:
            self._separation_manager.close()
            self._separation_manager = None

        try:
            self._separation_manager = separation.SeparationManager(command)
        except Exception:  # noqa: BLE001
            self._separation_manager = None
            self.comboBox_separation_model.clear()
            self.label_separation_model.setEnabled(False)
            self.comboBox_separation_model.setEnabled(False)
            self.label_separation_threads.setEnabled(False)
            self.spinBox_separation_threads.setEnabled(False)
            state = _ProviderState.NOT_SELECTED
            notification.error("Selected provider encountered an error")
            self._update_provider_label(state)
            return

        models = self._separation_manager.get_available_models()
        self.comboBox_separation_model.clear()
        for model_name, model_display_name in models.items():
            self.comboBox_separation_model.addItem(model_display_name, model_name)
        self.label_separation_model.setEnabled(True)
        self.comboBox_separation_model.setEnabled(True)
        self.label_separation_threads.setEnabled(True)
        self.spinBox_separation_threads.setEnabled(True)
        self._update_provider_label(_ProviderState.SELECTED)
        self._set_stem_separation_control_states(
            self.groupBox_stem_separation.isChecked()
        )

    def _set_theme_settings_enabled(self) -> None:
        hidden = self.comboBox_theme.currentData() == settings.Theme.SYSTEM
        self.label_primary_color.setHidden(hidden)
        self.comboBox_primary_color.setHidden(hidden)
        self.label_colored_background.setHidden(hidden)
        self.checkBox_colored_background.setHidden(hidden)
        self._update_provider_label(self._provider_state)

    def _handle_format_dependent_settings(self) -> None:
        self._update_stem_separation_enabled()

    def _update_stem_separation_enabled(self) -> None:
        disabled = (
            self.comboBox_format_version.currentData() <= settings.FormatVersion.V1_0_0
            or not self.groupBox_audio.isChecked()
        )
        self.groupBox_stem_separation.setDisabled(disabled)
        self._set_stem_separation_control_states(
            self.groupBox_stem_separation.isChecked() and not disabled
        )

    def _set_stem_separation_control_states(self, enabled: bool) -> None:
        self.button_select_separation_provider.setEnabled(enabled)
        self.lineEdit_separation_provider_info.setEnabled(enabled)
        self.label_separation_model.setEnabled(enabled)
        self.comboBox_separation_model.setEnabled(enabled)
        self.label_separation_threads.setEnabled(enabled)
        self.spinBox_separation_threads.setEnabled(enabled)

    def _set_location(self, app: settings.SupportedApps) -> None:
        path = self._get_executable(app)
        text = str(path) if path is not None else ""
        match app:
            case settings.SupportedApps.KAREDI:
                self.lineEdit_path_karedi.setText(text)
            case settings.SupportedApps.PERFORMOUS:
                self.lineEdit_path_performous.setText(text)
            case settings.SupportedApps.TUNE_PERFECT:
                self.lineEdit_path_tune_perfect.setText(text)
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

    def _select_separation_executable(self) -> Path | None:
        filt = "*"
        directory = platformdirs.user_desktop_dir()
        filename = QFileDialog.getOpenFileName(
            self, "Select separation provider", directory, filt
        )[0]
        self.raise_()
        if not filename:
            notification.error("No file selected.")
            return None
        self._separation_manager_command = filename
        return Path(filename)

    def _update_provider_label(self, state: _ProviderState) -> None:
        self._provider_state = state
        match state:
            case _ProviderState.NOT_SELECTED:
                info_text = "No separation provider selected."
                info_tooltip = (
                    "Please select a separation provider to enable stem separation."
                )
            case _ProviderState.SELECTED:
                assert self._separation_manager is not None
                info_text = f"{self._separation_manager.get_name()} v.{self._separation_manager.get_version()}"
                info_tooltip = f"Location: {self._separation_manager.client.command[0]}"
            case _:
                assert_never()
        self.lineEdit_separation_provider_info.setText(info_text)
        self.lineEdit_separation_provider_info.setToolTip(info_tooltip)

    def _on_select_separation_provider(self) -> None:
        if path := self._select_separation_executable():
            self._connect_stem_separation([str(path)])

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
        self._separation_manager_command = settings.get_audio_separation_executable()
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
        self.checkBox_auto_update.setChecked(settings.get_auto_update())
        self.groupBox_cover.setChecked(settings.get_cover())
        self.comboBox_cover_max_size.setCurrentIndex(
            self.comboBox_cover_max_size.findData(settings.get_cover_max_size())
        )
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
        self.groupBox_stem_separation.setChecked(settings.get_audio_separation())
        self._connect_stem_separation([self._separation_manager_command])
        self.comboBox_separation_model.setCurrentIndex(
            self.comboBox_separation_model.findData(
                settings.get_audio_separation_model()
            )
        )
        self.spinBox_separation_threads.setValue(
            settings.get_audio_separation_threads()
        )
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
        self.checkBox_trash_files.setChecked(settings.get_trash_files())
        self.checkBox_trash_remotely_deleted_songs.setChecked(
            settings.get_trash_remotely_deleted_songs()
        )
        if (path := settings.get_app_path(settings.SupportedApps.KAREDI)) is not None:
            self.lineEdit_path_karedi.setText(str(path))
        if (
            path := settings.get_app_path(settings.SupportedApps.PERFORMOUS)
        ) is not None:
            self.lineEdit_path_performous.setText(str(path))
        if (
            path := settings.get_app_path(settings.SupportedApps.TUNE_PERFECT)
        ) is not None:
            self.lineEdit_path_tune_perfect.setText(str(path))
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
        self.edit_path_template.setText(str(path_template.PathTemplate.from_settings()))
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
        self._cleanup_separation_manager()
        SettingsDialog._instance = None
        super().accept()

    def reject(self) -> None:
        self._cleanup_separation_manager()
        SettingsDialog._instance = None
        super().reject()

    def _cleanup_separation_manager(self) -> None:
        if self._separation_manager is not None:
            self._separation_manager.close()
            self._separation_manager = None

    def _save_settings(self) -> bool:
        new_theme = self.comboBox_theme.currentData()
        new_primary_color = self.comboBox_primary_color.currentData()
        colored_background = self.checkBox_colored_background.isChecked()
        settings.set_theme(new_theme)
        settings.set_primary_color(new_primary_color)
        settings.set_colored_background(colored_background)
        theme.Theme.new(new_theme, new_primary_color, colored_background).apply()
        settings.set_auto_update(self.checkBox_auto_update.isChecked())
        settings.set_browser(self.comboBox_browser.currentData())
        settings.set_cover(self.groupBox_cover.isChecked())
        settings.set_cover_max_size(self.comboBox_cover_max_size.currentData())
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

        settings.set_audio_separation(self.groupBox_stem_separation.isChecked())
        separation_threads = self.spinBox_separation_threads.value()
        settings.set_audio_separation_threads(separation_threads)
        separation.set_max_concurrent(separation_threads)
        if self._separation_manager is not None:
            settings.set_audio_separation_executable(
                self._separation_manager.client.command[0]
            )
        settings.set_audio_separation_model(
            self.comboBox_separation_model.currentData()
        )
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
        settings.set_trash_files(self.checkBox_trash_files.isChecked())
        settings.set_trash_remotely_deleted_songs(
            self.checkBox_trash_remotely_deleted_songs.isChecked()
        )
        settings.set_app_path(
            settings.SupportedApps.KAREDI, self.lineEdit_path_karedi.text()
        )
        settings.set_app_path(
            settings.SupportedApps.PERFORMOUS, self.lineEdit_path_performous.text()
        )
        settings.set_app_path(
            settings.SupportedApps.TUNE_PERFECT, self.lineEdit_path_tune_perfect.text()
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
        events.PreferencesChanged().post()
        return True

    def _on_tab_changed(self, index: int) -> None:
        SettingsDialog._last_tab_index = index
