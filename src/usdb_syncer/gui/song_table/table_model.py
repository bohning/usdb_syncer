"""Table model for song data."""

from functools import cache
from typing import Any, Iterable, assert_never

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)
from PySide6.QtGui import QIcon

from usdb_syncer import SongId, events
from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.usdb_song import UsdbSong

QIndex = QModelIndex | QPersistentModelIndex


class TableModel(QAbstractTableModel):
    """Table model for song data."""

    _ids: tuple[SongId, ...] = tuple()
    _rows: dict[SongId, int]
    _songs: dict[SongId, UsdbSong]

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._rows = {}
        self._songs = {}
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
        del self._songs[event.song_id]
        del self._rows[event.song_id]
        self._ids = tuple(i for i in self._ids if i != event.song_id)
        self.endRemoveRows()

    ### QAbstractTableModel implementation

    def columnCount(self, parent: QIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(Column)

    def rowCount(self, parent: QIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._ids)

    def data(self, index: QIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if song := self._get_song(index):
                return _display_data(song, index.column())
        if role == Qt.ItemDataRole.DecorationRole:
            if song := self._get_song(index):
                return _decoration_data(song, index.column())
        return None

    def _get_song(self, index: QIndex) -> UsdbSong | None:
        if not index.isValid():
            return None
        song_id = self._ids[index.row()]
        if song := UsdbSong.get(song_id):
            return song
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role == Qt.ItemDataRole.DecorationRole:
            return Column(section).decoration_data()
        if role == Qt.ItemDataRole.DisplayRole:
            return Column(section).display_data()
        return None


def _display_data(song: UsdbSong, column: int) -> str | None:
    col = Column(column)
    match col:
        case Column.SONG_ID:
            return str(song.song_id)
        case Column.ARTIST:
            return song.artist
        case Column.TITLE:
            return song.title
        case Column.LANGUAGE:
            return song.language
        case Column.EDITION:
            return song.edition
        case Column.GOLDEN_NOTES:
            return yes_no_str(song.golden_notes)
        case Column.RATING:
            return rating_str(song.rating)
        case Column.VIEWS:
            return str(song.views)
        case Column.DOWNLOAD_STATUS:
            return str(song.status)
        case (
            Column.TXT
            | Column.AUDIO
            | Column.VIDEO
            | Column.COVER
            | Column.BACKGROUND
            | Column.PINNED
        ):
            return None
        case _ as unreachable:
            assert_never(unreachable)


def _decoration_data(song: UsdbSong, column: int) -> QIcon | None:
    if not song.sync_meta:
        return None
    col = Column(column)
    match col:
        case (
            Column.SONG_ID
            | Column.ARTIST
            | Column.TITLE
            | Column.LANGUAGE
            | Column.EDITION
            | Column.GOLDEN_NOTES
            | Column.RATING
            | Column.VIEWS
            | Column.DOWNLOAD_STATUS
        ):
            return None
        case Column.TXT:
            return optional_check_icon(bool(song.sync_meta.txt))
        case Column.AUDIO:
            return optional_check_icon(bool(song.sync_meta.audio))
        case Column.VIDEO:
            return optional_check_icon(bool(song.sync_meta.video))
        case Column.COVER:
            return optional_check_icon(bool(song.sync_meta.cover))
        case Column.BACKGROUND:
            return optional_check_icon(bool(song.sync_meta.background))
        case Column.PINNED:
            return pinned_icon(song.sync_meta.pinned)
        case _ as unreachable:
            assert_never(unreachable)


# def _sort_data(song: SongData, column: int) -> int | str | bool:
#     col = Column(column)
#     match col:
#         case Column.SONG_ID:
#             return int(song.data.song_id)
#         case Column.ARTIST:
#             return song.data.artist
#         case Column.TITLE:
#             return song.data.title
#         case Column.LANGUAGE:
#             return song.data.language
#         case Column.EDITION:
#             return song.data.edition
#         case Column.GOLDEN_NOTES:
#             return song.data.golden_notes
#         case Column.RATING:
#             return song.data.rating
#         case Column.VIEWS:
#             return song.data.views
#         case Column.TXT:
#             return song.local_files.txt
#         case Column.AUDIO:
#             return song.local_files.audio
#         case Column.VIDEO:
#             return song.local_files.video
#         case Column.COVER:
#             return song.local_files.cover
#         case Column.BACKGROUND:
#             return song.local_files.background
#         case Column.DOWNLOAD_STATUS:
#             return song.status.value
#         case Column.PINNED:
#             return song.local_files.pinned
#         case _ as unreachable:
#             assert_never(unreachable)


@cache
def rating_str(rating: int) -> str:
    return rating * "★"


def yes_no_str(yes: bool) -> str:
    return "Yes" if yes else "No"


# Creating a QIcon without a QApplication gives a runtime error, so we can't put it
# in a global, but we also don't want to keep recreating it.
# So we store them in these convenience functions.
@cache
def optional_check_icon(yes: bool) -> QIcon | None:
    return QIcon(":/icons/tick.png") if yes else None


@cache
def pinned_icon(yes: bool) -> QIcon | None:
    return QIcon(":/icons/pin.png") if yes else None
