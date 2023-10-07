"""usdb_syncer's GUI"""

import datetime
import logging
import os
import sys
import webbrowser
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QSplashScreen,
)

from usdb_syncer import SongId, settings
from usdb_syncer.constants import SHORT_COMMIT_HASH, VERSION, Usdb
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
from usdb_syncer.usdb_id_file import (
    UsdbIdFileError,
    parse_usdb_id_file,
    write_usdb_id_file,
)
from usdb_syncer.utils import AppPaths, open_file_explorer

_logger = get_logger(__file__)


def get_available_song_ids_from_files(
    file_list: list[str], song_table: SongTable
) -> list[SongId]:
    song_ids: list[SongId] = []
    has_error = False
    for path in file_list:
        try:
            song_ids += parse_usdb_id_file(path)
        except UsdbIdFileError as error:
            _logger.error(f"failed importing file {path}: {str(error)}")
            has_error = True

    # stop import if encounter errors
    if has_error:
        return []

    unique_song_ids = list(set(song_ids))
    unique_song_ids.sort()
    _logger.info(
        f"read {len(file_list)} file(s), "
        f"found {len(unique_song_ids)} "
        f"USDB IDs: {', '.join(str(id) for id in unique_song_ids)}"
    )
    if unavailable_song_ids := [
        song_id for song_id in unique_song_ids if not song_table.get_data(song_id)
    ]:
        _logger.warning(
            f"{len(unavailable_song_ids)}/{len(unique_song_ids)} "
            "imported USDB IDs are not available: "
            f"{', '.join(str(song_id) for song_id in unavailable_song_ids)}"
        )

    if available_song_ids := [
        song_id for song_id in unique_song_ids if song_id not in unavailable_song_ids
    ]:
        _logger.info(
            f"available {len(available_song_ids)}/{len(unique_song_ids)} "
            "imported USDB IDs will be selected: "
            f"{', '.join(str(song_id) for song_id in available_song_ids)}"
        )

    return available_song_ids


class MainWindow(Ui_MainWindow, QMainWindow):
    """The app's main window and entry point to the GUI."""

    _search_timer: QTimer

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)
        self.threadpool = QThreadPool(self)
        self.tree = FilterTree(self)
        self.table = SongTable(self)
        self._setup_statusbar()
        self._setup_log()
        self._setup_toolbar()
        self._setup_shortcuts()
        self._setup_song_dir()
        self._setup_search()
        self._setup_buttons()
        self._restore_state()

    def _setup_statusbar(self) -> None:
        self._status_label = QLabel(self)
        self.statusbar.addWidget(self._status_label)

        def on_count_changed(shown_count: int) -> None:
            self._status_label.setText(
                f"{shown_count} out of {len(self.table.get_all_data())} songs shown."
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
            (self.action_find_local_songs, self._stage_local_songs),
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
        set_shortcut("Ctrl+.", self, lambda: DebugConsole(self).show())

    def _setup_song_dir(self) -> None:
        self.lineEdit_song_dir.setText(str(settings.get_song_dir()))
        self.pushButton_select_song_dir.clicked.connect(self.select_song_dir)

    def _setup_buttons(self) -> None:
        self.button_download.clicked.connect(self._download_selection)

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
        self.table.set_data(songs)
        self._update_dynamic_filters(songs)

    def _stage_local_songs(self) -> None:
        if directory := QFileDialog.getExistingDirectory(self, "Select Song Directory"):
            self.table.select_local_songs(Path(directory))

    def _refetch_song_list(self) -> None:
        run_with_progress(
            "Fetching song list...",
            lambda _: get_all_song_data(True),
            self.initialize_song_table,
        )

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
        self._set_song_dir(song_dir)

    def _set_song_dir(self, song_dir: str) -> None:
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
        if available_song_ids := get_available_song_ids_from_files(
            file_list, self.table
        ):
            # select available songs to prepare Download
            self.table.set_selection_to_song_ids(available_song_ids)

    def _export_usdb_ids_to_file(self) -> None:
        selected_ids = list(song.data.song_id for song in self.table.selected_songs())
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

        write_usdb_id_file(path, selected_ids)
        _logger.info(f"exported {len(selected_ids)} USDB IDs to {path}")

    def _show_current_song_in_usdb(self) -> None:
        if song := self.table.current_song():
            _logger.debug(f"Opening song page #{song.data.song_id} in webbrowser.")
            webbrowser.open(f"{Usdb.BASE_URL}?link=detail&id={int(song.data.song_id)}")
        else:
            _logger.info("No current song.")

    def _open_current_song_folder(self) -> None:
        if song := self.table.current_song():
            if song.local_files.usdb_path:
                open_file_explorer(song.local_files.usdb_path.parent)
            else:
                _logger.info("Song does not exist locally.")
        else:
            _logger.info("No current song.")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.table.save_state()
        self._save_state()
        dump_available_songs(list(s.data for s in self.table.get_all_data()))
        event.accept()

    def _restore_state(self) -> None:
        self.restoreGeometry(settings.get_geometry_main_window())
        self.restoreState(settings.get_state_main_window())
        self.dock_log.restoreGeometry(settings.get_geometry_log_dock())

    def _save_state(self) -> None:
        settings.set_geometry_main_window(self.saveGeometry())
        settings.set_state_main_window(self.saveState())
        settings.set_geometry_log_dock(self.dock_log.saveGeometry())


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
    splash.showMessage("Loading song database ...", color=Qt.GlobalColor.gray)
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
    painter.drawText(
        0,
        0,
        428,
        140,
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        VERSION,
    )
    font.setPointSize(12)
    painter.setFont(font)
    painter.drawText(
        0,
        0,
        428,
        155,
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        SHORT_COMMIT_HASH,
    )
    painter.end()
    return QSplashScreen(canvas)


def _init_app() -> QApplication:
    app = QApplication(sys.argv)
    app.setOrganizationName("bohning")
    app.setApplicationName("usdb_syncer")
    app.setWindowIcon(QIcon(":/app/appicon_128x128.png"))
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
