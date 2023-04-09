"""Controller for the song table."""


import logging
import os
from glob import glob
from typing import Any, Callable, Iterable, Iterator

from PySide6.QtCore import (
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QHeaderView, QMenu, QTableView, QWidget

from usdb_syncer import SongId
from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.gui.song_table.list_proxy_model import ListProxyModel
from usdb_syncer.gui.song_table.queue_proxy_model import QueueProxyModel
from usdb_syncer.gui.song_table.table_model import CustomRole, TableModel
from usdb_syncer.logger import get_logger
from usdb_syncer.song_data import DownloadStatus, LocalFiles, SongData
from usdb_syncer.song_loader import DownloadInfo, download_songs
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.usdb_scraper import UsdbSong
from usdb_syncer.utils import try_read_unknown_encoding

_logger = logging.getLogger(__file__)


class SongSignals(QObject):
    """Signals relating to songs."""

    started = Signal(SongId)
    finished = Signal(SongId, LocalFiles)


class SongTable:
    """Controller for the song table."""

    def __init__(
        self,
        parent: QWidget,
        list_view: QTableView,
        queue_view: QTableView,
        list_menu: QMenu,
        queue_menu: QMenu,
    ) -> None:
        self._parent = parent
        self._list_view = list_view
        self._queue_view = queue_view
        self._model = TableModel(parent)
        self._list_proxy = ListProxyModel(parent)
        self._queue_proxy = QueueProxyModel(parent)
        self._setup_view(self._list_view, self._list_proxy)
        self._setup_view(self._queue_view, self._queue_proxy)
        self._list_view.customContextMenuRequested.connect(
            lambda _: self._context_menu(list_menu)
        )
        self._queue_view.customContextMenuRequested.connect(
            lambda _: self._context_menu(queue_menu)
        )
        self._signals = SongSignals()
        self._signals.started.connect(self._on_download_started)
        self._signals.finished.connect(self._on_download_finished)

    def initialize(self, song_list: tuple[SongData, ...]) -> None:
        self._model.set_data(song_list)
        self._setup_list_table_header()
        self._setup_queue_table_header()

    def download_selection(self) -> None:
        self._download(self._list_rows(selected_only=True))

    def download_batch(self) -> None:
        self._download(self._queue_rows())

    def _download(self, rows: Iterable[int]) -> None:
        to_download = []

        def process(data: SongData) -> bool:
            if data.status.can_be_downloaded():
                data.status = DownloadStatus.PENDING
                to_download.append(data)
                return True
            return False

        self._process_rows(rows, process)
        if to_download:
            download_songs(
                map(DownloadInfo.from_song_data, to_download),
                self._signals.started.emit,
                self._signals.finished.emit,
            )

    def _process_rows(
        self, rows: Iterable[int], processor: Callable[[SongData], bool]
    ) -> None:
        invalidate = False
        for row in rows:
            data = self._model.songs[row]
            if processor(data):
                invalidate = True
                self._model.row_changed(row)
        if invalidate:
            self._queue_proxy.invalidateRowsFilter()

    def stage_selection(self) -> None:
        def process(data: SongData) -> bool:
            if data.status is DownloadStatus.NONE:
                data.status = DownloadStatus.STAGED
                return True
            return False

        self._process_rows(self._list_rows(selected_only=True), process)

    def unstage_selection(self) -> None:
        def process(data: SongData) -> bool:
            if data.status.can_be_unstaged():
                data.status = DownloadStatus.NONE
                return True
            return False

        self._process_rows(self._queue_rows(selected_only=True), process)

    def clear_batch(self) -> None:
        data_rows = [
            (row, data)
            for row in self._queue_proxy.source_rows()
            if (data := self._model.songs[row]).status.can_be_unstaged()
        ]
        if not data_rows:
            return
        for row, data in data_rows:
            data.status = DownloadStatus.NONE
            self._model.row_changed(row)
        self._queue_proxy.invalidateRowsFilter()

    def _setup_view(self, view: QTableView, model: QSortFilterProxyModel) -> None:
        model.setSourceModel(self._model)
        model.setSortRole(CustomRole.SORT)
        view.setModel(model)
        header = view.horizontalHeader()
        # for resizable columns, use content size as the start value
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def _context_menu(self, base_menu: QMenu) -> None:
        menu = QMenu()
        for action in base_menu.actions():
            menu.addAction(action)
        menu.exec(QCursor.pos())

    def _on_download_started(self, song_id: SongId) -> None:
        if not (row := self._model.rows.get(song_id)):
            return
        data = self._model.songs[row]
        data.status = DownloadStatus.DOWNLOADING
        self._model.row_changed(row)

    def _on_download_finished(self, song_id: SongId, files: LocalFiles) -> None:
        if not (row := self._model.rows.get(song_id)):
            return
        data = self._model.songs[row]
        data.status = DownloadStatus.DONE
        data.local_files = files
        self._model.row_changed(row)

    ### song list view

    def _setup_list_table_header(self) -> None:
        header = self._list_view.horizontalHeader()
        for column in Column:
            size = column.section_size(header, self._parent) or header.sectionSize(
                column
            )
            header.setSectionResizeMode(column, column.section_resize_mode())
            header.resizeSection(column, size)

    ### download queue view

    def _setup_queue_table_header(self) -> None:
        header = self._queue_view.horizontalHeader()
        list_header = self._list_view.horizontalHeader()
        for col in Column:
            if col.display_in_queue_view():
                header.setSectionResizeMode(col, list_header.sectionResizeMode(col))
                header.resizeSection(col, list_header.sectionSize(col))

    ### selection model

    def connect_selected_rows_changed(self, func: Callable[[int], None]) -> None:
        """Calls `func` with the new count of selected rows. The new count is not
        necessarily different.
        """
        model = self._list_view.selectionModel()
        model.selectionChanged.connect(  # type:ignore
            lambda *_: func(len(model.selectedRows()))
        )

    def selected_row_count(self) -> int:
        return len(self._list_view.selectionModel().selectedRows())

    def _list_rows(self, selected_only: bool = False) -> Iterable[int]:
        return self._list_proxy.source_rows(
            self._list_view.selectionModel().selectedRows() if selected_only else None
        )

    def _queue_rows(self, selected_only: bool = False) -> Iterable[int]:
        return self._queue_proxy.source_rows(
            self._queue_view.selectionModel().selectedRows() if selected_only else None
        )

    def select_local_songs(self, directory: str) -> None:
        txts = _parse_all_txts(directory)
        rows = self._list_proxy.find_rows_for_song_txts(txts)
        for idx, song_rows in enumerate(rows):
            if not song_rows:
                name = txts[idx].headers.artist_title_str()
                _logger.warning(f"no matches for '{name}'")
            if len(song_rows) > 1:
                name = txts[idx].headers.artist_title_str()
                _logger.info(f"{len(song_rows)} matches for '{name}'")
        self.set_selection_to_rows(idx for row_list in rows for idx in row_list)

    def set_selection_to_rows(self, rows: Iterator[QModelIndex]) -> None:
        selection = QItemSelection()
        for row in rows:
            selection.select(row, row)
        self._list_view.selectionModel().select(
            selection,
            QItemSelectionModel.SelectionFlag.Rows
            | QItemSelectionModel.SelectionFlag.ClearAndSelect,
        )

    ### sort and filter model

    def connect_row_count_changed(self, func: Callable[[int], None]) -> None:
        """Calls `func` with the new row count."""

        def wrapped(*_: Any) -> None:
            func(self._list_proxy.rowCount())

        self._list_proxy.rowsInserted.connect(wrapped)  # type:ignore
        self._list_proxy.rowsRemoved.connect(wrapped)  # type:ignore

    def row_count(self) -> int:
        return self._list_proxy.rowCount()

    def set_text_filter(self, text: str) -> None:
        self._list_proxy.set_text_filter(text)

    def set_artist_filter(self, artist: str) -> None:
        self._list_proxy.set_artist_filter(artist)

    def set_title_filter(self, title: str) -> None:
        self._list_proxy.set_title_filter(title)

    def set_language_filter(self, language: str) -> None:
        self._list_proxy.set_language_filter(language)

    def set_edition_filter(self, edition: str) -> None:
        self._list_proxy.set_edition_filter(edition)

    def set_golden_notes_filter(self, golden_notes: bool | None) -> None:
        self._list_proxy.set_golden_notes_filter(golden_notes)

    def set_rating_filter(self, rating: int, exact: bool) -> None:
        self._list_proxy.set_rating_filter(rating, exact)

    def set_views_filter(self, min_views: int) -> None:
        self._list_proxy.set_views_filter(min_views)

    ### data model

    def set_data(self, songs: tuple[SongData, ...]) -> None:
        self._model.set_data(songs)

    def get_all_data(self) -> tuple[SongData, ...]:
        return self._model.songs

    def all_local_songs(self) -> Iterator[UsdbSong]:
        return self._model.all_local_songs()

    def get_data(self, song_id: SongId) -> SongData | None:
        return self._model.item_for_id(song_id)

    def update_item(self, new: SongData) -> None:
        self._model.update_item(new)


def _parse_all_txts(directory: str) -> list[SongTxt]:
    err_logger = get_logger(__file__ + "[errors]")
    err_logger.setLevel(logging.ERROR)
    txts: list[SongTxt] = []
    for path in glob(os.path.join(directory, "**", "*.txt"), recursive=True):
        contents = try_read_unknown_encoding(path)
        if contents and (txt := SongTxt.try_parse(contents, err_logger)):
            txts.append(txt)
    return txts
