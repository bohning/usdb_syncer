"""usdb_dl's GUI"""

import datetime
import logging
import os
import sys
from glob import glob
from typing import Any

# maybe reportlab is better suited?
from pdfme import build_pdf  # type: ignore
from PySide6.QtCore import QObject, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHeaderView,
    QMainWindow,
    QSplashScreen,
)

from usdb_dl import SongId, settings
from usdb_dl.gui.forms.MainWindow import Ui_MainWindow
from usdb_dl.gui.meta_tags_dialog import MetaTagsDialog
from usdb_dl.gui.settings_dialog import SettingsDialog
from usdb_dl.gui.sort_filter_proxy_model import SortFilterProxyModel
from usdb_dl.gui.table_model import TableModel
from usdb_dl.song_list_fetcher import SongListFetcher
from usdb_dl.song_loader import download_songs
from usdb_dl.usdb_scraper import SongMeta


class MainWindow(Ui_MainWindow, QMainWindow):
    """The app's main window and entry point to the GUI."""

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)

        self.threadpool = QThreadPool(self)

        self.plainTextEdit.setReadOnly(True)
        self.len_song_list = 0
        self._infos: list[tuple[str, float]] = []
        self._warnings: list[tuple[str, float]] = []
        self._errors: list[tuple[str, float]] = []
        self.toolButton_infos.toggled.connect(self._on_log_filter_changed)
        self.toolButton_warnings.toggled.connect(self._on_log_filter_changed)
        self.toolButton_errors.toggled.connect(self._on_log_filter_changed)

        self.action_meta_tags.triggered.connect(lambda: MetaTagsDialog(self).show())
        self.action_settings.triggered.connect(lambda: SettingsDialog(self).show())
        self.action_generate_song_pdf.triggered.connect(self.generate_song_pdf)

        self.lineEdit_song_dir.setText(settings.get_song_dir())

        self.pushButton_get_songlist.clicked.connect(lambda: self.refresh(True))
        self.pushButton_downloadSelectedSongs.clicked.connect(
            self.download_selected_songs
        )
        self.pushButton_select_song_dir.clicked.connect(self.select_song_dir)

        self.model = TableModel(self)

        self.filter_proxy_model = SortFilterProxyModel(self)
        self.filter_proxy_model.setSourceModel(self.model)

        self.lineEdit_search.textChanged.connect(self.set_text_filter)
        self.tableView_availableSongs.setModel(self.filter_proxy_model)

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

    def set_text_filter(self, search: str) -> None:
        self.filter_proxy_model.set_text_filter(search)
        self.statusbar.showMessage(f"{self.filter_proxy_model.rowCount()} songs found.")

    @Slot(str)
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

    def refresh(self, force_reload: bool) -> None:
        self.pushButton_get_songlist.setEnabled(False)
        self.threadpool.start(SongListFetcher(force_reload, self.on_song_list_fetched))

    def on_song_list_fetched(self, song_list: list[SongMeta]) -> None:
        # TODO: remove all existing items in the model!
        self.model.load_data(song_list)
        self.pushButton_get_songlist.setEnabled(True)
        self.len_song_list = len(song_list)
        artists = set()
        titles = []
        languages = set()
        editions = set()
        self.model.removeRows(0, self.model.rowCount())

        for song in song_list:
            artists.add(song.artist)
            titles.append(song.title)
            languages.add(song.language)
            editions.add(song.edition)

        self.statusbar.showMessage(f"{self.filter_proxy_model.rowCount()} songs found.")

        self.comboBox_artist.addItems(list(sorted(set(artists))))
        self.comboBox_title.addItems(list(sorted(set(titles))))
        self.comboBox_language.addItems(list(sorted(set(languages))))
        self.comboBox_edition.addItems(list(sorted(set(editions))))

        header = self.tableView_availableSongs.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 84)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, header.sectionSize(5))
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(6, header.sectionSize(6))
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(7, header.sectionSize(7))
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(8, 24)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(9, 24)
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(10, 24)
        header.setSectionResizeMode(11, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(11, 24)
        header.setSectionResizeMode(12, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(12, 24)

    def select_song_dir(self) -> None:
        song_dir = str(QFileDialog.getExistingDirectory(self, "Select Song Directory"))
        self.lineEdit_song_dir.setText(song_dir)
        settings.set_song_dir(song_dir)
        self._crawl_song_dir()

    def _crawl_song_dir(self) -> None:
        checks: list[tuple[SongId, dict[int, bool]]] = []
        for _path, dirs, files in os.walk(self.lineEdit_song_dir.text()):
            dirs.sort()
            for file in files:
                if file.endswith(".usdb"):
                    song_id = file.removesuffix(".usdb")
                    check_indices: dict[int, bool] = {}
                    checks.append((SongId(song_id), check_indices))
                    for song_file in files:
                        if song_file.endswith(".txt"):
                            check_indices[8] = True
                        if (
                            song_file.endswith(".mp3")
                            or song_file.endswith(".ogg")
                            or song_file.endswith("m4a")
                            or song_file.endswith("opus")
                            or song_file.endswith("ogg")
                        ):
                            check_indices[9] = True
                        if song_file.endswith(".mp4") or song_file.endswith(".webm"):
                            check_indices[10] = True
                        if song_file.endswith("[CO].jpg"):
                            check_indices[11] = True
                        if song_file.endswith("[BG].jpg"):
                            check_indices[12] = True
        self.model.set_checks(checks)

    def download_selected_songs(self) -> None:
        indices = self.tableView_availableSongs.selectionModel().selectedRows()
        ids = self.model.ids_for_indices(indices)
        download_songs(ids)

    def generate_song_pdf(self) -> None:
        document: dict[str, Any] = {}
        document["style"] = {"margin_bottom": 15, "text_align": "j"}
        document["formats"] = {"url": {"c": "blue", "u": 1}, "title": {"b": 1, "s": 13}}
        document["sections"] = []
        section1: dict[str, list[Any]] = {}
        document["sections"].append(section1)
        content1: list[Any] = []
        section1["content"] = content1
        date = datetime.datetime.now()
        content1.append(
            {
                ".": f"Songlist ({date:%Y-%m-%d})",
                "style": "title",
                "label": "title1",
                "outline": {"level": 1, "text": "A different title 1"},
            }
        )

        pattern = f"{self.lineEdit_song_dir.text()}/**/*.usdb"
        for path in glob(pattern, recursive=True):
            id_str = os.path.basename(path).removesuffix(".usdb")
            if (song_id := SongId.try_from(id_str)) is None:
                continue
            if not (song := self.model.item_for_id(song_id)):
                continue
            data = f"{song_id}\t\t{song.artist}\t\t{song.title}\t\t{song.language}"
            content1.append([data.replace("’", "'")])

        with open(f"{date:%Y-%m-%d}_songlist.pdf", "wb") as file:
            build_pdf(document, file)


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
    app.setApplicationName("usdb_dl")
    mw = MainWindow()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8",
        handlers=(
            logging.FileHandler("usdb_dl.log"),
            logging.StreamHandler(sys.stdout),
            TextEditLogger(mw),
        ),
    )
    pixmap = QPixmap(":/splash/splash.png")
    splash = QSplashScreen(pixmap)
    splash.show()
    QApplication.processEvents()
    splash.showMessage("Loading song database from usdb...", color=Qt.GlobalColor.gray)
    SongListFetcher(False, mw.on_song_list_fetched).run()
    splash.showMessage(
        f"Song database successfully loaded with {mw.len_song_list} songs.",
        color=Qt.GlobalColor.gray,
    )
    mw.showMaximized()
    logging.info("Application successfully loaded.")
    splash.finish(mw)
    app.exec()
