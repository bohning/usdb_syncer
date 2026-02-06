"""Table model for song data."""

from collections.abc import Iterable
from typing import Any, assert_never

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)
from PySide6.QtGui import QFont, QIcon

from usdb_syncer import SongId, events
from usdb_syncer.db import JobStatus
from usdb_syncer.gui.fonts import get_rating_font
from usdb_syncer.gui.song_table.column import Column, ColumnBase
from usdb_syncer.sync_meta import Resource
from usdb_syncer.usdb_song import UsdbSong

QIndex = QModelIndex | QPersistentModelIndex


class TableModel(QAbstractTableModel):
    """Table model for song data."""

    _ids: tuple[SongId, ...] = ()
    _rows: dict[SongId, int]

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._rows = {}
        events.SongChanged.subscribe(self._on_song_changed)
        events.SongDeleted.subscribe(self._on_song_deleted)
        events.SongDirChanged.subscribe(lambda _: self.reset)

    def reset(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def set_songs(self, songs: Iterable[SongId]) -> None:
        self.beginResetModel()
        self._ids = tuple(songs)
        self._rows = {song: row for row, song in enumerate(self._ids)}
        self.endResetModel()

    def ids_for_indices(self, indices: Iterable[QModelIndex]) -> list[SongId]:
        return [self._ids[idx.row()] for idx in indices]

    def ids_for_rows(self, rows: Iterable[int]) -> list[SongId]:
        return [self._ids[row] for row in rows]

    def indices_for_ids(self, ids: Iterable[SongId]) -> list[QModelIndex]:
        return [
            self.index(row, 0)
            for song_id in ids
            if (row := self._rows.get(song_id)) is not None
        ]

    def row_for_id(self, song_id: SongId) -> int | None:
        return self._rows.get(song_id)

    def _row_changed(self, row: int) -> None:
        start_idx = self.index(row, 0)
        end_idx = self.index(row, self.columnCount() - 1)
        self.dataChanged.emit(start_idx, end_idx)

    def _on_song_changed(self, event: events.SongChanged) -> None:
        if (row := self._rows.get(event.song_id)) is not None:
            self._row_changed(row)

    def _on_song_deleted(self, event: events.SongDeleted) -> None:
        if (row := self._rows.get(event.song_id)) is None:
            return
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._rows[event.song_id]
        self._ids = self._ids[:row] + self._ids[row + 1 :]
        self.endRemoveRows()

    # QAbstractTableModel implementation

    def columnCount(self, parent: QIndex | None = None) -> int:  # noqa: N802
        if parent is None:
            parent = QModelIndex()
        return 0 if parent.isValid() else Column.len()

    def rowCount(self, parent: QIndex | None = None) -> int:  # noqa: N802
        if parent is None:
            parent = QModelIndex()
        return 0 if parent.isValid() else len(self._ids)

    def data(self, index: QIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        song = self._get_song(index)
        if not song:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return _display_data(song, index.column())
        if role == Qt.ItemDataRole.DecorationRole:
            return _decoration_data(song, index.column())
        if role == Qt.ItemDataRole.ToolTipRole:
            return _tooltip_data(song, index.column())
        if role == Qt.ItemDataRole.FontRole:
            return _font_data(index.column())
        return None

    def _get_song(self, index: QIndex) -> UsdbSong | None:
        if not index.isValid():
            return None
        song_id = self._ids[index.row()]
        if song := UsdbSong.get(song_id):
            return song
        return None

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role == Qt.ItemDataRole.DecorationRole:
            return ColumnBase.from_index(section).decoration_data()
        if role == Qt.ItemDataRole.DisplayRole:
            return ColumnBase.from_index(section).display_data()
        return None


def _display_data(song: UsdbSong, column: int) -> str | None:
    return ColumnBase.from_index(column).cell_display_data(song)


def _decoration_data(song: UsdbSong, column: int) -> QIcon | None:
    return ColumnBase.from_index(column).cell_decoration_data(song)


def _font_data(column: int) -> QFont | None:
    if ColumnBase.from_index(column) == Column.RATING:
        return get_rating_font()
    return None


def _tooltip_data(song: UsdbSong, column: int) -> str | None:
    if not (sync_meta := song.sync_meta):
        return None

    col = Column.from_index(column)
    if resource := col.get_resource_for_column(sync_meta):
        return status_tooltip(resource)

    return None


def status_tooltip(resource: Resource) -> str:
    file = resource.file
    match resource.status:
        case JobStatus.SUCCESS | JobStatus.SUCCESS_UNCHANGED:
            tooltip = file.fname if file else "local file missing"
        case JobStatus.SKIPPED_DISABLED:
            tooltip = "Resource download disabled in the settings"
        case JobStatus.SKIPPED_UNAVAILABLE:
            tooltip = "No resource available"
        case JobStatus.FALLBACK:
            tooltip = (
                (f"{file.fname} (fallback to commented/USDB resource)")
                if file
                else "local file missing"
            )
        case JobStatus.FAILURE_EXISTING:
            tooltip = (
                (f"{file.fname} (fallback to existing resource)")
                if file
                else "local file missing"
            )
        case JobStatus.FAILURE:
            tooltip = "Resource download failed"
        case _ as unreachable:
            assert_never(unreachable)
    return tooltip
