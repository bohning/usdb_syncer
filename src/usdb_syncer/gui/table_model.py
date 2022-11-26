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
from unidecode import unidecode

from usdb_syncer import SongId
from usdb_syncer.song_list_fetcher import SyncedSongMeta
from usdb_syncer.usdb_scraper import SongMeta

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


class TableSongMeta:
    """SongMeta wrapper for use in the song table."""

    def __init__(self, data: SongMeta) -> None:
        self.data = data
        self.song_id = data.song_id
        self.song_id_str = str(data.song_id)
        self.golden_notes = "Yes" if data.golden_notes else "No"
        self.rating_str = data.rating_str()
        self._checks: dict[int, bool] = {}
        self.searchable_text = unidecode(
            " ".join(
                (
                    self.song_id_str,
                    self.data.artist,
                    self.data.title,
                    self.data.language,
                    self.data.edition,
                )
            )
        ).lower()

    def display_data(self, index: int) -> str:
        match index:
            case 0:
                return self.song_id_str
            case 1:
                return self.data.artist
            case 2:
                return self.data.title
            case 3:
                return self.data.language
            case 4:
                return self.data.edition
            case 5:
                return self.golden_notes
            case 6:
                return self.rating_str
            case 7:
                return str(self.data.views)
            case _:
                return ""

    def decoration_data(self, index: int) -> QIcon | None:
        return QIcon(":/icons/tick.png") if self._checks.get(index) else None

    def update_checks(self, checks: dict[int, bool]) -> None:
        self._checks.update(checks)


class TableModel(QAbstractTableModel):
    """Table model for song data."""

    _songs: list[SyncedSongMeta]
    _indices: dict[SongId, int]

    def __init__(self, parent: QObject) -> None:
        self._songs = []
        self._indices = {}
        super().__init__(parent)

    def set_data(self, songs: list[SyncedSongMeta]) -> None:
        self.beginResetModel()
        self._songs = songs
        self._indices = dict(map(lambda t: (t[1].song_id, t[0]), enumerate(songs)))
        self.endResetModel()

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

    def ids_for_indices(self, indices: Iterator[QModelIndex]) -> list[SongId]:
        return [self._songs[idx.row()].song_id for idx in indices]

    def item_for_id(self, song_id: SongId) -> SongMeta | None:
        if (idx := self._indices.get(song_id)) is not None:
            return self._songs[idx].data
        return None

    def all_local_songs(self) -> Iterator[SongMeta]:
        return (song.data for song in self._songs if song.local_txt)

    def resync_data(self, song_dir: str) -> None:
        self.beginResetModel()
        self._songs = [SyncedSongMeta(s.data, song_dir) for s in self._songs]
        self.endResetModel()
