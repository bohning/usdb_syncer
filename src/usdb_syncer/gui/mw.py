"""usdb_syncer's GUI"""

import datetime
import os
import webbrowser
from pathlib import Path

from PySide6 import QtGui
from PySide6.QtWidgets import QFileDialog, QLabel, QMainWindow

from usdb_syncer import db, events, settings, song_routines, usdb_id_file
from usdb_syncer.constants import Usdb
from usdb_syncer.gui import gui_utils, progress_bar
from usdb_syncer.gui.about_dialog import AboutDialog
from usdb_syncer.gui.debug_console import DebugConsole
from usdb_syncer.gui.ffmpeg_dialog import check_ffmpeg
from usdb_syncer.gui.forms.MainWindow import Ui_MainWindow
from usdb_syncer.gui.meta_tags_dialog import MetaTagsDialog
from usdb_syncer.gui.progress import run_with_progress
from usdb_syncer.gui.search_tree.tree import FilterTree
from usdb_syncer.gui.settings_dialog import SettingsDialog
from usdb_syncer.gui.song_table.song_table import SongTable
from usdb_syncer.gui.usdb_login_dialog import UsdbLoginDialog
from usdb_syncer.logger import get_logger
from usdb_syncer.pdf import generate_song_pdf
from usdb_syncer.song_loader import DownloadManager
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.usdb_song import UsdbSong
from usdb_syncer.utils import AppPaths, open_file_explorer

_logger = get_logger(__file__)


class MainWindow(Ui_MainWindow, QMainWindow):
    """The app's main window and entry point to the GUI."""

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)
        self.tree = FilterTree(self)
        self.table = SongTable(self)
        self.progress_bar = progress_bar.ProgressBar(
            self.bar_download_progress, self.label_download_progress
        )
        self._setup_statusbar()
        self._setup_log()
        self._setup_toolbar()
        self._setup_shortcuts()
        self._setup_song_dir()
        self.lineEdit_search.textChanged.connect(
            lambda txt: events.TextFilterChanged(txt).post()
        )
        self._setup_buttons()
        self._restore_state()

    def _setup_statusbar(self) -> None:
        self._status_label = QLabel(self)
        self.statusbar.addWidget(self._status_label)

        def on_count_changed(shown_count: int) -> None:
            self._status_label.setText(
                f"{shown_count} out of {db.usdb_song_count()} songs shown."
            )

        self.table.connect_row_count_changed(on_count_changed)

    def _setup_log(self) -> None:
        self.plainTextEdit.setReadOnly(True)
        self._debugs: list[tuple[str, float]] = []
        self._infos: list[tuple[str, float]] = []
        self._warnings: list[tuple[str, float]] = []
        self._errors: list[tuple[str, float]] = []
        self.toolButton_debugs.toggled.connect(self._on_log_filter_changed)
        self.toolButton_infos.toggled.connect(self._on_log_filter_changed)
        self.toolButton_warnings.toggled.connect(self._on_log_filter_changed)
        self.toolButton_errors.toggled.connect(self._on_log_filter_changed)

    def _setup_toolbar(self) -> None:
        for action, func in (
            (self.action_songs_download, self._download_selection),
            (self.action_songs_abort, self.table.abort_selected_downloads),
            (self.action_find_local_songs, self._select_local_songs),
            (self.action_refetch_song_list, self._refetch_song_list),
            (self.action_usdb_login, lambda: UsdbLoginDialog(self).show()),
            (self.action_meta_tags, lambda: MetaTagsDialog(self).show()),
            (self.action_settings, lambda: SettingsDialog(self).show()),
            (self.action_about, lambda: AboutDialog(self).show()),
            (self.action_generate_song_pdf, self._generate_song_pdf),
            (self.action_import_usdb_ids, self._import_usdb_ids_from_files),
            (self.action_export_usdb_ids, self._export_usdb_ids_to_file),
            (self.action_show_log, lambda: open_file_explorer(AppPaths.log)),
            (self.action_show_in_usdb, self._show_current_song_in_usdb),
            (self.action_open_song_folder, self._open_current_song_folder),
            (self.action_delete, self.table.delete_selected_songs),
            (self.action_pin, self.table.set_pin_selected_songs),
        ):
            action.triggered.connect(func)

    def _download_selection(self) -> None:
        check_ffmpeg(self, self.table.download_selection)

    def _setup_shortcuts(self) -> None:
        gui_utils.set_shortcut("Ctrl+.", self, lambda: DebugConsole(self).show())

    def _setup_song_dir(self) -> None:
        self.lineEdit_song_dir.setText(str(settings.get_song_dir()))
        self.pushButton_select_song_dir.clicked.connect(self._select_song_dir)

    def _setup_buttons(self) -> None:
        self.button_download.clicked.connect(self._download_selection)
        self.button_pause.clicked.connect(DownloadManager.set_pause)

    def _on_log_filter_changed(self) -> None:
        messages = []
        if self.toolButton_debugs.isChecked():
            messages += self._debugs
        if self.toolButton_infos.isChecked():
            messages += self._infos
        if self.toolButton_warnings.isChecked():
            messages += self._warnings
        if self.toolButton_errors.isChecked():
            messages += self._errors
        messages.sort(key=lambda m: m[1])
        self.plainTextEdit.setPlainText("\n".join(m[0] for m in messages))
        gui_utils.scroll_to_bottom(self.plainTextEdit)

    def log_to_text_edit(self, message: str, level: int, created: float) -> None:
        match level:
            case 40:
                self._errors.append((message, created))
                if self.toolButton_errors.isChecked():
                    self.plainTextEdit.appendPlainText(message)
            case 30:
                self._warnings.append((message, created))
                if self.toolButton_warnings.isChecked():
                    self.plainTextEdit.appendPlainText(message)
            case 20:
                self._infos.append((message, created))
                if self.toolButton_infos.isChecked():
                    self.plainTextEdit.appendPlainText(message)
            case 10:
                self._debugs.append((message, created))
                if self.toolButton_debugs.isChecked():
                    self.plainTextEdit.appendPlainText(message)

    def _select_local_songs(self) -> None:
        if directory := QFileDialog.getExistingDirectory(self, "Select Song Directory"):
            songs = run_with_progress(
                "Reading song txts ...",
                lambda _: song_routines.find_local_songs(Path(directory)),
            )
            self.table.set_selection_to_song_ids(songs)
            _logger.info(f"Selected {len(songs)} songs.")

    def _refetch_song_list(self) -> None:
        with db.transaction():
            run_with_progress(
                "Fetching song list ...",
                lambda _: song_routines.load_available_songs(force_reload=True),
            )
        self.table.reset()

    def _select_song_dir(self) -> None:
        song_dir = QFileDialog.getExistingDirectory(self, "Select Song Directory")
        if not song_dir:
            return
        path = Path(song_dir).resolve(strict=True)
        with db.transaction():
            run_with_progress(
                "Reading meta files ...",
                lambda _: song_routines.synchronize_sync_meta_folder(path),
            )
            SyncMeta.reset_active(path)
        self.lineEdit_song_dir.setText(str(path))
        settings.set_song_dir(path)
        UsdbSong.clear_cache()
        events.SongDirChanged(path).post()

    def _generate_song_pdf(self) -> None:
        fname = f"{datetime.datetime.now():%Y-%m-%d}_songlist.pdf"
        path = os.path.join(settings.get_song_dir(), fname)
        path = QFileDialog.getSaveFileName(self, dir=path, filter="PDF (*.pdf)")[0]
        if path:
            generate_song_pdf(db.all_local_usdb_songs(), path)

    def _import_usdb_ids_from_files(self) -> None:
        file_list = QFileDialog.getOpenFileNames(
            self,
            caption="Select one or more files to import USDB IDs from",
            dir=os.getcwd(),
            filter=(
                "JSON, USDB IDs, Weblinks (*.json *.usdb_ids *.url *.webloc *.desktop)"
            ),
        )[0]
        if not file_list:
            _logger.info("no files selected to import USDB IDs from")
            return
        if available := usdb_id_file.get_available_song_ids_from_files(file_list):
            self.table.set_selection_to_song_ids(available)

    def _export_usdb_ids_to_file(self) -> None:
        selected_ids = [song.song_id for song in self.table.selected_songs()]
        if not selected_ids:
            _logger.info("Skipping export: no songs selected.")
            return

        # Note: automatically checks if file already exists
        path = QFileDialog.getSaveFileName(
            self,
            caption="Select export file for USDB IDs",
            dir=os.getcwd(),
            filter="USDB ID File (*.usdb_ids)",
        )[0]
        if not path:
            _logger.info("export aborted")
            return

        usdb_id_file.write_usdb_id_file(path, selected_ids)
        _logger.info(f"exported {len(selected_ids)} USDB IDs to {path}")

    def _show_current_song_in_usdb(self) -> None:
        if song := self.table.current_song():
            _logger.debug(f"Opening song page #{song.song_id} in webbrowser.")
            webbrowser.open(f"{Usdb.BASE_URL}?link=detail&id={song.song_id:d}")
        else:
            _logger.info("No current song.")

    def _open_current_song_folder(self) -> None:
        if song := self.table.current_song():
            if song.sync_meta:
                open_file_explorer(song.sync_meta.path.parent)
            else:
                _logger.info("Song does not exist locally.")
        else:
            _logger.info("No current song.")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        DownloadManager.quit()
        self.table.save_state()
        self._save_state()
        db.close()
        event.accept()

    def _restore_state(self) -> None:
        self.restoreGeometry(settings.get_geometry_main_window())
        self.restoreState(settings.get_state_main_window())
        self.dock_log.restoreGeometry(settings.get_geometry_log_dock())

    def _save_state(self) -> None:
        settings.set_geometry_main_window(self.saveGeometry())
        settings.set_state_main_window(self.saveState())
        settings.set_geometry_log_dock(self.dock_log.saveGeometry())
