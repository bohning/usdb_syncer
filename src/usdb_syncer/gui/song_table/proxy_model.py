"""Proxy model for sorting and filtering data of a source model."""

from typing import Iterable, Iterator

from PySide6.QtCore import (
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    QTimer,
)

from usdb_syncer.gui.search_tree.tree import FilterTree
from usdb_syncer.gui.song_table.table_model import CustomRole
from usdb_syncer.song_data import SongData, fuzz_text

QIndex = QModelIndex | QPersistentModelIndex


class ProxyModel(QSortFilterProxyModel):
    """Proxy model for sorting and filtering data of a source model."""

    def __init__(self, parent: QObject, filter_tree: FilterTree) -> None:
        self._text_filter: list[str] = []
        self.filter_tree = filter_tree

        self._filter_invalidation_timer = QTimer(parent)
        self._filter_invalidation_timer.setSingleShot(True)
        self._filter_invalidation_timer.setInterval(600)
        self._filter_invalidation_timer.timeout.connect(self.invalidateRowsFilter)
        filter_tree.connect_filter_changed(self._filter_invalidation_timer.start)

        super().__init__(parent)

    def source_rows(self, subset: list[QModelIndex] | None = None) -> list[int]:
        """Returns the source rows of the provided or all rows in the model."""
        indices = subset or (self.index(row, 0) for row in range(self.rowCount()))
        return [row for idx in indices if (row := self.mapToSource(idx).row()) != -1]

    def target_indices(self, sources: Iterable[QModelIndex]) -> Iterator[QModelIndex]:
        return (self.mapFromSource(idx) for idx in sources)

    def set_text_filter(self, text: str) -> None:
        self._text_filter = fuzz_text(text).split()
        self._filter_invalidation_timer.start()

    def filterAcceptsRow(self, source_row: int, source_parent: QIndex) -> bool:
        model = self.sourceModel()
        idx = model.index(source_row, 0, source_parent)
        return self._filter_accepts_song(model.data(idx, CustomRole.ALL_DATA))

    def _filter_accepts_song(self, song: SongData) -> bool:
        return all(
            word in song.fuzzy_text for word in self._text_filter
        ) and self.filter_tree.accepts_song(song)
