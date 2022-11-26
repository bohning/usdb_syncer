"""Table model for song data."""

from enum import Enum
from functools import cache
from typing import Any, Iterator

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)
from PySide6.QtGui import QIcon

from usdb_syncer import SongId, settings
from usdb_syncer.song_data import SongData
from usdb_syncer.usdb_scraper import UsdbSong

QIndex = QModelIndex | QPersistentModelIndex


class CustomRole(int, Enum):
    """Custom values expanding Qt.QItemDataRole."""

    ALL_DATA = 100


@cache
def columns() -> tuple[tuple[QIcon, str], ...]:
    return (
        (QIcon(":/icons/id.png"), "ID"),
        (QIcon(":/icons/artist.png"), "Artist"),
        (QIcon(":/icons/title.png"), "Title"),
        (QIcon(":/icons/language.png"), "Language"),
        (QIcon(":/icons/edition.png"), "Edition"),
        (QIcon(":/icons/golden_notes.png"), ""),
        (QIcon(":/icons/rating.png"), ""),
        (QIcon(":/icons/views.png"), ""),
        (QIcon(":/icons/text.png"), ""),
        (QIcon(":/icons/audio.png"), ""),
        (QIcon(":/icons/video.png"), ""),
        (QIcon(":/icons/cover.png"), ""),
        (QIcon(":/icons/background.png"), ""),
    )


class TableModel(QAbstractTableModel):
    """Table model for song data."""

    _songs: tuple[SongData, ...] = tuple()
    _indices: dict[SongId, int]

    def __init__(self, parent: QObject) -> None:
        self._indices = {}
        super().__init__(parent)

    def set_data(self, songs: list[UsdbSong]) -> None:
        song_dir = settings.get_song_dir()
        self.beginResetModel()
        self._songs = tuple(SongData.from_usdb_song(s, song_dir) for s in songs)
        self._indices = dict(map(lambda t: (t[1].song_id, t[0]), enumerate(songs)))
        self.endResetModel()

    def ids_for_indices(self, indices: Iterator[QModelIndex]) -> list[SongId]:
        return [self._songs[idx.row()].data.song_id for idx in indices]

    def item_for_id(self, song_id: SongId) -> UsdbSong | None:
        if (idx := self._indices.get(song_id)) is not None:
            return self._songs[idx].data
        return None

    def all_local_songs(self) -> Iterator[UsdbSong]:
        return (song.data for song in self._songs if song.local_txt)

    def resync_local_data(self) -> None:
        song_dir = settings.get_song_dir()
        self.beginResetModel()
        self._songs = tuple(
            SongData.from_usdb_song(s.data, song_dir) for s in self._songs
        )
        self.endResetModel()

    ### QAbstractTableModel implementation

    def columnCount(self, parent: QIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(columns())

    def rowCount(self, parent: QIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._songs)

    def data(self, index: QIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return self._songs[index.row()].display_data(index.column())
        if role == Qt.ItemDataRole.DecorationRole:
            return self._songs[index.row()].decoration_data(index.column())
        if role == CustomRole.ALL_DATA:
            return self._songs[index.row()]
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
            return columns()[section][0]
        if role == Qt.ItemDataRole.DisplayRole:
            return columns()[section][1]
        return None
