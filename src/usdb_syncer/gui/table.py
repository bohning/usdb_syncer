"""Controller for the song table."""

from typing import Any, Callable, Iterator

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView

from usdb_syncer import SongId
from usdb_syncer.gui.sort_filter_proxy_model import SortFilterProxyModel
from usdb_syncer.gui.table_model import TableModel
from usdb_syncer.song_list_fetcher import SyncedSongMeta
from usdb_syncer.usdb_scraper import SongMeta


class SongTable:
    """Controller for the song table."""

    def __init__(self, parent: QObject, view: QTableView) -> None:
        self._view = view
        self._model = TableModel(parent)
        self._proxy_model = SortFilterProxyModel(parent)
        self._proxy_model.setSourceModel(self._model)
        self._view.setModel(self._proxy_model)
        self._view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def initialize(self, song_list: list[SyncedSongMeta]) -> None:
        self._model.set_data(song_list)
        self._setup_table_header()

    def _setup_table_header(self) -> None:
        header = self._view.horizontalHeader()
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

    def selected_song_ids(self) -> list[SongId]:
        selected_rows = self._view.selectionModel().selectedRows()
        source_rows = map(self._proxy_model.mapToSource, selected_rows)
        return self._model.ids_for_indices(source_rows)

    def all_local_songs(self) -> Iterator[SongMeta]:
        return self._model.all_local_songs()

    def resync_data(self, song_dir: str) -> None:
        self._model.resync_data(song_dir)

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

    def set_data(self, songs: list[SyncedSongMeta]) -> None:
        self._model.set_data(songs)
