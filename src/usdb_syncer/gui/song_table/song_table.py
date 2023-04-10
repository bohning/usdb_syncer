"""Controller for the song table."""


import logging
import os
from glob import glob
from typing import Any, Callable, Iterator

from PySide6.QtCore import QItemSelection, QItemSelectionModel, QModelIndex, QObject
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView

from usdb_syncer import SongId
from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.gui.song_table.sort_filter_proxy_model import SortFilterProxyModel
from usdb_syncer.gui.song_table.table_model import CustomRole, TableModel
from usdb_syncer.logger import get_logger
from usdb_syncer.song_data import SongData
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.usdb_scraper import UsdbSong
from usdb_syncer.utils import try_read_unknown_encoding

_logger = logging.getLogger(__file__)


class SongTable:
    """Controller for the song table."""

    def __init__(self, parent: QObject, view: QTableView) -> None:
        self._view = view
        self._model = TableModel(parent)
        self._proxy_model = SortFilterProxyModel(parent)
        self._proxy_model.setSourceModel(self._model)
        self._proxy_model.setSortRole(CustomRole.SORT)
        self._view.setModel(self._proxy_model)
        self._view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def initialize(self, song_list: tuple[SongData, ...]) -> None:
        self._model.set_data(song_list)
        self._setup_table_header()

    def _setup_table_header(self) -> None:
        header = self._view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(Column.SONG_ID, QHeaderView.ResizeMode.Fixed)

        font_metrics = header.fontMetrics()
        header.resizeSection(Column.SONG_ID, font_metrics.horizontalAdvance("12345678"))
        header.setSectionResizeMode(Column.ARTIST, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(Column.TITLE, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(Column.LANGUAGE, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(Column.EDITION, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(Column.GOLDEN_NOTES, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(
            Column.GOLDEN_NOTES, header.sectionSize(Column.GOLDEN_NOTES)
        )
        header.setSectionResizeMode(Column.RATING, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(Column.RATING, header.sectionSize(Column.RATING))
        header.setSectionResizeMode(Column.VIEWS, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(Column.VIEWS, header.sectionSize(Column.VIEWS))
        header.setSectionResizeMode(Column.TXT, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(Column.TXT, 24)
        header.setSectionResizeMode(Column.AUDIO, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(Column.AUDIO, 24)
        header.setSectionResizeMode(Column.VIDEO, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(Column.VIDEO, 24)
        header.setSectionResizeMode(Column.COVER, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(Column.COVER, 24)
        header.setSectionResizeMode(Column.BACKGROUND, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(Column.BACKGROUND, 24)

    ### selection model

    def connect_selected_rows_changed(self, func: Callable[[int], None]) -> None:
        """Calls `func` with the new count of selected rows. The new count is not
        necessarily different.
        """
        model = self._view.selectionModel()
        model.selectionChanged.connect(  # type:ignore
            lambda *_: func(len(model.selectedRows()))
        )

    def selected_row_count(self) -> int:
        return len(self._view.selectionModel().selectedRows())

    def selected_song_ids(self) -> list[SongId]:
        selected_rows = self._view.selectionModel().selectedRows()
        source_rows = map(self._proxy_model.mapToSource, selected_rows)
        return self._model.ids_for_indices(source_rows)

    def select_local_songs(self, directory: str) -> None:
        txts = _parse_all_txts(directory)
        rows = self._proxy_model.find_rows_for_song_txts(txts)
        for idx, song_rows in enumerate(rows):
            if not song_rows:
                name = txts[idx].headers.artist_title_str()
                _logger.warning(f"no matches for '{name}'")
            if len(song_rows) > 1:
                name = txts[idx].headers.artist_title_str()
                _logger.info(f"{len(song_rows)} matches for '{name}'")
        self.set_selection_to_rows(idx for row_list in rows for idx in row_list)

    def set_selection_to_song_ids(self, select_song_ids: list[SongId]) -> None:
        all_indices = [
            self._model.index(row, 0) for row in range(self._model.rowCount())
        ]
        all_song_ids = self._model.ids_for_indices(all_indices)
        select_indices = [
            all_indices[i]
            for i in range(len(all_indices))
            if all_song_ids[i] in select_song_ids
        ]
        self.set_selection_to_rows(iter(select_indices))

    def set_selection_to_rows(self, rows: Iterator[QModelIndex]) -> None:
        selection = QItemSelection()
        for row in rows:
            selection.select(row, row)
        self._view.selectionModel().select(
            selection,
            QItemSelectionModel.SelectionFlag.Rows
            | QItemSelectionModel.SelectionFlag.ClearAndSelect,
        )

    ### sort and filter model

    def connect_row_count_changed(self, func: Callable[[int], None]) -> None:
        """Calls `func` with the new row count."""

        def wrapped(*_: Any) -> None:
            func(self._proxy_model.rowCount())

        self._proxy_model.rowsInserted.connect(wrapped)  # type:ignore
        self._proxy_model.rowsRemoved.connect(wrapped)  # type:ignore

    def row_count(self) -> int:
        return self._proxy_model.rowCount()

    def set_text_filter(self, text: str) -> None:
        self._proxy_model.set_text_filter(text)

    def set_artist_filter(self, artist: str) -> None:
        self._proxy_model.set_artist_filter(artist)

    def set_title_filter(self, title: str) -> None:
        self._proxy_model.set_title_filter(title)

    def set_language_filter(self, language: str) -> None:
        self._proxy_model.set_language_filter(language)

    def set_edition_filter(self, edition: str) -> None:
        self._proxy_model.set_edition_filter(edition)

    def set_golden_notes_filter(self, golden_notes: bool | None) -> None:
        self._proxy_model.set_golden_notes_filter(golden_notes)

    def set_rating_filter(self, rating: int, exact: bool) -> None:
        self._proxy_model.set_rating_filter(rating, exact)

    def set_views_filter(self, min_views: int) -> None:
        self._proxy_model.set_views_filter(min_views)

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
