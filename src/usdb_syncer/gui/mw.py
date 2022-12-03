"""usdb_syncer's GUI"""

import logging
import sys
from enum import Enum

from PySide6.QtCore import QObject, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QMainWindow,
    QSplashScreen,
)

from usdb_syncer import settings
from usdb_syncer.gui.forms.MainWindow import Ui_MainWindow
from usdb_syncer.gui.meta_tags_dialog import MetaTagsDialog
from usdb_syncer.gui.progress import run_with_progress
from usdb_syncer.gui.settings_dialog import SettingsDialog
from usdb_syncer.gui.song_table.song_table import SongTable
from usdb_syncer.pdf import generate_song_pdf
from usdb_syncer.song_list_fetcher import SongListFetcher, get_available_songs
from usdb_syncer.song_loader import download_songs
from usdb_syncer.usdb_scraper import UsdbSong


class RatingFilter(Enum):
    """Selectable filters for song ratings."""

    ANY = (0, False)
    EXACT_1 = (1, True)
    EXACT_2 = (2, True)
    EXACT_3 = (3, True)
    EXACT_4 = (4, True)
    EXACT_5 = (5, True)
    MIN_2 = (2, False)
    MIN_3 = (3, False)
    MIN_4 = (4, False)
    MIN_5 = (5, False)

    def __str__(self) -> str:
        if self == RatingFilter.ANY:
            return "Any"
        if self.value[1]:
            return self.value[0] * "★"
        return self.value[0] * "★" + " or more"


class GoldenNotesFilter(Enum):
    """Selectable filters for songs with or without golden notes."""

    ANY = None
    YES = True
    NO = False

    def __str__(self) -> str:
        if self == GoldenNotesFilter.ANY:
            return "Any"
        if self == GoldenNotesFilter.YES:
            return "Yes"
        return "No"


class ViewsFilter(Enum):
    """Selectable filters for songs with a specific view count."""

    ANY = 0
    MIN_100 = 100
    MIN_200 = 200
    MIN_300 = 300
    MIN_400 = 400
    MIN_500 = 500

    def __str__(self) -> str:
        if self == ViewsFilter.ANY:
            return "Any"
        return f"{self.value}+"


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
        self._setup_song_dir()
        self._setup_search()
        self._setup_download()

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
        self.action_generate_song_pdf.triggered.connect(
            lambda: generate_song_pdf(self.table.all_local_songs())
        )

    def _setup_song_dir(self) -> None:
        self.lineEdit_song_dir.setText(settings.get_song_dir())
        self.pushButton_select_song_dir.clicked.connect(self.select_song_dir)

    def _setup_download(self) -> None:
        self.pushButton_downloadSelectedSongs.clicked.connect(
            lambda: download_songs(self.table.selected_song_ids())
        )

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
        slider = self.plainTextEdit.verticalScrollBar()
        slider.setValue(slider.maximum())

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

    def initialize_song_table(self, song_list: list[UsdbSong]) -> None:
        self.table.initialize(song_list)
        self.len_song_list = len(song_list)
        self._update_dynamic_filters(song_list)

    def _select_local_songs(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Song Directory")
        self.table.select_local_songs(directory)

    def _refetch_song_list(self) -> None:
        run_with_progress(
            "Fetching song list...",
            lambda _: get_available_songs(True),
            self._on_song_list_fetched,
        )

    def _on_song_list_fetched(self, song_list: list[UsdbSong]) -> None:
        self.table.set_data(song_list)
        self.len_song_list = len(song_list)
        self._update_dynamic_filters(song_list)

    def _update_dynamic_filters(self, song_list: list[UsdbSong]) -> None:
        def update_filter(selector: QComboBox, attribute: str) -> None:
            items = list(sorted(set(getattr(song, attribute) for song in song_list)))
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
        song_dir = str(QFileDialog.getExistingDirectory(self, "Select Song Directory"))
        self.lineEdit_song_dir.setText(song_dir)
        settings.set_song_dir(song_dir)
        self.table.resync_local_data()

    def _clear_filters(self) -> None:
        self.lineEdit_search.setText("")
        self.comboBox_artist.setCurrentIndex(0)
        self.comboBox_title.setCurrentIndex(0)
        self.comboBox_language.setCurrentIndex(0)
        self.comboBox_edition.setCurrentIndex(0)
        self.comboBox_golden_notes.setCurrentIndex(0)
        self.comboBox_rating.setCurrentIndex(0)
        self.comboBox_views.setCurrentIndex(0)


class Signals(QObject):
    """Custom signals."""

    message_level_time = Signal(str, int, float)


class TextEditLogger(logging.Handler):
    """Handler that logs to the GUI in a thread-safe manner."""

    def __init__(self, mw: MainWindow) -> None:
        super().__init__()
        self.signals = Signals()
        self.signals.message_level_time.connect(mw.log_to_text_edit)

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        self.signals.message_level_time.emit(message, record.levelno, record.created)


def main() -> None:
    app = QApplication(sys.argv)
    app.setOrganizationName("bohning")
    app.setApplicationName("usdb_syncer")
    mw = MainWindow()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8",
        handlers=(
            logging.FileHandler("usdb_syncer.log"),
            logging.StreamHandler(sys.stdout),
            TextEditLogger(mw),
        ),
    )
    pixmap = QPixmap(":/splash/splash.png")
    splash = QSplashScreen(pixmap)
    splash.show()
    QApplication.processEvents()
    splash.showMessage("Loading song database from usdb...", color=Qt.GlobalColor.gray)
    SongListFetcher(False, mw.lineEdit_song_dir.text(), mw.initialize_song_table).run()
    splash.showMessage(
        f"Song database successfully loaded with {mw.len_song_list} songs.",
        color=Qt.GlobalColor.gray,
    )
    mw.showMaximized()
    logging.info("Application successfully loaded.")
    splash.finish(mw)
    app.exec()
