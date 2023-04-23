"""Controller for the song table."""


import logging
import os
from glob import glob
from typing import Any, Callable, Iterable, Iterator

import attrs
from PySide6.QtCore import (
    QByteArray,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QMenu,
    QProgressBar,
    QTableView,
    QWidget,
)

from usdb_syncer import SongId, settings
from usdb_syncer.gui.song_table.batch_model import BatchModel
from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.gui.song_table.list_model import ListModel
from usdb_syncer.gui.song_table.table_model import CustomRole, TableModel
from usdb_syncer.logger import get_logger
from usdb_syncer.song_data import DownloadResult, DownloadStatus, SongData
from usdb_syncer.song_loader import DownloadInfo, download_songs
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.usdb_scraper import UsdbSong
from usdb_syncer.utils import try_read_unknown_encoding

_logger = logging.getLogger(__file__)
DEFAULT_COLUMN_WIDTH = 300


class SongSignals(QObject):
    """Signals relating to songs."""

    started = Signal(SongId)
    finished = Signal(DownloadResult)


@attrs.define
class Progress:
    """Progress bar controller."""

    _bar: QProgressBar
    _label: QLabel
    _running: int = 0
    _finished: int = 0

    def start(self, count: int) -> None:
        if self._running == self._finished:
            self._running = 0
            self._finished = 0
        self._running += count
        self._update()

    def finish(self, count: int) -> None:
        self._finished += count
        self._update()

    def _update(self) -> None:
        self._label.setText(f"{self._finished}/{self._running}")
        self._bar.setValue(int((self._finished + 1) / (self._running + 1) * 100))


class SongTable:
    """Controller for the song table."""

    def __init__(
        self,
        parent: QWidget,
        list_view: QTableView,
        batch_view: QTableView,
        list_menu: QMenu,
        batch_menu: QMenu,
        progress_bar: QProgressBar,
        progress_label: QLabel,
    ) -> None:
        self._parent = parent
        self._list_view = list_view
        self._batch_view = batch_view
        self._model = TableModel(parent)
        self._list_model = ListModel(parent)
        self._batch_model = BatchModel(parent)
        self._setup_view(
            self._list_view,
            self._list_model,
            list_menu,
            settings.get_list_view_header_state(),
        )
        self._setup_view(
            self._batch_view,
            self._batch_model,
            batch_menu,
            settings.get_batch_view_header_state(),
        )
        self._signals = SongSignals()
        self._signals.started.connect(self._on_download_started)
        self._signals.finished.connect(self._on_download_finished)
        self._progress = Progress(progress_bar, progress_label)

    def initialize(self, song_list: tuple[SongData, ...]) -> None:
        self._model.set_data(song_list)

    def download_selection(self) -> None:
        self._download(self._list_rows(selected_only=True))

    def download_batch(self) -> None:
        self._download(self._batch_rows())

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
            self._progress.start(len(to_download))
            download_songs(
                map(DownloadInfo.from_song_data, to_download),
                self._signals.started.emit,
                self._signals.finished.emit,
            )

    def _process_rows(
        self, rows: Iterable[int], processor: Callable[[SongData], bool]
    ) -> None:
        for row in rows:
            data = self._model.songs[row]
            if processor(data):
                self._model.row_changed(row)

    def stage_selection(self) -> None:
        self._stage_rows(self._list_rows(selected_only=True))

    def _stage_rows(self, rows: Iterable[int]) -> None:
        def process(data: SongData) -> bool:
            if data.status is DownloadStatus.NONE:
                data.status = DownloadStatus.STAGED
                return True
            return False

        self._process_rows(rows, process)

    def unstage_selection(self) -> None:
        def process(data: SongData) -> bool:
            if data.status.can_be_unstaged():
                data.status = DownloadStatus.NONE
                return True
            return False

        self._process_rows(self._batch_rows(selected_only=True), process)

    def clear_batch(self) -> None:
        def process(data: SongData) -> bool:
            if data.status.can_be_unstaged():
                data.status = DownloadStatus.NONE
                return True
            return False

        self._process_rows(self._batch_rows(), process)

    def _setup_view(
        self,
        view: QTableView,
        model: QSortFilterProxyModel,
        menu: QMenu,
        state: QByteArray,
    ) -> None:
        model.setSourceModel(self._model)
        model.setSortRole(CustomRole.SORT)
        view.setModel(model)
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        view.customContextMenuRequested.connect(lambda _: self._context_menu(menu))  # type: ignore
        view.doubleClicked.connect(lambda idx: self._on_double_clicked(idx, model))  # type: ignore
        header = view.horizontalHeader()
        if not state.isEmpty():
            header.restoreState(state)
            return
        for column in Column:
            if not model.filterAcceptsColumn(column, QModelIndex()):
                continue
            if size := column.fixed_size(header, self._parent):
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
                header.resizeSection(column, size)
            # setting a (default) width on the last, stretching column seems to cause
            # issues, so we set it manually on the other columns
            elif column is not max(Column):
                header.resizeSection(column, DEFAULT_COLUMN_WIDTH)
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)

    def _context_menu(self, base_menu: QMenu) -> None:
        menu = QMenu()
        for action in base_menu.actions():
            menu.addAction(action)
        menu.exec(QCursor.pos())

    def _on_double_clicked(
        self, index: QModelIndex, model: QSortFilterProxyModel
    ) -> None:
        row = model.mapToSource(index).row()
        data = self._model.songs[row]
        if model is self._batch_model and data.status.can_be_unstaged():
            data.status = DownloadStatus.NONE
        elif model is self._list_model and data.status is DownloadStatus.NONE:
            data.status = DownloadStatus.STAGED
        else:
            return
        self._model.row_changed(row)

    def _on_download_started(self, song_id: SongId) -> None:
        if not (row := self._model.rows.get(song_id)):
            return
        data = self._model.songs[row]
        data.status = DownloadStatus.DOWNLOADING
        self._model.row_changed(row)

    def _on_download_finished(self, result: DownloadResult) -> None:
        if not (row := self._model.rows.get(result.song_id)):
            return
        data = self._model.songs[row]
        if result.files:
            data.status = DownloadStatus.DONE
            data.local_files = result.files
        else:
            data.status = DownloadStatus.FAILED
        self._model.row_changed(row)
        self._progress.finish(1)

    def save_state(self) -> None:
        settings.set_list_view_header_state(
            self._list_view.horizontalHeader().saveState()
        )
        settings.set_batch_view_header_state(
            self._batch_view.horizontalHeader().saveState()
        )

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
        return self._list_model.source_rows(
            self._list_view.selectionModel().selectedRows() if selected_only else None
        )

    def _batch_rows(self, selected_only: bool = False) -> Iterable[int]:
        return self._batch_model.source_rows(
            self._batch_view.selectionModel().selectedRows() if selected_only else None
        )

    def stage_local_songs(self, directory: str) -> None:
        txts = _parse_all_txts(directory)
        matches = self._list_model.find_rows_for_song_txts(txts)
        for idx, song_rows in enumerate(matches):
            if not song_rows:
                name = txts[idx].headers.artist_title_str()
                _logger.warning(f"no matches for '{name}'")
            if len(song_rows) > 1:
                name = txts[idx].headers.artist_title_str()
                _logger.info(f"{len(song_rows)} matches for '{name}'")
        rows = [idx.row() for row_list in matches for idx in row_list]
        self._stage_rows(rows)
        _logger.info(f"Added {len(rows)} songs to batch.")

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

    def connect_row_count_changed(self, func: Callable[[int, int], None]) -> None:
        """Calls `func` with the new list and batch row counts."""

        def wrapped(*_: Any) -> None:
            func(self._list_model.rowCount(), self._batch_model.rowCount())

        self._model.modelReset.connect(wrapped)  # type:ignore
        for model in (self._list_model, self._batch_model):
            model.rowsInserted.connect(wrapped)  # type:ignore
            model.rowsRemoved.connect(wrapped)  # type:ignore

    def set_text_filter(self, text: str) -> None:
        self._list_model.set_text_filter(text)

    def set_artist_filter(self, artist: str) -> None:
        self._list_model.set_artist_filter(artist)

    def set_title_filter(self, title: str) -> None:
        self._list_model.set_title_filter(title)

    def set_language_filter(self, language: str) -> None:
        self._list_model.set_language_filter(language)

    def set_edition_filter(self, edition: str) -> None:
        self._list_model.set_edition_filter(edition)

    def set_golden_notes_filter(self, golden_notes: bool | None) -> None:
        self._list_model.set_golden_notes_filter(golden_notes)

    def set_rating_filter(self, rating: int, exact: bool) -> None:
        self._list_model.set_rating_filter(rating, exact)

    def set_views_filter(self, min_views: int) -> None:
        self._list_model.set_views_filter(min_views)

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
