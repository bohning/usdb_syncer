"""Proxy model for sorting and filtering data of a source model."""

from typing import Iterable

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QSortFilterProxyModel

from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.gui.song_table.table_model import CustomRole
from usdb_syncer.song_data import DownloadStatus, SongData

QIndex = QModelIndex | QPersistentModelIndex


class QueueProxyModel(QSortFilterProxyModel):
    """Proxy model for sorting and filtering data of a source model."""

    def source_rows(self, subset: list[QModelIndex] | None = None) -> Iterable[int]:
        """Returns the source rows of the provided or all rows in the model."""
        indices = subset or (self.index(row, 0) for row in range(self.rowCount()))
        return (self.mapToSource(idx).row() for idx in indices)

    ### QSortFilterProxyModel implementation

    def filterAcceptsRow(self, source_row: int, source_parent: QIndex) -> bool:
        model = self.sourceModel()
        idx = model.index(source_row, 0, source_parent)
        song: SongData = model.data(idx, CustomRole.ALL_DATA)
        return song.status is not DownloadStatus.NONE

    def filterAcceptsColumn(self, source_column: int, _source_parent: QIndex) -> bool:
        return Column(source_column).display_in_queue_view()
