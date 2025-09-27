"""usdb_syncer's GUI"""

import webbrowser
from collections.abc import Callable
from pathlib import Path

from PySide6.QtGui import QCloseEvent, QPixmap
from PySide6.QtWidgets import QFileDialog, QLabel, QMainWindow

from usdb_syncer import (
    SongId,
    db,
    events,
    settings,
    song_routines,
    usdb_id_file,
    utils,
    webserver,
)
from usdb_syncer.constants import Usdb
from usdb_syncer.gui import (
    cover_widget,
    ffmpeg_dialog,
    gui_utils,
    icons,
    progress,
    progress_bar,
)
from usdb_syncer.gui import events as gui_events
from usdb_syncer.gui.about_dialog import AboutDialog
from usdb_syncer.gui.comment_dialog import CommentDialog
from usdb_syncer.gui.debug_console import DebugConsole
from usdb_syncer.gui.forms.MainWindow import Ui_MainWindow
from usdb_syncer.gui.meta_tags_dialog import MetaTagsDialog
from usdb_syncer.gui.previewer import Previewer
from usdb_syncer.gui.progress import run_with_progress
from usdb_syncer.gui.report_dialog import ReportDialog
from usdb_syncer.gui.search_tree.tree import FilterTree
from usdb_syncer.gui.settings_dialog import SettingsDialog
from usdb_syncer.gui.shortcuts import MainWindowShortcut, SongTableShortcut
from usdb_syncer.gui.song_table.song_table import SongTable
from usdb_syncer.gui.usdb_login_dialog import UsdbLoginDialog
from usdb_syncer.gui.webserver_dialog import WebserverDialog
from usdb_syncer.logger import logger
from usdb_syncer.song_loader import DownloadManager
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.usdb_scraper import post_song_rating
from usdb_syncer.usdb_song import UsdbSong
from usdb_syncer.utils import AppPaths, LinuxEnvCleaner, open_path_or_file

NO_COVER_PIXMAP = QPixmap(":/images/nocover.png")


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
            lambda txt: gui_events.TextFilterChanged(txt).post()
        )
        gui_events.SavedSearchRestored.subscribe(
            lambda event: self.lineEdit_search.setText(event.search.text)
        )
        gui_events.ThemeChanged.subscribe(self._on_theme_changed)
        gui_events.CurrentSongChanged.subscribe(self._on_current_song_changed)
        self._setup_buttons()
        self.cover = cover_widget.ScaledCoverLabel(self.dock_cover)
        self._restore_state()
        self._current_song_id: int | None = None

    def _focus_search(self) -> None:
        self.lineEdit_search.setFocus()
        self.lineEdit_search.selectAll()

    def _focus_filter_search(self) -> None:
        self.line_edit_search_filters.setFocus()
        self.line_edit_search_filters.selectAll()

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
        self.menu_view.addAction(self.dock_cover.toggleViewAction())
        self.menu_view.addAction(self.dock_log.toggleViewAction())
        for action, func, shortcut in (
            (
                self.action_songs_download,
                self.table.download_selection,
                SongTableShortcut.DOWNLOAD,
            ),
            (
                self.action_songs_abort,
                self.table.abort_selected_downloads,
                SongTableShortcut.ABORT_DOWNLOAD,
            ),
            (self.action_find_local_songs, self._select_local_songs, None),
            (self.action_refetch_song_list, self._refetch_song_list, None),
            (self.action_usdb_login, lambda: UsdbLoginDialog(self).show(), None),
            (self.action_meta_tags, lambda: MetaTagsDialog(self).show(), None),
            (
                self.action_settings,
                lambda: SettingsDialog.load(self, self.table.current_song()),
                MainWindowShortcut.OPEN_PREFERENCES,
            ),
            (self.action_about, lambda: AboutDialog(self).show(), None),
            (self.action_webserver, lambda: WebserverDialog(self).show(), None),
            (
                self.action_generate_song_list,
                lambda: ReportDialog(self, self.table).show(),
                None,
            ),
            (self.action_import_usdb_ids, self._import_usdb_ids_from_files, None),
            (self.action_export_usdb_ids, self._export_usdb_ids_to_file, None),
            (
                self.action_show_log,
                lambda: open_path_or_file(AppPaths.log.parent),
                None,
            ),
            (self.action_show_in_usdb, self._show_current_song_in_usdb, None),
            (self.action_post_comment_in_usdb, self._show_comment_dialog, None),
            (self.action_rate_1star, lambda: self._rate_in_usdb(1), None),
            (self.action_rate_2stars, lambda: self._rate_in_usdb(2), None),
            (self.action_rate_3stars, lambda: self._rate_in_usdb(3), None),
            (self.action_rate_4stars, lambda: self._rate_in_usdb(4), None),
            (self.action_rate_5stars, lambda: self._rate_in_usdb(5), None),
            (self.action_open_song_folder, self._open_current_song_folder, None),
            (
                self.action_open_song_in_karedi,
                lambda: self._open_current_song_in_app(settings.SupportedApps.KAREDI),
                None,
            ),
            (
                self.action_open_song_in_performous,
                lambda: self._open_current_song_in_app(
                    settings.SupportedApps.PERFORMOUS
                ),
                None,
            ),
            (
                self.action_open_song_in_tune_perfect,
                lambda: self._open_current_song_in_app(
                    settings.SupportedApps.TUNE_PERFECT
                ),
                None,
            ),
            (
                self.action_open_song_in_ultrastar_manager,
                lambda: self._open_current_song_in_app(
                    settings.SupportedApps.ULTRASTAR_MANAGER
                ),
                None,
            ),
            (
                self.action_open_song_in_usdx,
                lambda: self._open_current_song_in_app(settings.SupportedApps.USDX),
                None,
            ),
            (
                self.action_open_song_in_vocaluxe,
                lambda: self._open_current_song_in_app(settings.SupportedApps.VOCALUXE),
                None,
            ),
            (
                self.action_open_song_in_yass_reloaded,
                lambda: self._open_current_song_in_app(
                    settings.SupportedApps.YASS_RELOADED
                ),
                None,
            ),
            (
                self.action_delete,
                self.table.delete_selected_songs,
                SongTableShortcut.TRASH_SONG,
            ),
            (
                self.action_pin,
                self.table.set_pin_selected_songs,
                SongTableShortcut.PIN_SONG,
            ),
            (self.action_preview, self._show_preview_dialog, SongTableShortcut.PREVIEW),
            (
                self.action_go_to_search,
                self._focus_search,
                MainWindowShortcut.GO_TO_SEARCH,
            ),
            (
                self.action_go_to_filter_search,
                self._focus_filter_search,
                MainWindowShortcut.GO_TO_FILTER_SEARCH,
            ),
            (
                self.action_go_to_song_table,
                self.table_view.setFocus,
                MainWindowShortcut.GO_TO_SONG_TABLE,
            ),
            (
                self.action_go_to_filters,
                self.search_view.setFocus,
                MainWindowShortcut.GO_TO_FILTERS,
            ),
            (
                self.action_go_to_open_song_menu,
                self._show_open_song_menu,
                SongTableShortcut.OPEN_SONG,
            ),
        ):
            action.triggered.connect(func)
            if shortcut:
                action.setShortcut(shortcut)
        self.menu_custom_data.aboutToShow.connect(self.table.build_custom_data_menu)

    def _setup_shortcuts(self) -> None:
        MainWindowShortcut.OPEN_DEBUG_CONSOLE.connect(
            self, lambda: DebugConsole(self).show()
        )
        SongTableShortcut.PLAY_SAMPLE.connect(
            self.table_view, self.table.on_play_or_stop_sample
        )

    def _setup_song_dir(self) -> None:
        self.song_dir = settings.get_song_dir()
        self.lineEdit_song_dir.setText(str(self.song_dir))

    def _setup_buttons(self) -> None:
        self.button_download.clicked.connect(self.table.download_selection)
        # no need to actually set shortcut because there is an identical action
        self.button_download.setToolTip(SongTableShortcut.DOWNLOAD)
        self.pushButton_select_song_dir.setShortcut(MainWindowShortcut.SELECT_FOLDER)
        self.pushButton_select_song_dir.clicked.connect(self._select_song_dir)
        self.pushButton_select_song_dir.setToolTip(MainWindowShortcut.SELECT_FOLDER)
        self.button_pause.setShortcut(MainWindowShortcut.PAUSE_DOWNLOAD)
        self.button_pause.clicked.connect(DownloadManager.set_pause)
        self.button_pause.setToolTip(MainWindowShortcut.PAUSE_DOWNLOAD)

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
            folder = settings.get_song_dir()
            song_routines.load_available_songs_and_sync_meta(folder, True)

        def on_done(result: progress.Result[None]) -> None:
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
                song_routines.synchronize_sync_meta_folder(path, True)
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

    def _show_preview_dialog(self) -> None:
        song = self.table.current_song()
        if song:
            ffmpeg_dialog.check_ffmpeg(self, lambda: Previewer.load_song(song))

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
        self._open_current_song(lambda path: utils.open_external_app(app, path))

    def _show_open_song_menu(self) -> None:
        pos = self.mapToGlobal(self.rect().center())
        self.menu_open_song_in.popup(pos)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        def cleanup() -> None:
            DownloadManager.quit()
            webserver.stop()

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
            run_with_progress("Shutting down ...", cleanup, on_done)
            event.ignore()

    def _restore_state(self) -> None:
        self.restoreGeometry(settings.get_geometry_main_window())
        self.restoreState(settings.get_state_main_window())
        self.dock_log.restoreGeometry(settings.get_geometry_log_dock())

    def _save_state(self) -> None:
        settings.set_geometry_main_window(self.saveGeometry())
        settings.set_state_main_window(self.saveState())
        settings.set_geometry_log_dock(self.dock_log.saveGeometry())

    def _on_theme_changed(self, event: gui_events.ThemeChanged) -> None:
        key = event.theme.KEY
        self.toolButton_debugs.setIcon(icons.Icon.BUG.icon(key))
        self.toolButton_infos.setIcon(icons.Icon.INFO.icon(key))
        self.toolButton_warnings.setIcon(icons.Icon.WARNING.icon(key))
        self.toolButton_errors.setIcon(icons.Icon.ERROR.icon(key))
        self.button_download.setIcon(icons.Icon.DOWNLOAD.icon(key))
        self.button_pause.setIcon(icons.Icon.PAUSE_REMOTE.icon(key))
        self.pushButton_select_song_dir.setIcon(icons.Icon.SONG_FOLDER.icon(key))
        self.action_settings.setIcon(icons.Icon.SETTINGS.icon(key))
        self.action_meta_tags.setIcon(icons.Icon.META_TAGS.icon(key))
        self.action_generate_song_list.setIcon(icons.Icon.REPORT.icon(key))
        self.action_webserver.setIcon(icons.Icon.SERVER.icon(key))
        self.action_usdb_login.setIcon(icons.Icon.USDB.icon(key))
        self.action_refetch_song_list.setIcon(icons.Icon.CHECK_FOR_UPDATE.icon(key))
        self.action_show_log.setIcon(icons.Icon.LOG.icon(key))
        self.action_songs_download.setIcon(icons.Icon.DOWNLOAD.icon(key))
        self.action_songs_abort.setIcon(icons.Icon.ABORT.icon(key))
        self.action_show_in_usdb.setIcon(icons.Icon.USDB.icon(key))
        self.action_post_comment_in_usdb.setIcon(icons.Icon.COMMENT.icon(key))
        self.menu_rate_song_on_usdb.setIcon(icons.Icon.RATING.icon(key))
        self.action_open_song_folder.setIcon(icons.Icon.SONG_FOLDER.icon(key))
        self.menu_open_song_in.setIcon(icons.Icon.OPEN_SONG_WITH.icon(key))
        self.menu_custom_data.setIcon(icons.Icon.CUSTOM_DATA.icon(key))
        self.action_pin.setIcon(icons.Icon.PIN.icon(key))
        self.action_delete.setIcon(icons.Icon.DELETE.icon(key))
        self.action_open_song_in_usdx.setIcon(icons.Icon.USDX.icon(key))
        self.action_open_song_in_vocaluxe.setIcon(icons.Icon.VOCALUXE.icon(key))
        self.action_open_song_in_performous.setIcon(icons.Icon.PERFORMOUS.icon(key))
        self.action_open_song_in_tune_perfect.setIcon(icons.Icon.TUNE_PERFECT.icon(key))
        self.action_open_song_in_yass_reloaded.setIcon(
            icons.Icon.YASS_RELOADED.icon(key)
        )
        self.action_open_song_in_karedi.setIcon(icons.Icon.KAREDI.icon(key))
        self.action_open_song_in_ultrastar_manager.setIcon(
            icons.Icon.ULTRASTAR_MANAGER.icon(key)
        )
        self.action_find_local_songs.setIcon(icons.Icon.DATABASE.icon(key))
        self.action_import_usdb_ids.setIcon(icons.Icon.FILE_IMPORT.icon(key))
        self.action_export_usdb_ids.setIcon(icons.Icon.FILE_EXPORT.icon(key))
        self.action_preview.setIcon(icons.Icon.ULTRASTAR_GAME.icon(key))

    def _on_current_song_changed(self, event: gui_events.CurrentSongChanged) -> None:
        song = event.song
        for action in self.menu_songs.actions():
            action.setEnabled(bool(song))
        if not song:
            return
        for action in (
            self.action_open_song_folder,
            self.menu_open_song_in,
            self.action_open_song_in_karedi,
            self.action_open_song_in_performous,
            self.action_open_song_in_tune_perfect,
            self.action_open_song_in_ultrastar_manager,
            self.action_open_song_in_usdx,
            self.action_open_song_in_vocaluxe,
            self.action_open_song_in_yass_reloaded,
            self.action_delete,
            self.action_pin,
            self.action_preview,
            self.menu_custom_data,
        ):
            action.setEnabled(song.is_local())
        self.action_pin.setChecked(song.is_pinned())
        self.action_songs_abort.setEnabled(song.status.can_be_aborted())
