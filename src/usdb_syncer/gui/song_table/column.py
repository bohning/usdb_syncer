"""Table model for song data."""

from __future__ import annotations

import enum
from datetime import datetime
from functools import cache
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple, assert_never

import attrs
from PySide6.QtGui import QIcon

from usdb_syncer import db, settings
from usdb_syncer.constants import BLACK_STAR, HALF_BLACK_STAR
from usdb_syncer.gui.icons import Icon

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from PySide6.QtGui import QIcon

    from usdb_syncer.sync_meta import Resource, SyncMeta
    from usdb_syncer.usdb_song import UsdbSong


MIN_COLUMN_WIDTH = 24


class ColumnBase:
    """Base for native and custom columns."""

    @staticmethod
    def len() -> int:
        return len(_ColumnRegistry.columns)

    @staticmethod
    def all_columns() -> Iterator[ColumnBase]:
        return (c for c in _ColumnRegistry.columns)

    @staticmethod
    def from_index(index: int) -> ColumnBase:
        return _ColumnRegistry.columns[index]

    def index(self) -> int:
        return _ColumnRegistry.columns.index(self)

    def val(self) -> ColumnValue:
        raise NotImplementedError

    def cell_display_data(self, song: UsdbSong) -> str | None:
        raise NotImplementedError

    def cell_decoration_data(
        self, song: UsdbSong, theme: settings.Theme
    ) -> QIcon | None:
        raise NotImplementedError

    def display_data(self) -> str | None:
        return self.val().label if self.val().display_data else None

    def decoration_data(self, theme: settings.Theme) -> QIcon:
        return self.val().icon.icon(theme)

    @staticmethod
    def from_song_order(song_order: db.SongOrderBase) -> ColumnBase:
        return next(
            (c for c in _ColumnRegistry.columns if c.val().song_order == song_order),
            _ColumnRegistry.default_column,
        )

    def get_resource_for_column(self, sync_meta: SyncMeta) -> Resource | None:
        match self:
            case Column.TXT:
                return sync_meta.txt
            case Column.AUDIO:
                return sync_meta.audio
            case Column.VIDEO:
                return sync_meta.video
            case Column.COVER:
                return sync_meta.cover
            case Column.BACKGROUND:
                return sync_meta.background
            case _:
                return None


class ColumnValue(NamedTuple):
    """Values of a Column variant."""

    label: str
    display_data: bool
    icon: Icon
    fixed_size: int | None
    song_order: db.SongOrderBase


class Column(ColumnBase, enum.Enum):
    """Table columns."""

    # fmt: off
    SAMPLE_URL = ColumnValue("Sample", False, Icon.AUDIO_SAMPLE, MIN_COLUMN_WIDTH, db.SongOrder.SAMPLE_URL)
    SONG_ID = ColumnValue("ID", True, Icon.ID, None, db.SongOrder.SONG_ID)
    ARTIST = ColumnValue("Artist", True, Icon.ARTIST, None, db.SongOrder.ARTIST)
    TITLE = ColumnValue("Title", True, Icon.TITLE, None, db.SongOrder.TITLE)
    LANGUAGE = ColumnValue("Language", True, Icon.LANGUAGE, None, db.SongOrder.LANGUAGE)
    EDITION = ColumnValue("Edition", True, Icon.EDITION, None, db.SongOrder.EDITION)
    GOLDEN_NOTES = ColumnValue("Golden Notes", False, Icon.GOLDEN_NOTES, None, db.SongOrder.GOLDEN_NOTES)
    RATING = ColumnValue("Rating", False, Icon.RATING, None, db.SongOrder.RATING)
    VIEWS = ColumnValue("Views", False, Icon.VIEWS, None, db.SongOrder.VIEWS)
    YEAR = ColumnValue("Year", True, Icon.CALENDAR, None, db.SongOrder.YEAR)
    GENRE = ColumnValue("Genre", True, Icon.GENRE, None, db.SongOrder.GENRE)
    CREATOR = ColumnValue("Creator", True, Icon.CREATOR, None, db.SongOrder.CREATOR)
    TAGS = ColumnValue("Tags", True, Icon.TAGS, None, db.SongOrder.TAGS)
    LAST_CHANGE = ColumnValue("Last Change", True, Icon.LAST_CHANGE, None, db.SongOrder.LAST_CHANGE)
    PINNED = ColumnValue("Pinned", False, Icon.PIN, MIN_COLUMN_WIDTH, db.SongOrder.PINNED)
    TXT = ColumnValue("Text", False, Icon.TEXT, MIN_COLUMN_WIDTH, db.SongOrder.TXT)
    AUDIO = ColumnValue("Audio", False, Icon.AUDIO, MIN_COLUMN_WIDTH, db.SongOrder.AUDIO)
    VIDEO = ColumnValue("Video", False, Icon.VIDEO, MIN_COLUMN_WIDTH, db.SongOrder.VIDEO)
    COVER = ColumnValue("Cover", False, Icon.COVER, MIN_COLUMN_WIDTH, db.SongOrder.COVER)
    BACKGROUND = ColumnValue("Background", False, Icon.BACKGROUND, MIN_COLUMN_WIDTH, db.SongOrder.BACKGROUND)
    DOWNLOAD_STATUS = ColumnValue("Status", True, Icon.DOWNLOAD, None, db.SongOrder.STATUS)
    # fmt: on

    def val(self) -> ColumnValue:
        return self.value

    def display_data(self) -> str | None:
        return self.value.label if self.value.display_data else None

    def get_resource_for_column(self, sync_meta: SyncMeta) -> Resource | None:
        match self:
            case Column.TXT:
                return sync_meta.txt
            case Column.AUDIO:
                return sync_meta.audio
            case Column.VIDEO:
                return sync_meta.video
            case Column.COVER:
                return sync_meta.cover
            case Column.BACKGROUND:
                return sync_meta.background
            case _:
                return None

    def cell_display_data(self, song: UsdbSong) -> str | None:  # noqa: C901
        match self:
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

    def cell_decoration_data(  # noqa: C901
        self, song: UsdbSong, theme: settings.Theme
    ) -> QIcon | None:
        sync_meta = song.sync_meta
        match self:
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
                    song.sync_meta
                    and song.sync_meta.audio
                    and song.sync_meta.audio.file
                )
                if song.is_playing and local:
                    icon = Icon.PAUSE_LOCAL
                elif song.is_playing:
                    icon = Icon.PAUSE_REMOTE
                elif local:
                    icon = Icon.PLAY_LOCAL
                elif song.sample_url:
                    icon = Icon.PLAY_REMOTE
                else:
                    return None
            case Column.TXT:
                if not (sync_meta and (txt := sync_meta.txt)):
                    return None
                icon = status_icon(txt, sync_meta.path.parent)
            case Column.AUDIO:
                if not (sync_meta and (audio := sync_meta.audio)):
                    return None
                icon = status_icon(audio, sync_meta.path.parent)
            case Column.VIDEO:
                if not (sync_meta and (video := sync_meta.video)):
                    return None
                icon = status_icon(video, sync_meta.path.parent)
            case Column.COVER:
                if not (sync_meta and (cover := sync_meta.cover)):
                    return None
                icon = status_icon(cover, sync_meta.path.parent)
            case Column.BACKGROUND:
                if not (sync_meta and (background := sync_meta.background)):
                    return None
                icon = status_icon(background, sync_meta.path.parent)
            case Column.PINNED:
                if not (sync_meta and sync_meta.pinned):
                    return None
                icon = Icon.PIN
            case _ as unreachable:
                assert_never(unreachable)
        return icon.icon(theme)


@attrs.define(frozen=True)
class CustomColumn(ColumnBase):
    """Custom table column."""

    value: ColumnValue

    def val(self) -> ColumnValue:
        return self.value

    @classmethod
    def new(cls, key: str) -> CustomColumn:
        return cls(
            ColumnValue(
                label=key,
                display_data=True,
                icon=Icon.CUSTOM_DATA,
                fixed_size=None,
                song_order=db.CustomSongOrder(key),
            )
        )

    def cell_display_data(self, song: UsdbSong) -> str | None:
        if song.sync_meta:
            return song.sync_meta.custom_data.get(self.value.label)
        return None

    def cell_decoration_data(
        self,
        song: UsdbSong,  # noqa: ARG002
        theme: settings.Theme,  # noqa: ARG002
    ) -> QIcon | None:
        return None

    def __eq__(self, value: Any) -> bool:
        return isinstance(value, CustomColumn) and self.value.label == value.value.label

    @classmethod
    def get(cls, key: str) -> CustomColumn | None:
        return col if (col := cls.new(key)) in _ColumnRegistry.columns else None

    def unregister_column(self) -> None:
        _ColumnRegistry.columns.remove(self)

    @classmethod
    def register_column(cls, key: str) -> None:
        _ColumnRegistry.columns.append(cls.new(key))


def status_icon(resource: Resource, folder: Path) -> Icon:
    match resource.status:
        case db.JobStatus.SUCCESS | db.JobStatus.SUCCESS_UNCHANGED:
            icon = (
                Icon.SUCCESS if resource.file_in_sync(folder) else Icon.SUCCESS_CHANGES
            )
        case db.JobStatus.SKIPPED_DISABLED:
            icon = Icon.SKIPPED_DISABLED
        case db.JobStatus.SKIPPED_UNAVAILABLE:
            icon = Icon.SKIPPED_UNAVAILABLE
        case db.JobStatus.FALLBACK:
            icon = (
                Icon.FALLBACK
                if resource.file_in_sync(folder)
                else Icon.FALLBACK_CHANGES
            )
        case db.JobStatus.FAILURE_EXISTING:
            icon = (
                Icon.FAILURE_EXISTING
                if resource.file_in_sync(folder)
                else Icon.FAILURE_EXISTING_CHANGES
            )
        case db.JobStatus.FAILURE:
            icon = Icon.FAILURE
        case _ as unreachable:
            assert_never(unreachable)
    return icon


class _ColumnRegistry:
    """State of available columns."""

    columns: ClassVar[list[ColumnBase]] = list(Column)
    default_column: ClassVar[ColumnBase] = columns[1]


@cache
def rating_str(rating: float) -> str:
    return int(rating) * BLACK_STAR + (HALF_BLACK_STAR if rating % 1 == 0.5 else "")


def yes_no_str(yes: bool) -> str:
    return "Yes" if yes else "No"
