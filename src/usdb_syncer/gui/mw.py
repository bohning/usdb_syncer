"""usdb_syncer's GUI"""

import webbrowser
from collections.abc import Callable
from pathlib import Path

from PySide6 import QtGui
from PySide6.QtWidgets import QFileDialog, QLabel, QMainWindow

from usdb_syncer import SongId, db, events, settings, song_routines, usdb_id_file
from usdb_syncer.constants import Usdb
from usdb_syncer.gui import gui_utils, icons, progress, progress_bar
from usdb_syncer.gui.about_dialog import AboutDialog
from usdb_syncer.gui.comment_dialog import CommentDialog
from usdb_syncer.gui.debug_console import DebugConsole
from usdb_syncer.gui.forms.MainWindow import Ui_MainWindow
from usdb_syncer.gui.meta_tags_dialog import MetaTagsDialog
from usdb_syncer.gui.progress import run_with_progress
from usdb_syncer.gui.report_dialog import ReportDialog
from usdb_syncer.gui.search_tree.tree import FilterTree
from usdb_syncer.gui.settings_dialog import SettingsDialog
from usdb_syncer.gui.song_table.song_table import SongTable
from usdb_syncer.gui.usdb_login_dialog import UsdbLoginDialog
from usdb_syncer.logger import logger
from usdb_syncer.song_loader import DownloadManager
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.usdb_scraper import post_song_rating
from usdb_syncer.usdb_song import UsdbSong
from usdb_syncer.utils import AppPaths, LinuxEnvCleaner, open_path_or_file


class MainWindow(Ui_MainWindow, QMainWindow):
    """The app's main window and entry point to the GUI."""

    _cleaned_up = False

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
        events.SavedSearchRestored.subscribe(
            lambda event: self.lineEdit_search.setText(event.search.text)
        )
        events.ThemeChanged.subscribe(self._on_theme_changed)
        self._setup_buttons()
        self._restore_state()

    def _setup_statusbar(self) -> None:
        self._status_label = QLabel(self)
        self.statusbar.addWidget(self._status_label)

        def on_count_changed(rows: int, selected: int) -> None:
            total = db.usdb_song_count()
            self._status_label.setText(
                f"{rows} out of {total} songs shown, {selected} selected."
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
        self.menu_view.addAction(self.dock_search.toggleViewAction())
        self.menu_view.addAction(self.dock_log.toggleViewAction())
        for action, func in (
            (self.action_songs_download, self.table.download_selection),
            (self.action_songs_abort, self.table.abort_selected_downloads),
            (self.action_find_local_songs, self._select_local_songs),
            (self.action_refetch_song_list, self._refetch_song_list),
            (self.action_usdb_login, lambda: UsdbLoginDialog(self).show()),
            (self.action_meta_tags, lambda: MetaTagsDialog(self).show()),
            (
                self.action_settings,
                lambda: SettingsDialog(self, self.table.current_song()).show(),
            ),
            (self.action_about, lambda: AboutDialog(self).show()),
            (
                self.action_generate_song_list,
                lambda: ReportDialog(self, self.table).show(),
            ),
            (self.action_import_usdb_ids, self._import_usdb_ids_from_files),
            (self.action_export_usdb_ids, self._export_usdb_ids_to_file),
            (self.action_show_log, lambda: open_path_or_file(AppPaths.log.parent)),
            (self.action_show_in_usdb, self._show_current_song_in_usdb),
            (self.action_post_comment_in_usdb, self._show_comment_dialog),
            (self.action_rate_1star, lambda: self._rate_in_usdb(1)),
            (self.action_rate_2stars, lambda: self._rate_in_usdb(2)),
            (self.action_rate_3stars, lambda: self._rate_in_usdb(3)),
            (self.action_rate_4stars, lambda: self._rate_in_usdb(4)),
            (self.action_rate_5stars, lambda: self._rate_in_usdb(5)),
            (self.action_open_song_folder, self._open_current_song_folder),
            (
                self.action_open_song_in_karedi,
                lambda: self._open_current_song_in_app(settings.SupportedApps.KAREDI),
            ),
            (
                self.action_open_song_in_performous,
                lambda: self._open_current_song_in_app(
                    settings.SupportedApps.PERFORMOUS
                ),
            ),
            (
                self.action_open_song_in_ultrastar_manager,
                lambda: self._open_current_song_in_app(
                    settings.SupportedApps.ULTRASTAR_MANAGER
                ),
            ),
            (
                self.action_open_song_in_usdx,
                lambda: self._open_current_song_in_app(settings.SupportedApps.USDX),
            ),
            (
                self.action_open_song_in_vocaluxe,
                lambda: self._open_current_song_in_app(settings.SupportedApps.VOCALUXE),
            ),
            (
                self.action_open_song_in_yass_reloaded,
                lambda: self._open_current_song_in_app(
                    settings.SupportedApps.YASS_RELOADED
                ),
            ),
            (self.action_delete, self.table.delete_selected_songs),
            (self.action_pin, self.table.set_pin_selected_songs),
        ):
            action.triggered.connect(func)
        self.menu_custom_data.aboutToShow.connect(self.table.build_custom_data_menu)

    def _setup_shortcuts(self) -> None:
        gui_utils.set_shortcut("Ctrl+.", self, lambda: DebugConsole(self).show())

    def _setup_song_dir(self) -> None:
        self.song_dir = settings.get_song_dir()
        self.lineEdit_song_dir.setText(str(self.song_dir))
        self.pushButton_select_song_dir.clicked.connect(self._select_song_dir)

    def _setup_buttons(self) -> None:
        self.button_download.clicked.connect(self.table.download_selection)
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
        def on_done(result: progress.Result[set[SongId]]) -> None:
            songs = result.result()
            self.table.set_selection_to_song_ids(songs)
            logger.info(f"Selected {len(songs)} songs.")

        if directory := QFileDialog.getExistingDirectory(self, "Select Song Directory"):
            run_with_progress(
                "Reading song txts ...",
                lambda: song_routines.find_local_songs(Path(directory)),
                on_done=on_done,
            )

    def _refetch_song_list(self) -> None:
        def task() -> None:
            with db.transaction():
                song_routines.load_available_songs(force_reload=True)

        def on_done(result: progress.Result[None]) -> None:
            UsdbSong.clear_cache()
            self.table.end_reset()
            self.table.search_songs()
            result.result()

        self.table.begin_reset()
        run_with_progress("Fetching song list ...", task=task, on_done=on_done)

    def _select_song_dir(self) -> None:
        song_dir = QFileDialog.getExistingDirectory(self, "Select Song Directory")
        if not song_dir:
            return
        path = Path(song_dir).resolve(strict=True)

        def task() -> None:
            with db.transaction():
                song_routines.synchronize_sync_meta_folder(path)
                SyncMeta.reset_active(path)

        def on_done(result: progress.Result[None]) -> None:
            result.result()
            self.lineEdit_song_dir.setText(str(path))
            settings.set_song_dir(path)
            UsdbSong.clear_cache()
            events.SongDirChanged(path).post()

        run_with_progress("Reading meta files ...", task=task, on_done=on_done)

    def _import_usdb_ids_from_files(self) -> None:
        file_list = QFileDialog.getOpenFileNames(
            self,
            caption="Select one or more files to import USDB IDs from",
            dir=str(Path.cwd()),
            filter=(
                "JSON, USDB IDs, Weblinks (*.json *.usdb_ids *.url *.webloc *.desktop)"
            ),
        )[0]
        if not file_list:
            logger.info("no files selected to import USDB IDs from")
            return
        paths = [Path(f) for f in file_list]
        if available := usdb_id_file.get_available_song_ids_from_files(paths):
            self.table.set_selection_to_song_ids(available)

    def _export_usdb_ids_to_file(self) -> None:
        selected_ids = [song.song_id for song in self.table.selected_songs()]
        if not selected_ids:
            logger.info("Skipping export: no songs selected.")
            return

        # Note: automatically checks if file already exists
        path = QFileDialog.getSaveFileName(
            self,
            caption="Select export file for USDB IDs",
            dir=str(Path.cwd()),
            filter="USDB ID File (*.usdb_ids)",
        )[0]
        if not path:
            logger.info("export aborted")
            return

        usdb_id_file.write_usdb_id_file(Path(path), selected_ids)
        logger.info(f"exported {len(selected_ids)} USDB IDs to {path}")

    def _show_current_song_in_usdb(self) -> None:
        if song := self.table.current_song():
            logger.debug(f"Opening song page #{song.song_id} in webbrowser.")
            with LinuxEnvCleaner():
                webbrowser.open(f"{Usdb.DETAIL_URL}{song.song_id:d}")
        else:
            logger.info("No current song.")

    def _show_comment_dialog(self) -> None:
        song = self.table.current_song()
        if song:
            CommentDialog(self, song).show()
        else:
            logger.debug("Not opening comment dialog: no song selected.")

    def _rate_in_usdb(self, stars: int) -> None:
        song = self.table.current_song()
        if song:
            post_song_rating(song.song_id, stars)
        else:
            logger.debug("Not rating song: no song selected.")

    def _open_current_song(self, action: Callable[[Path], None]) -> None:
        if song := self.table.current_song():
            if song.sync_meta:
                if song.sync_meta.path.exists():
                    action(song.sync_meta.path.parent)
                else:
                    with db.transaction():
                        song.remove_sync_meta()
                    events.SongChanged(song.song_id)
                    logger.info("Song does not exist locally anymore.")
            else:
                logger.info("Song does not exist locally.")
        else:
            logger.info("No current song.")

    def _open_current_song_folder(self) -> None:
        self._open_current_song(open_path_or_file)

    def _open_current_song_in_app(self, app: settings.SupportedApps) -> None:
        self._open_current_song(lambda path: settings.SupportedApps.open_app(app, path))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        def on_done(result: progress.Result) -> None:
            result.log_error()
            self.table.save_state()
            self._save_state()
            db.close()
            self._cleaned_up = True
            logger.debug("Closing after cleanup.")
            self.close()

        if self._cleaned_up:
            logger.debug("Accepting close event.")
            event.accept()
        else:
            logger.debug("Close event deferred, cleaning up ...")
            run_with_progress("Shutting down ...", DownloadManager.quit, on_done)
            event.ignore()

    def _restore_state(self) -> None:
        self.restoreGeometry(settings.get_geometry_main_window())
        self.restoreState(settings.get_state_main_window())
        self.dock_log.restoreGeometry(settings.get_geometry_log_dock())

    def _save_state(self) -> None:
        settings.set_geometry_main_window(self.saveGeometry())
        settings.set_state_main_window(self.saveState())
        settings.set_geometry_log_dock(self.dock_log.saveGeometry())

    def _on_theme_changed(self, event: events.ThemeChanged) -> None:
        theme = event.theme
        self.toolButton_debugs.setIcon(icons.Icon.BUG.icon(theme))
        self.toolButton_infos.setIcon(icons.Icon.INFO.icon(theme))
        self.toolButton_warnings.setIcon(icons.Icon.WARNING.icon(theme))
        self.toolButton_errors.setIcon(icons.Icon.ERROR.icon(theme))
        self.button_download.setIcon(icons.Icon.DOWNLOAD.icon(theme))
        self.button_pause.setIcon(icons.Icon.PAUSE_REMOTE.icon(theme))
        self.pushButton_select_song_dir.setIcon(icons.Icon.SONG_FOLDER.icon(theme))
        self.action_settings.setIcon(icons.Icon.SETTINGS.icon(theme))
        self.action_meta_tags.setIcon(icons.Icon.META_TAGS.icon(theme))
        self.action_generate_song_list.setIcon(icons.Icon.REPORT.icon(theme))
        self.action_usdb_login.setIcon(icons.Icon.USDB.icon(theme))
        self.action_refetch_song_list.setIcon(icons.Icon.CHECK_FOR_UPDATE.icon(theme))
        self.action_show_log.setIcon(icons.Icon.LOG.icon(theme))
        self.action_songs_download.setIcon(icons.Icon.DOWNLOAD.icon(theme))
        self.action_songs_abort.setIcon(icons.Icon.ABORT.icon(theme))
        self.action_show_in_usdb.setIcon(icons.Icon.USDB.icon(theme))
        self.action_post_comment_in_usdb.setIcon(icons.Icon.COMMENT.icon(theme))
        self.menu_rate_song_on_usdb.setIcon(icons.Icon.RATING.icon(theme))
        self.action_open_song_folder.setIcon(icons.Icon.SONG_FOLDER.icon(theme))
        self.menu_open_song_in.setIcon(icons.Icon.OPEN_SONG_WITH.icon(theme))
        self.menu_custom_data.setIcon(icons.Icon.CUSTOM_DATA.icon(theme))
        self.action_pin.setIcon(icons.Icon.PIN.icon(theme))
        self.action_delete.setIcon(icons.Icon.DELETE.icon(theme))
        self.action_open_song_in_usdx.setIcon(icons.Icon.USDX.icon(theme))
        self.action_open_song_in_vocaluxe.setIcon(icons.Icon.VOCALUXE.icon(theme))
        self.action_open_song_in_performous.setIcon(icons.Icon.PERFORMOUS.icon(theme))
        self.action_open_song_in_yass_reloaded.setIcon(
            icons.Icon.YASS_RELOADED.icon(theme)
        )
        self.action_open_song_in_karedi.setIcon(icons.Icon.KAREDI.icon(theme))
        self.action_open_song_in_ultrastar_manager.setIcon(
            icons.Icon.ULTRASTAR_MANAGER.icon(theme)
        )
        self.action_find_local_songs.setIcon(icons.Icon.DATABASE.icon(theme))
        self.action_import_usdb_ids.setIcon(icons.Icon.FILE_IMPORT.icon(theme))
        self.action_export_usdb_ids.setIcon(icons.Icon.FILE_EXPORT.icon(theme))
