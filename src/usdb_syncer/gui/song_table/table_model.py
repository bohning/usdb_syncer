"""Table model for song data."""

from enum import Enum
from functools import cache
from typing import Any, Iterable, Iterator, assert_never

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)
from PySide6.QtGui import QIcon

from usdb_syncer import SongId
from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.song_data import SongData
from usdb_syncer.usdb_scraper import UsdbSong

QIndex = QModelIndex | QPersistentModelIndex


class CustomRole(int, Enum):
    """Custom values expanding Qt.QItemDataRole."""

    ALL_DATA = 100
    SORT = 101


class TableModel(QAbstractTableModel):
    """Table model for song data."""

    songs: tuple[SongData, ...] = tuple()
    rows: dict[SongId, int]

    def __init__(self, parent: QObject) -> None:
        self.rows = {}
        super().__init__(parent)

    def set_data(self, songs: tuple[SongData, ...]) -> None:
        self.beginResetModel()
        self.songs = songs
        self.rows = {song.data.song_id: idx for idx, song in enumerate(songs)}
        self.endResetModel()

    def update_item(self, new: SongData) -> None:
        row = self.rows[new.data.song_id]
        self.songs = self.songs[:row] + (new,) + self.songs[row + 1 :]
        self.row_changed(row)

    def remove_row(self, row: int) -> None:
        self.set_data(self.songs[:row] + self.songs[row + 1 :])

    def ids_for_indices(self, indices: Iterable[QModelIndex]) -> list[SongId]:
        return [self.songs[idx.row()].data.song_id for idx in indices]

    def ids_for_rows(self, rows: Iterable[int]) -> list[SongId]:
        return [self.songs[row].data.song_id for row in rows]

    def indices_for_ids(self, ids: Iterable[SongId]) -> list[QModelIndex]:
        return [
            self.index(row, 0)
            for song_id in ids
            if (row := self.rows.get(song_id, None)) is not None
        ]

    def item_for_id(self, song_id: SongId) -> SongData | None:
        if (idx := self.rows.get(song_id)) is not None:
            return self.songs[idx]
        return None

    def row_for_id(self, song_id: SongId) -> int | None:
        return self.rows.get(song_id)

    def all_local_songs(self) -> Iterator[UsdbSong]:
        return (song.data for song in self.songs if song.local_files.txt)

    def row_changed(self, row: int) -> None:
        start_idx = self.index(row, 0)
        end_idx = self.index(row, self.columnCount() - 1)
        self.dataChanged.emit(start_idx, end_idx)  # type:ignore

    ### QAbstractTableModel implementation

    def columnCount(self, parent: QIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(Column)

    def rowCount(self, parent: QIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.songs)

    def data(self, index: QIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return _display_data(self.songs[index.row()], index.column())
        if role == Qt.ItemDataRole.DecorationRole:
            return _decoration_data(self.songs[index.row()], index.column())
        if role == CustomRole.ALL_DATA:
            return self.songs[index.row()]
        if role == CustomRole.SORT:
            return _sort_data(self.songs[index.row()], index.column())
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


def _display_data(song: SongData, column: int) -> str | None:
    col = Column(column)
    match col:
        case Column.SONG_ID:
            return str(song.data.song_id)
        case Column.ARTIST:
            return song.data.artist
        case Column.TITLE:
            return song.data.title
        case Column.LANGUAGE:
            return song.data.language
        case Column.EDITION:
            return song.data.edition
        case Column.GOLDEN_NOTES:
            return yes_no_str(song.data.golden_notes)
        case Column.RATING:
            return rating_str(song.data.rating)
        case Column.VIEWS:
            return str(song.data.views)
        case Column.DOWNLOAD_STATUS:
            return str(song.status)
        case (
            Column.TXT | Column.AUDIO | Column.VIDEO | Column.COVER | Column.BACKGROUND
        ):
            return None
        case _ as unreachable:
            assert_never(unreachable)


def _decoration_data(song: SongData, column: int) -> QIcon | None:
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
            return optional_check_icon(song.local_files.txt)
        case Column.AUDIO:
            return optional_check_icon(song.local_files.audio)
        case Column.VIDEO:
            return optional_check_icon(song.local_files.video)
        case Column.COVER:
            return optional_check_icon(song.local_files.cover)
        case Column.BACKGROUND:
            return optional_check_icon(song.local_files.background)
        case _ as unreachable:
            assert_never(unreachable)


def _sort_data(song: SongData, column: int) -> int | str | bool:
    col = Column(column)
    match col:
        case Column.SONG_ID:
            return int(song.data.song_id)
        case Column.ARTIST:
            return song.data.artist
        case Column.TITLE:
            return song.data.title
        case Column.LANGUAGE:
            return song.data.language
        case Column.EDITION:
            return song.data.edition
        case Column.GOLDEN_NOTES:
            return song.data.golden_notes
        case Column.RATING:
            return song.data.rating
        case Column.VIEWS:
            return song.data.views
        case Column.TXT:
            return song.local_files.txt
        case Column.AUDIO:
            return song.local_files.audio
        case Column.VIDEO:
            return song.local_files.video
        case Column.COVER:
            return song.local_files.cover
        case Column.BACKGROUND:
            return song.local_files.background
        case Column.DOWNLOAD_STATUS:
            return song.status.value
        case _ as unreachable:
            assert_never(unreachable)


@cache
def rating_str(rating: int) -> str:
    return rating * "★"


def yes_no_str(yes: bool) -> str:
    return "Yes" if yes else "No"


# Creating a QIcon without a QApplication gives a runtime error, so we can't put it
# in a global, but we also don't want to keep recreating it.
# So we store it in this convenience function.
@cache
def optional_check_icon(yes: bool) -> QIcon | None:
    return QIcon(":/icons/tick.png") if yes else None
