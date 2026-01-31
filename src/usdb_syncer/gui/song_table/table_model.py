"""Table model for song data."""

from collections.abc import Iterable
from datetime import datetime
from functools import cache
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
from usdb_syncer.constants import BLACK_STAR, HALF_BLACK_STAR
from usdb_syncer.db import JobStatus, ResourceKind
from usdb_syncer.gui import icons
from usdb_syncer.gui.fonts import get_rating_font
from usdb_syncer.gui.song_table.column import Column
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
        return 0 if parent.isValid() else len(Column)

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
            return Column.from_index(section).decoration_data()
        if role == Qt.ItemDataRole.DisplayRole:
            return Column.from_index(section).display_data()
        return None


def _display_data(song: UsdbSong, column: int) -> str | None:  # noqa: C901
    col = Column.from_index(column)
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
        case Column.YEAR:
            return str(song.year) if song.year else ""
        case Column.GENRE:
            return song.genre
        case Column.CREATOR:
            return song.creator
        case Column.TAGS:
            return song.tags
        case Column.LAST_CHANGE:
            return str(datetime.fromtimestamp(song.usdb_mtime))
        case Column.DOWNLOAD_STATUS:
            return str(song.status)
        case (
            Column.SAMPLE_URL
            | Column.TXT
            | Column.AUDIO
            | Column.VIDEO
            | Column.COVER
            | Column.BACKGROUND
            | Column.PINNED
        ):
            return None
        case _ as unreachable:
            assert_never(unreachable)


def _decoration_data(song: UsdbSong, column: int) -> QIcon | None:  # noqa: C901
    col = Column.from_index(column)
    sync_meta = song.sync_meta
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
            | Column.YEAR
            | Column.GENRE
            | Column.CREATOR
            | Column.TAGS
            | Column.LAST_CHANGE
        ):
            return None
        case Column.SAMPLE_URL:
            local = bool(
                song.sync_meta and song.sync_meta.resource_is_local(ResourceKind.AUDIO)
            )
            if song.is_playing and local:
                icon = icons.Icon.PAUSE_LOCAL
            elif song.is_playing:
                icon = icons.Icon.PAUSE_REMOTE
            elif local:
                icon = icons.Icon.PLAY_LOCAL
            elif song.sample_url:
                icon = icons.Icon.PLAY_REMOTE
            else:
                return None
        case Column.TXT:
            if not (sync_meta and (txt := sync_meta.txt)):
                return None
            icon = status_icon(txt)
        case Column.AUDIO:
            if not (sync_meta and (audio := sync_meta.audio)):
                return None
            icon = status_icon(audio)
        case Column.VIDEO:
            if not (sync_meta and (video := sync_meta.video)):
                return None
            icon = status_icon(video)
        case Column.COVER:
            if not (sync_meta and (cover := sync_meta.cover)):
                return None
            icon = status_icon(cover)
        case Column.BACKGROUND:
            if not (sync_meta and (background := sync_meta.background)):
                return None
            icon = status_icon(background)
        case Column.PINNED:
            if not (sync_meta and sync_meta.pinned):
                return None
            icon = icons.Icon.PIN
        case _ as unreachable:
            assert_never(unreachable)
    return icon.icon()


def status_icon(resource: Resource) -> icons.Icon:
    match resource.status:
        case JobStatus.SUCCESS | JobStatus.SUCCESS_UNCHANGED:
            icon = icons.Icon.SUCCESS
        case JobStatus.SKIPPED_DISABLED:
            icon = icons.Icon.SKIPPED_DISABLED
        case JobStatus.SKIPPED_UNAVAILABLE:
            icon = icons.Icon.SKIPPED_UNAVAILABLE
        case JobStatus.FALLBACK:
            icon = icons.Icon.FALLBACK
        case JobStatus.FAILURE_EXISTING:
            icon = icons.Icon.FAILURE_EXISTING
        case JobStatus.FAILURE:
            icon = icons.Icon.FAILURE
        case _ as unreachable:
            assert_never(unreachable)
    return icon


def _font_data(column: int) -> QFont | None:
    col = Column.from_index(column)
    if col == Column.RATING:
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


@cache
def rating_str(rating: float) -> str:
    return int(rating) * BLACK_STAR + (HALF_BLACK_STAR if rating % 1 == 0.5 else "")


def yes_no_str(yes: bool) -> str:
    return "Yes" if yes else "No"
