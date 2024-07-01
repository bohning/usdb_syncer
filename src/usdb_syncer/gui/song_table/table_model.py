"""Table model for song data."""

from functools import cache
from pathlib import Path
from typing import Any, Iterable, assert_never

from PIL import Image
from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)
from PySide6.QtGui import QIcon

from usdb_syncer import SongId, events, utils
from usdb_syncer.constants import ImageQualityThresholds
from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.usdb_song import DownloadStatus, UsdbSong

QIndex = QModelIndex | QPersistentModelIndex


class TableModel(QAbstractTableModel):
    """Table model for song data."""

    _ids: tuple[SongId, ...] = tuple()
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
        if role == Qt.ItemDataRole.ToolTipRole:
            if song := self._get_song(index):
                return _tooltip_data(song, index.column())
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
        case Column.YEAR:
            return str(song.year) if song.year else ""
        case Column.GENRE:
            return song.genre
        case Column.CREATOR:
            return song.creator
        case Column.TAGS:
            return song.tags
        case Column.DOWNLOAD_STATUS:
            return (
                utils.format_timestamp(song.sync_meta.mtime)
                if song.sync_meta and song.status is DownloadStatus.NONE
                else str(song.status)
            )
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
            | Column.YEAR
            | Column.GENRE
            | Column.CREATOR
            | Column.TAGS
        ):
            return None
        case Column.TXT:
            return optional_check_icon_high(bool(song.sync_meta.txt))
        case Column.AUDIO:
            return optional_check_icon_high(bool(song.sync_meta.audio))
        case Column.VIDEO:
            return optional_check_icon_high(bool(song.sync_meta.video))
        case Column.COVER:
            if song.sync_meta.cover:
                path = song.sync_meta.path.parent.joinpath(song.sync_meta.cover.fname)
                return get_cover_image_quality_icon(path)
            return None
        case Column.BACKGROUND:
            if song.sync_meta.background:
                path = song.sync_meta.path.parent.joinpath(
                    song.sync_meta.background.fname
                )
                return get_background_image_quality_icon(path)
            return None
        case Column.PINNED:
            return pinned_icon(song.sync_meta.pinned)
        case _ as unreachable:
            assert_never(unreachable)


def _tooltip_data(song: UsdbSong, column: int) -> str | None:
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
            | Column.YEAR
            | Column.GENRE
            | Column.CREATOR
            | Column.TAGS
            | Column.TXT
            | Column.PINNED
            | Column.AUDIO
            | Column.VIDEO
        ):
            return None
        case Column.COVER:
            if song.sync_meta.cover:
                path = song.sync_meta.path.parent.joinpath(song.sync_meta.cover.fname)
                return get_cover_image_quality_tooltip(path)
            return None
        case Column.BACKGROUND:
            if song.sync_meta.background:
                path = song.sync_meta.path.parent.joinpath(
                    song.sync_meta.background.fname
                )
                return get_background_image_quality_tooltip(path)
            return None
        case _ as unreachable:
            assert_never(unreachable)


def get_cover_image_quality_icon(image_path: Path) -> QIcon | None:
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            if width == height:
                match width:
                    case _ if width >= ImageQualityThresholds.COVER_HIGH:
                        return optional_check_icon_high(True)
                    case _ if width >= ImageQualityThresholds.COVER_MEDIUM:
                        return optional_check_icon_medium(True)
                    case _:
                        return optional_check_icon_low(True)
            else:
                match width:
                    case _ if width >= ImageQualityThresholds.COVER_HIGH:
                        return optional_check_icon_high_exclamation(True)
                    case _ if width >= ImageQualityThresholds.COVER_MEDIUM:
                        return optional_check_icon_medium_exclamation(True)
                    case _:
                        return optional_check_icon_low_exclamation(True)
    except IOError:
        return optional_warning(True)


def get_background_image_quality_icon(image_path: Path) -> QIcon | None:
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            if (
                width * ImageQualityThresholds.BACKGROUND_WIDTH_FACTOR
                == height * ImageQualityThresholds.BACKGROUND_HEIGHT_FACTOR
            ):
                match width:
                    case _ if width >= ImageQualityThresholds.BACKGROUND_HIGH:
                        return optional_check_icon_high(True)
                    case _ if width >= ImageQualityThresholds.BACKGROUND_MEDIUM:
                        return optional_check_icon_medium(True)
                    case _:
                        return optional_check_icon_low(True)
            else:
                match width:
                    case _ if width >= ImageQualityThresholds.BACKGROUND_HIGH:
                        return optional_check_icon_high_exclamation(True)
                    case _ if width >= ImageQualityThresholds.BACKGROUND_MEDIUM:
                        return optional_check_icon_medium_exclamation(True)
                    case _:
                        return optional_check_icon_low_exclamation(True)
    except IOError:
        return optional_warning(True)


def get_cover_image_quality_tooltip(image_path: Path) -> str | None:
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            if width == height:
                return f"{width} x {height}"
            min_size = min(width, height)
            return f"{width} x {height} (crop to {min_size} x {min_size})"
    except IOError:
        return "IOError: File could not be opened."


def get_background_image_quality_tooltip(image_path: Path) -> str | None:
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            ratio = (width * ImageQualityThresholds.BACKGROUND_WIDTH_FACTOR) / (
                height * ImageQualityThresholds.BACKGROUND_HEIGHT_FACTOR
            )
            match ratio:
                case _ if ratio == 1:
                    return f"{width} x {height}"
                case _ if ratio > 1:
                    return (
                        f"{width} x {height} (crop to {round(height*16/9)} x {height})"
                    )
                case _:
                    return f"{width} x {height} (crop to {width} x {round(width*9/16)})"
    except IOError:
        return "IOError: File could not be opened."


@cache
def rating_str(rating: int) -> str:
    return rating * "★"


def yes_no_str(yes: bool) -> str:
    return "Yes" if yes else "No"


# Creating a QIcon without a QApplication gives a runtime error, so we can't put it
# in a global, but we also don't want to keep recreating it.
# So we store them in these convenience functions.
@cache
def optional_check_icon_high(yes: bool) -> QIcon | None:
    return QIcon(":/icons/tick_high.png") if yes else None


@cache
def optional_check_icon_high_exclamation(yes: bool) -> QIcon | None:
    return QIcon(":/icons/tick_high_exclamation.png") if yes else None


@cache
def optional_check_icon_medium(yes: bool) -> QIcon | None:
    return QIcon(":/icons/tick_medium.png") if yes else None


@cache
def optional_check_icon_medium_exclamation(yes: bool) -> QIcon | None:
    return QIcon(":/icons/tick_medium_exclamation.png") if yes else None


@cache
def optional_check_icon_low(yes: bool) -> QIcon | None:
    return QIcon(":/icons/tick_low.png") if yes else None


@cache
def optional_check_icon_low_exclamation(yes: bool) -> QIcon | None:
    return QIcon(":/icons/tick_low_exclamation.png") if yes else None


@cache
def optional_warning(yes: bool) -> QIcon | None:
    return QIcon(":/icons/warning.png") if yes else None


@cache
def pinned_icon(yes: bool) -> QIcon | None:
    return QIcon(":/icons/pin.png") if yes else None
