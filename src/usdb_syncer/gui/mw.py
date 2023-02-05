"""usdb_syncer's GUI"""

import datetime
import logging
import os
import sys

from PySide6.QtCore import QObject, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QMainWindow,
    QSplashScreen,
)

from usdb_syncer import SongId, settings
from usdb_syncer.exchange_format import get_song_ids_from_files, write_song_ids_to_file
from usdb_syncer.gui.debug_console import DebugConsole
from usdb_syncer.gui.ffmpeg_dialog import check_ffmpeg
from usdb_syncer.gui.forms.MainWindow import Ui_MainWindow
from usdb_syncer.gui.meta_tags_dialog import MetaTagsDialog
from usdb_syncer.gui.progress import run_with_progress
from usdb_syncer.gui.settings_dialog import SettingsDialog
from usdb_syncer.gui.song_table.song_table import SongTable
from usdb_syncer.gui.utils import scroll_to_bottom, set_shortcut
from usdb_syncer.pdf import generate_song_pdf
from usdb_syncer.song_data import LocalFiles, SongData
from usdb_syncer.song_filters import GoldenNotesFilter, RatingFilter, ViewsFilter
from usdb_syncer.song_list_fetcher import get_all_song_data, resync_song_data
from usdb_syncer.song_loader import DownloadInfo, download_songs
from usdb_syncer.utils import AppPaths, open_file_explorer


class SongSignals(QObject):
    """Signals relating to songs."""

    started = Signal(SongId)
    finished = Signal(SongId, LocalFiles)


class MainWindow(Ui_MainWindow, QMainWindow):
    """The app's main window and entry point to the GUI."""

    _search_timer: QTimer
    len_song_list = 0

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)
        self.threadpool = QThreadPool(self)
        self._setup_table()
        self._setup_log()
        self._setup_toolbar()
        self._setup_shortcuts()
        self._setup_song_dir()
        self._setup_search()
        self._setup_download()
        self._setup_signals()

    def _setup_table(self) -> None:
        self.table = SongTable(self, self.tableView_availableSongs)
        self.table.connect_row_count_changed(
            lambda c: self.statusbar.showMessage(f"{c} songs found.")
        )
        self.table.connect_selected_rows_changed(self._on_selected_rows_changed)
        self._on_selected_rows_changed(self.table.selected_row_count())

    def _setup_log(self) -> None:
        self.plainTextEdit.setReadOnly(True)
        self._infos: list[tuple[str, float]] = []
        self._warnings: list[tuple[str, float]] = []
        self._errors: list[tuple[str, float]] = []
        self.toolButton_infos.toggled.connect(self._on_log_filter_changed)
        self.toolButton_warnings.toggled.connect(self._on_log_filter_changed)
        self.toolButton_errors.toggled.connect(self._on_log_filter_changed)

    def _setup_toolbar(self) -> None:
        self.action_select_local_songs.triggered.connect(self._select_local_songs)
        self.action_refetch_song_list.triggered.connect(self._refetch_song_list)
        self.action_meta_tags.triggered.connect(lambda: MetaTagsDialog(self).show())
        self.action_settings.triggered.connect(lambda: SettingsDialog(self).show())
        self.action_generate_song_pdf.triggered.connect(self._generate_song_pdf)
        self.action_import_usdb_ids.triggered.connect(self._import_usdb_ids_from_files)
        self.action_export_usdb_ids.triggered.connect(self._export_usdb_ids_to_file)
        self.action_show_log.triggered.connect(
            lambda: open_file_explorer(os.path.dirname(AppPaths.log))
        )

    def _setup_shortcuts(self) -> None:
        set_shortcut("Ctrl+.", self, lambda: DebugConsole(self).show())

    def _setup_song_dir(self) -> None:
        self.lineEdit_song_dir.setText(settings.get_song_dir())
        self.pushButton_select_song_dir.clicked.connect(self.select_song_dir)

    def _setup_download(self) -> None:
        self.pushButton_downloadSelectedSongs.clicked.connect(
            self._download_selected_songs
        )

    def _download_selected_songs(self) -> None:
        def _download_songs() -> None:
            songs = [
                DownloadInfo.from_song_data(song)
                for song_id in self.table.selected_song_ids()
                if (song := self.table.get_data(song_id))
            ]
            download_songs(
                songs, self.song_signals.started.emit, self.song_signals.finished.emit
            )

        check_ffmpeg(self, _download_songs)

    def _setup_search(self) -> None:
        self._populate_search_filters()
        self._connect_search_filters()
        self.clear_filters.clicked.connect(self._clear_filters)

    def _populate_search_filters(self) -> None:
        for rating in RatingFilter:
            self.comboBox_rating.addItem(str(rating), rating.value)
        for golden in GoldenNotesFilter:
            self.comboBox_golden_notes.addItem(str(golden), golden.value)
        for views in ViewsFilter:
            self.comboBox_views.addItem(str(views), views.value)

    def _connect_search_filters(self) -> None:
        self.lineEdit_search.textChanged.connect(self.table.set_text_filter)
        for (combo_box, setter) in (
            (self.comboBox_artist, self.table.set_artist_filter),
            (self.comboBox_title, self.table.set_title_filter),
            (self.comboBox_language, self.table.set_language_filter),
            (self.comboBox_edition, self.table.set_edition_filter),
        ):
            combo_box.currentIndexChanged.connect(
                lambda idx, combo_box=combo_box, setter=setter: setter(
                    "" if not idx else combo_box.currentText()
                )
            )
        self.comboBox_rating.currentIndexChanged.connect(
            lambda: self.table.set_rating_filter(*self.comboBox_rating.currentData())
        )
        self.comboBox_golden_notes.currentIndexChanged.connect(
            lambda: self.table.set_golden_notes_filter(
                self.comboBox_golden_notes.currentData()
            )
        )
        self.comboBox_views.currentIndexChanged.connect(
            lambda: self.table.set_views_filter(self.comboBox_views.currentData())
        )

    def _on_log_filter_changed(self) -> None:
        messages = []
        if self.toolButton_infos.isChecked():
            messages += self._infos
        if self.toolButton_warnings.isChecked():
            messages += self._warnings
        if self.toolButton_errors.isChecked():
            messages += self._errors
        messages.sort(key=lambda m: m[1])
        self.plainTextEdit.setPlainText("\n".join(m[0] for m in messages))
        scroll_to_bottom(self.plainTextEdit)

    def _on_selected_rows_changed(self, count: int) -> None:
        s__ = "" if count == 1 else "s"
        self.pushButton_downloadSelectedSongs.setText(f"Download {count} song{s__}!")
        self.pushButton_downloadSelectedSongs.setEnabled(bool(count))

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

    def _setup_signals(self) -> None:
        self.song_signals = SongSignals()
        self.song_signals.finished.connect(self._update_downloaded_song)

    def _update_downloaded_song(self, song_id: SongId, files: LocalFiles) -> None:
        if old := self.table.get_data(song_id):
            new = old.with_local_files(files)
            self.table.update_item(new)

    def initialize_song_table(self, songs: tuple[SongData, ...]) -> None:
        self.table.initialize(songs)
        self.len_song_list = len(songs)
        self._update_dynamic_filters(songs)

    def _select_local_songs(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Song Directory")
        self.table.select_local_songs(directory)

    def _refetch_song_list(self) -> None:
        run_with_progress(
            "Fetching song list...",
            lambda _: get_all_song_data(True),
            self._on_song_list_fetched,
        )

    def _on_song_list_fetched(self, songs: tuple[SongData, ...]) -> None:
        self.table.set_data(songs)
        self.len_song_list = len(songs)
        self._update_dynamic_filters(songs)

    def _update_dynamic_filters(self, songs: tuple[SongData, ...]) -> None:
        def update_filter(selector: QComboBox, attribute: str) -> None:
            items = list(sorted(set(getattr(song.data, attribute) for song in songs)))
            items.insert(0, "Any")
            current_text = selector.currentText()
            try:
                new_index = items.index(current_text)
            except ValueError:
                new_index = 0
            selector.blockSignals(True)
            selector.clear()
            selector.addItems(items)
            selector.setCurrentIndex(new_index)
            selector.blockSignals(False)
            if current_text != selector.currentText():
                selector.currentIndexChanged.emit(new_index)  # type: ignore

        for (selector, name) in (
            (self.comboBox_artist, "artist"),
            (self.comboBox_title, "title"),
            (self.comboBox_language, "language"),
            (self.comboBox_edition, "edition"),
        ):
            update_filter(selector, name)

    def select_song_dir(self) -> None:
        song_dir = QFileDialog.getExistingDirectory(self, "Select Song Directory")
        if not song_dir:
            return
        self.lineEdit_song_dir.setText(song_dir)
        settings.set_song_dir(song_dir)
        data = resync_song_data(self.table.get_all_data())
        self.table.set_data(data)

    def _clear_filters(self) -> None:
        self.lineEdit_search.setText("")
        self.comboBox_artist.setCurrentIndex(0)
        self.comboBox_title.setCurrentIndex(0)
        self.comboBox_language.setCurrentIndex(0)
        self.comboBox_edition.setCurrentIndex(0)
        self.comboBox_golden_notes.setCurrentIndex(0)
        self.comboBox_rating.setCurrentIndex(0)
        self.comboBox_views.setCurrentIndex(0)

    def _generate_song_pdf(self) -> None:
        fname = f"{datetime.datetime.now():%Y-%m-%d}_songlist.pdf"
        path = os.path.join(settings.get_song_dir(), fname)
        path = QFileDialog.getSaveFileName(self, dir=path, filter="PDF (*.pdf)")[0]
        if path:
            generate_song_pdf(self.table.all_local_songs(), path)

    def _import_usdb_ids_from_files(self) -> None:
        logger = logging.getLogger()
        file_list = QFileDialog.getOpenFileNames(
            self,
            caption="Select one or more files to import USDB IDs from",
            dir=os.getcwd(),
            filter="CSV or Weblink (*.csv *.url)",
        )[0]
        list_of_song_id_lists = [get_song_ids_from_files(path) for path in file_list]
        song_ids = [id for sublist in list_of_song_id_lists for id in sublist]
        unique_song_ids = list(set(song_ids))
        logger.info(
            f"read {len(file_list)} file(s), "
            f"found {len(unique_song_ids)} "
            f"USDB IDs: {[str(id) for id in unique_song_ids]}"
        )
        songs = [
            DownloadInfo.from_song_data(song)
            for song_id in unique_song_ids
            if (song := self.table.get_data(song_id))
        ]
        if unavailable_songs := [
            song_id for song_id in unique_song_ids if not self.table.get_data(song_id)
        ]:
            logger.warning(
                "some imported USDB IDs are not available: "
                f"{[str(song_id) for song_id in unavailable_songs]}"
            )

        download_songs(
            songs, self.song_signals.started.emit, self.song_signals.finished.emit
        )

    def _export_usdb_ids_to_file(self) -> None:
        logger = logging.getLogger()
        selected_ids = [song_id for song_id in self.table.selected_song_ids()]
        if not selected_ids:
            logger.error("skipping export: no songs selected")
            return

        # Note: automatically checks if file already exists
        path = QFileDialog.getSaveFileName(
            self,
            caption="Select export file for USDB IDs",
            dir=os.getcwd(),
            filter="CSV (*.csv)",
        )[0]
        if not path:
            logger.info("export aborted")
            return

        write_song_ids_to_file(path, selected_ids)
        logger.info(f"exported {len(selected_ids)} USDB IDs to {path}")


class LogSignal(QObject):
    """Signal used by the logger."""

    message_level_time = Signal(str, int, float)


class TextEditLogger(logging.Handler):
    """Handler that logs to the GUI in a thread-safe manner."""

    def __init__(self, mw: MainWindow) -> None:
        super().__init__()
        self.signals = LogSignal()
        self.signals.message_level_time.connect(mw.log_to_text_edit)

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        self.signals.message_level_time.emit(message, record.levelno, record.created)


def main() -> None:
    app = _init_app()
    mw = MainWindow()
    _configure_logging(mw)
    _load_main_window(mw)
    app.exec()


def _load_main_window(mw: MainWindow) -> None:
    splash = QSplashScreen(QPixmap(":/splash/splash.png"))
    splash.show()
    QApplication.processEvents()
    splash.showMessage("Loading song database from usdb...", color=Qt.GlobalColor.gray)
    songs = get_all_song_data(False)
    mw.initialize_song_table(songs)
    splash.showMessage(
        f"Song database successfully loaded with {mw.len_song_list} songs.",
        color=Qt.GlobalColor.gray,
    )
    mw.showMaximized()
    logging.info("Application successfully loaded.")
    splash.finish(mw)


def _init_app() -> QApplication:
    app = QApplication(sys.argv)
    app.setOrganizationName("bohning")
    app.setApplicationName("usdb_syncer")
    return app


def _configure_logging(mw: MainWindow) -> None:
    logging.basicConfig(
        level=logging.INFO,
        style="{",
        format="{asctime} [{levelname}] {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8",
        handlers=(
            logging.FileHandler(AppPaths.log),
            logging.StreamHandler(sys.stdout),
            TextEditLogger(mw),
        ),
    )
