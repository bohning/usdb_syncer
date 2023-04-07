"""Proxy model for sorting and filtering data of a source model."""

from PySide6.QtCore import (
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    QTimer,
)
from usdb_syncer.gui.song_table.column import Column

from usdb_syncer.gui.song_table.table_model import CustomRole
from usdb_syncer.song_data import DownloadStatus, SongData, fuzz_text
from usdb_syncer.song_txt import SongTxt

QIndex = QModelIndex | QPersistentModelIndex


class QueueProxyModel(QSortFilterProxyModel):
    """Proxy model for sorting and filtering data of a source model."""

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)

    def filterAcceptsRow(self, source_row: int, source_parent: QIndex) -> bool:
        model = self.sourceModel()
        idx = model.index(source_row, 0, source_parent)
        song: SongData = model.data(idx, CustomRole.ALL_DATA)
        return song.status is not DownloadStatus.NONE

    def filterAcceptsColumn(self, source_column: int, _source_parent: QIndex) -> bool:
        return Column(source_column).display_in_queue_view()
