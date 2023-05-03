"""usdb_syncer's GUI"""

import datetime
import logging
import os
import sys

from PySide6.QtCore import QObject, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QSplashScreen,
)

from usdb_syncer import settings
from usdb_syncer.gui.debug_console import DebugConsole
from usdb_syncer.gui.ffmpeg_dialog import check_ffmpeg
from usdb_syncer.gui.forms.MainWindow import Ui_MainWindow
from usdb_syncer.gui.meta_tags_dialog import MetaTagsDialog
from usdb_syncer.gui.progress import run_with_progress
from usdb_syncer.gui.settings_dialog import SettingsDialog
from usdb_syncer.gui.song_table.song_table import SongTable
from usdb_syncer.gui.usdb_login_dialog import UsdbLoginDialog
from usdb_syncer.gui.utils import scroll_to_bottom, set_shortcut
from usdb_syncer.logger import get_logger
from usdb_syncer.pdf import generate_song_pdf
from usdb_syncer.song_data import SongData
from usdb_syncer.song_filters import GoldenNotesFilter, RatingFilter, ViewsFilter
from usdb_syncer.song_list_fetcher import (
    dump_available_songs,
    get_all_song_data,
    resync_song_data,
)
from usdb_syncer.usdb_id_file import UsdbIdFile
from usdb_syncer.utils import AppPaths, open_file_explorer

_logger = get_logger(__file__)


class MainWindow(Ui_MainWindow, QMainWindow):
    """The app's main window and entry point to the GUI."""

    _search_timer: QTimer

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)
        self.threadpool = QThreadPool(self)
        self._setup_table()
        self._setup_statusbar()
        self._setup_log()
        self._setup_toolbar()
        self._setup_shortcuts()
        self._setup_song_dir()
        self._setup_search()
        self._setup_buttons()
        self._restore_state()

    def _setup_table(self) -> None:
        self.table = SongTable(
            self,
            self.view_list,
            self.view_batch,
            self.menu_songs,
            self.menu_batch,
            self.bar_download_progress,
            self.label_download_progress,
        )

    def _setup_statusbar(self) -> None:
        self._status_label = QLabel(self)
        self.statusbar.addWidget(self._status_label)

        def on_count_changed(list_count: int, batch_count: int) -> None:
            total = len(self.table.get_all_data())
            self._status_label.setText(
                f"{list_count} out of {total} songs shown. {batch_count} in batch."
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
            (self.action_songs_to_batch, self.table.stage_selection),
            (self.action_batch_remove, self.table.unstage_selection),
            (self.action_find_local_songs, self._stage_local_songs),
            (self.action_refetch_song_list, self._refetch_song_list),
            (self.action_usdb_login, lambda: UsdbLoginDialog(self).show()),
            (self.action_meta_tags, lambda: MetaTagsDialog(self).show()),
            (self.action_settings, lambda: SettingsDialog(self).show()),
            (self.action_generate_song_pdf, self._generate_song_pdf),
            (self.action_import_usdb_ids, self._import_usdb_ids_from_files),
            (self.action_export_usdb_ids, self._export_usdb_ids_to_file),
            (self.action_show_log, lambda: open_file_explorer(AppPaths.log)),
        ):
            action.triggered.connect(func)

    def _download_selection(self) -> None:
        check_ffmpeg(self, self.table.download_selection)

    def _download_batch(self) -> None:
        check_ffmpeg(self, self.table.download_batch)

    def _setup_shortcuts(self) -> None:
        set_shortcut("Ctrl+.", self, lambda: DebugConsole(self).show())

    def _setup_song_dir(self) -> None:
        self.lineEdit_song_dir.setText(str(settings.get_song_dir()))
        self.pushButton_select_song_dir.clicked.connect(self.select_song_dir)

    def _setup_buttons(self) -> None:
        self.button_batch_download.clicked.connect(self._download_batch)
        self.button_batch_clear.clicked.connect(self.table.clear_batch)

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
        for combo_box, setter in (
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
        scroll_to_bottom(self.plainTextEdit)

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

    def initialize_song_table(self, songs: tuple[SongData, ...]) -> None:
        self.table.initialize(songs)
        self._update_dynamic_filters(songs)

    def _stage_local_songs(self) -> None:
        if directory := QFileDialog.getExistingDirectory(self, "Select Song Directory"):
            self.table.stage_local_songs(directory)

    def _refetch_song_list(self) -> None:
        run_with_progress(
            "Fetching song list...",
            lambda _: get_all_song_data(True),
            self._on_song_list_fetched,
        )

    def _on_song_list_fetched(self, songs: tuple[SongData, ...]) -> None:
        self.table.set_data(songs)
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

        for selector, name in (
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
        file_list = QFileDialog.getOpenFileNames(
            self,
            caption="Select one or more files to import USDB IDs from",
            dir=os.getcwd(),
            filter="JSON, USDB IDs, Weblinks (*.json *.usdb_ids *.url *.webloc *.desktop)",
        )[0]
        if not file_list:
            _logger.info("no files selected to import USDB IDs from")
            return
        file_parsers = [UsdbIdFile.parse(path) for path in file_list]
        has_error = False
        for count, parser in enumerate(file_parsers):
            if parser.error:
                _logger.error(
                    f"failed importing file {file_list[count]}: {str(parser.error)}"
                )
                has_error = True
        # stop import if encounter errors
        if has_error:
            return
        song_ids = [id for parser in file_parsers for id in parser.ids]
        unique_song_ids = list(set(song_ids))
        unique_song_ids.sort()
        _logger.info(
            f"read {len(file_list)} file(s), "
            f"found {len(unique_song_ids)} "
            f"USDB IDs: {', '.join(str(id) for id in unique_song_ids)}"
        )
        if unavailable_song_ids := [
            song_id for song_id in unique_song_ids if not self.table.get_data(song_id)
        ]:
            _logger.warning(
                f"{len(unavailable_song_ids)}/{len(unique_song_ids)} "
                "imported USDB IDs are not available: "
                f"{', '.join(str(song_id) for song_id in unavailable_song_ids)}"
            )
        if available_song_ids := [
            song_id
            for song_id in unique_song_ids
            if song_id not in unavailable_song_ids
        ]:
            # select available songs to prepare Download
            _logger.info(
                f"available {len(available_song_ids)}/{len(unique_song_ids)} "
                "imported USDB IDs are added to Batch: "
                f"{', '.join(str(song_id) for song_id in available_song_ids)}"
            )
            self.table.stage_song_ids(available_song_ids)

    def _export_usdb_ids_to_file(self) -> None:
        selected_ids = self.table.batch_ids()
        if not selected_ids:
            _logger.info("skipping export: no songs in Batch")
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

        id_file = UsdbIdFile(list(selected_ids))
        id_file.write(path)
        _logger.info(f"exported {len(list(selected_ids))} USDB IDs to {path}")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.table.save_state()
        self._save_state()
        dump_available_songs(list(s.data for s in self.table.get_all_data()))
        event.accept()

    def _restore_state(self) -> None:
        self.restoreGeometry(settings.get_geometry_main_window())
        self.splitter_main.restoreState(settings.get_state_splitter_main())
        self.splitter_bottom.restoreState(settings.get_state_splitter_bottom())

    def _save_state(self) -> None:
        settings.set_geometry_main_window(self.saveGeometry())
        settings.set_state_splitter_main(self.splitter_main.saveState())
        settings.set_state_splitter_bottom(self.splitter_bottom.saveState())


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
    splash = generate_splashscreen()
    splash.show()
    QApplication.processEvents()
    splash.showMessage("Loading song database from usdb...", color=Qt.GlobalColor.gray)
    songs = get_all_song_data(False)
    mw.initialize_song_table(songs)
    splash.showMessage(
        f"Song database successfully loaded with {len(songs)} songs.",
        color=Qt.GlobalColor.gray,
    )
    mw.show()
    logging.info("Application successfully loaded.")
    splash.finish(mw)


def generate_splashscreen() -> QSplashScreen:
    canvas = QPixmap(":/splash/splash.png")
    painter = QPainter(canvas)
    painter.setPen(QColor(0, 174, 239))  # light blue
    font = QFont()
    font.setFamily("Kozuka Gothic Pro")
    font.setPointSize(24)
    painter.setFont(font)
    version = "0.1.0"
    painter.drawText(
        0,
        0,
        428,
        140,
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        version,
    )
    painter.end()
    return QSplashScreen(canvas)


def _init_app() -> QApplication:
    app = QApplication(sys.argv)
    app.setOrganizationName("bohning")
    app.setApplicationName("usdb_syncer")
    return app


def _configure_logging(mw: MainWindow) -> None:
    logging.basicConfig(
        level=logging.DEBUG,
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
