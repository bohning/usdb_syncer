"""usdb_dl's GUI"""

import datetime
import json
import logging
import os
import sys
import time
from typing import Any, cast

import appdirs

# maybe reportlab is better suited?
from pdfme import build_pdf  # type: ignore
from PySide6.QtCore import (
    QEvent,
    QObject,
    QSortFilterProxyModel,
    Qt,
    QThreadPool,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QContextMenuEvent,
    QIcon,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHeaderView,
    QMainWindow,
    QMenu,
    QSplashScreen,
)

from usdb_dl import SongId, usdb_scraper
from usdb_dl.gui.forms.MainWindow import Ui_MainWindow
from usdb_dl.gui.meta_tags_dialog import MetaTagsDialog
from usdb_dl.options import (
    AudioCodec,
    AudioContainer,
    AudioOptions,
    BackgroundOptions,
    Browser,
    Encoding,
    Newline,
    Options,
    TxtOptions,
    VideoCodec,
    VideoContainer,
    VideoFps,
    VideoOptions,
    VideoResolution,
)
from usdb_dl.song_loader import SongLoader
from usdb_dl.usdb_scraper import SongMeta

# from pytube import extract


class MainWindow(Ui_MainWindow, QMainWindow):
    """The app's main window and entry point to the GUI."""

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)

        self.threadpool = QThreadPool(self)

        self.plainTextEdit.setReadOnly(True)
        self._infos: list[tuple[str, float]] = []
        self._warnings: list[tuple[str, float]] = []
        self._errors: list[tuple[str, float]] = []
        self.toolButton_infos.toggled.connect(self._on_log_filter_changed)
        self.toolButton_warnings.toggled.connect(self._on_log_filter_changed)
        self.toolButton_errors.toggled.connect(self._on_log_filter_changed)

        self.action_meta_tags.triggered.connect(lambda: MetaTagsDialog(self).show())

        self.lineEdit_song_dir.setText(os.path.join(os.getcwd(), "songs"))

        self.pushButton_get_songlist.clicked.connect(lambda: self.refresh(True))
        self.pushButton_downloadSelectedSongs.clicked.connect(
            self.download_selected_songs
        )
        self.pushButton_select_song_dir.clicked.connect(self.select_song_dir)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderItem(
            0, QStandardItem(QIcon(":/icons/id.png"), "ID")
        )
        self.model.setHorizontalHeaderItem(
            1, QStandardItem(QIcon(":/icons/artist.png"), "Artist")
        )
        self.model.setHorizontalHeaderItem(
            2, QStandardItem(QIcon(":/icons/title.png"), "Title")
        )
        self.model.setHorizontalHeaderItem(
            3, QStandardItem(QIcon(":/icons/language.png"), "Language")
        )
        self.model.setHorizontalHeaderItem(
            4, QStandardItem(QIcon(":/icons/edition.png"), "Edition")
        )
        self.model.setHorizontalHeaderItem(
            5, QStandardItem(QIcon(":/icons/golden_notes.png"), "")
        )
        self.model.setHorizontalHeaderItem(
            6, QStandardItem(QIcon(":/icons/rating.png"), "")
        )
        self.model.setHorizontalHeaderItem(
            7, QStandardItem(QIcon(":/icons/views.png"), "")
        )
        self.model.setHorizontalHeaderItem(
            8, QStandardItem(QIcon(":/icons/text.png"), "")
        )
        self.model.setHorizontalHeaderItem(
            9, QStandardItem(QIcon(":/icons/audio.png"), "")
        )
        self.model.setHorizontalHeaderItem(
            10, QStandardItem(QIcon(":/icons/video.png"), "")
        )
        self.model.setHorizontalHeaderItem(
            11, QStandardItem(QIcon(":/icons/cover.png"), "")
        )
        self.model.setHorizontalHeaderItem(
            12, QStandardItem(QIcon(":/icons/background.png"), "")
        )

        self.filter_proxy_model = QSortFilterProxyModel()
        self.filter_proxy_model.setSourceModel(self.model)
        self.filter_proxy_model.setFilterCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        self.filter_proxy_model.setFilterKeyColumn(-1)

        self.lineEdit_search.textChanged.connect(self.set_filter_regular_expression)
        self.tableView_availableSongs.setModel(self.filter_proxy_model)
        self.tableView_availableSongs.installEventFilter(self)

        self._populate_comboboxes()
        self.comboBox_search_column.currentIndexChanged.connect(
            self.set_filter_key_column
        )
        self.checkBox_case_sensitive.stateChanged.connect(self.set_case_sensitivity)

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

    def set_filter_regular_expression(self, regexp: str) -> None:
        self.filter_proxy_model.setFilterRegularExpression(regexp)
        self.statusbar.showMessage(f"{self.filter_proxy_model.rowCount()} songs found.")

    def set_filter_key_column(self, index: int) -> None:
        if index == 0:
            self.filter_proxy_model.setFilterKeyColumn(-1)
        else:
            self.filter_proxy_model.setFilterKeyColumn(index)
        self.statusbar.showMessage(f"{self.filter_proxy_model.rowCount()} songs found.")

    def set_case_sensitivity(self, state: int) -> None:
        if state == 0:
            self.filter_proxy_model.setFilterCaseSensitivity(
                Qt.CaseSensitivity.CaseInsensitive
            )
        else:
            self.filter_proxy_model.setFilterCaseSensitivity(
                Qt.CaseSensitivity.CaseSensitive
            )
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

    def _populate_comboboxes(self) -> None:
        for encoding in Encoding:
            self.comboBox_encoding.addItem(str(encoding), encoding)
        for newline in Newline:
            self.comboBox_line_endings.addItem(str(newline), newline)
        for container in AudioContainer:
            self.comboBox_audio_format.addItem(str(container), container)
        for codec in AudioCodec:
            self.comboBox_audio_conversion_format.addItem(str(codec), codec)
        for browser in Browser:
            self.comboBox_browser.addItem(QIcon(browser.icon()), str(browser), browser)
        for video_container in VideoContainer:
            self.comboBox_videocontainer.addItem(str(video_container), video_container)
        for video_codec in VideoCodec:
            self.comboBox_videoencoder.addItem(str(video_codec), video_codec)
        for resolution in VideoResolution:
            self.comboBox_videoresolution.addItem(str(resolution), resolution)
        for fps in VideoFps:
            self.comboBox_fps.addItem(str(fps), fps)

    def refresh(self, force_reload: bool) -> int:
        # TODO: remove all existing items in the model!
        available_songs = get_available_songs(force_reload)
        artists = set()
        titles = []
        languages = set()
        editions = set()
        self.model.removeRows(0, self.model.rowCount())

        root = self.model.invisibleRootItem()
        for song in available_songs:
            id_item = QStandardItem()
            id_item.setData(str(song.song_id), cast(int, Qt.ItemDataRole.DisplayRole))
            id_item.setCheckable(True)
            artist_item = QStandardItem()
            artist_item.setData(song.artist, cast(int, Qt.ItemDataRole.DisplayRole))
            title_item = QStandardItem()
            title_item.setData(song.title, cast(int, Qt.ItemDataRole.DisplayRole))
            language_item = QStandardItem()
            language_item.setData(song.language, cast(int, Qt.ItemDataRole.DisplayRole))
            edition_item = QStandardItem()
            edition_item.setData(song.edition, cast(int, Qt.ItemDataRole.DisplayRole))
            goldennotes_item = QStandardItem()
            goldennotes_item.setData(
                "Yes" if song.golden_notes else "No",
                cast(int, Qt.ItemDataRole.DisplayRole),
            )
            rating_item = QStandardItem()
            rating_item.setData(
                song.rating_str(), cast(int, Qt.ItemDataRole.DisplayRole)
            )
            views_item = QStandardItem()
            views_item.setData(int(song.views), cast(int, Qt.ItemDataRole.DisplayRole))
            row = [
                id_item,
                artist_item,
                title_item,
                language_item,
                edition_item,
                goldennotes_item,
                rating_item,
                views_item,
            ]
            root.appendRow(row)

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

        return len(available_songs)

    def select_song_dir(self) -> None:
        song_dir = str(QFileDialog.getExistingDirectory(self, "Select Song Directory"))
        self.lineEdit_song_dir.setText(song_dir)
        for _path, dirs, files in os.walk(song_dir):
            dirs.sort()
            for file in files:
                if file.endswith(".usdb"):
                    idp = file.replace(".usdb", "")
                    items = self.model.findItems(
                        idp, flags=Qt.MatchFlag.MatchExactly, column=0
                    )
                    if items:
                        item = items[0]
                        item.setCheckState(Qt.CheckState.Checked)

                        if idp:
                            for file in files:
                                if file.endswith(".txt"):
                                    self.model.setItem(
                                        item.row(),
                                        8,
                                        QStandardItem(QIcon(":/icons/tick.png"), ""),
                                    )

                                if (
                                    file.endswith(".mp3")
                                    or file.endswith(".ogg")
                                    or file.endswith("m4a")
                                    or file.endswith("opus")
                                    or file.endswith("ogg")
                                ):
                                    self.model.setItem(
                                        item.row(),
                                        9,
                                        QStandardItem(QIcon(":/icons/tick.png"), ""),
                                    )

                                if file.endswith(".mp4") or file.endswith(".webm"):
                                    self.model.setItem(
                                        item.row(),
                                        10,
                                        QStandardItem(QIcon(":/icons/tick.png"), ""),
                                    )

                                if file.endswith("[CO].jpg"):
                                    self.model.setItem(
                                        item.row(),
                                        11,
                                        QStandardItem(QIcon(":/icons/tick.png"), ""),
                                    )

                                if file.endswith("[BG].jpg"):
                                    self.model.setItem(
                                        item.row(),
                                        12,
                                        QStandardItem(QIcon(":/icons/tick.png"), ""),
                                    )

    def download_selected_songs(self) -> None:
        ids: list[SongId] = []
        for row in range(
            self.model.rowCount(self.tableView_availableSongs.rootIndex())
        ):
            item = self.model.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                ids.append(SongId(item.data(0)))
            else:
                pass
                # self.treeView_availableSongs.setRowHidden(row, QModelIndex(), True)
        self.download_songs(ids)
        self.generate_songlist_pdf()

    def generate_songlist_pdf(self) -> None:
        ### generate song list PDF
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

        for row in range(
            self.model.rowCount(self.tableView_availableSongs.rootIndex())
        ):
            item = self.model.item(row, 0)
            if item.checkState() == Qt.CheckState.Checked:
                song_id = str(int(item.text()))
                artist = self.model.item(row, 1).text()
                title = self.model.item(row, 2).text()
                language = self.model.item(row, 3).text()
                _edition = self.model.item(row, 4).text()
                content1.append(
                    [
                        f"{song_id}\t\t{artist}\t\t{title}\t\t{language}".replace(
                            "’", "'"
                        )
                    ]
                )

        with open(f"{date:%Y-%m-%d}_songlist.pdf", "wb") as file:
            build_pdf(document, file)
        ####

    def _download_options(self) -> Options:
        return Options(
            song_dir=self.lineEdit_song_dir.text(),
            txt_options=self._txt_options(),
            audio_options=self._audio_options(),
            browser=self.comboBox_browser.currentData(),
            video_options=self._video_options(),
            cover=self.groupBox_cover.isChecked(),
            background_options=self._background_options(),
        )

    def _txt_options(self) -> TxtOptions | None:
        if not self.groupBox_songfile.isChecked():
            return None
        return TxtOptions(
            encoding=self.comboBox_encoding.currentData(),
            newline=self.comboBox_line_endings.currentData(),
        )

    def _audio_options(self) -> AudioOptions | None:
        if not self.groupBox_audio.isChecked():
            return None
        return AudioOptions(
            format=self.comboBox_audio_format.currentData(),
            reencode_format=self.comboBox_audio_conversion_format.currentData()
            if self.groupBox_reencode_audio.isChecked()
            else None,
        )

    def _video_options(self) -> VideoOptions | None:
        if not self.groupBox_video.isChecked():
            return None
        return VideoOptions(
            format=self.comboBox_videocontainer.currentData(),
            reencode_format=self.comboBox_videoencoder.currentData()
            if self.groupBox_reencode_video.isChecked()
            else None,
            max_resolution=self.comboBox_videoresolution.currentData(),
            max_fps=self.comboBox_fps.currentData(),
        )

    def _background_options(self) -> BackgroundOptions | None:
        if not self.groupBox_background.isChecked():
            return None
        return BackgroundOptions(
            only_if_no_video=self.comboBox_background.currentText()
            == "only if no video"
        )

    def download_songs(self, ids: list[SongId]) -> None:
        options = self._download_options()
        for song_id in ids:
            worker = SongLoader(song_id=song_id, options=options)
            self.threadpool.start(worker)

        logging.info(f"DONE! (Downloaded {len(ids)} songs)")

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if (
            isinstance(event, QContextMenuEvent)
            and source == self.tableView_availableSongs
        ):
            menu = QMenu()
            menu.addAction("Check all selected songs")
            menu.addAction("Uncheck all selected songs")

            if menu.exec(event.globalPos()):
                index = self.tableView_availableSongs.indexAt(event.pos())
                print(index)
            return True
        return super().eventFilter(source, event)


def get_available_songs(force_reload: bool) -> list[SongMeta]:
    if force_reload or not (available_songs := load_available_songs()):
        available_songs = usdb_scraper.get_usdb_available_songs()
        dump_available_songs(available_songs)
    return available_songs


def load_available_songs() -> list[SongMeta] | None:
    path = available_songs_path()
    if not has_recent_mtime(path) or not os.path.exists(path):
        return None
    with open(path, encoding="utf8") as file:
        try:
            return json.load(file, object_hook=lambda d: SongMeta(**d))
        except (json.decoder.JSONDecodeError, TypeError):
            return None


def dump_available_songs(available_songs: list[SongMeta]) -> None:
    os.makedirs(os.path.dirname(available_songs_path()), exist_ok=True)
    with open(available_songs_path(), "w", encoding="utf8") as file:
        json.dump(available_songs, file, cls=usdb_scraper.SongMetaEncoder)


def available_songs_path() -> str:
    return os.path.join(
        appdirs.user_cache_dir("usdb_dl", "bohning"), "available_songs.json"
    )


def has_recent_mtime(path: str, recent_secs: int = 60 * 60 * 24) -> bool:
    """True if the given path exists and its mtime is less than recent_secs in the past."""
    return os.path.exists(path) and time.time() - os.path.getmtime(path) < recent_secs


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
    num_songs = mw.refresh(False)
    splash.showMessage(
        f"Song database successfully loaded with {num_songs} songs.",
        color=Qt.GlobalColor.gray,
    )
    mw.show()
    logging.info("Application successfully loaded.")
    splash.finish(mw)
    app.exec()
