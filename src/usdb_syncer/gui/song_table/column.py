"""Table model for song data."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, NamedTuple, assert_never

from PySide6.QtGui import QIcon

from usdb_syncer import db
from usdb_syncer.gui.icons import Icon

if TYPE_CHECKING:
    from PySide6.QtGui import QIcon

    from usdb_syncer.sync_meta import Resource, SyncMeta


MIN_COLUMN_WIDTH = 24


class ColumnValue(NamedTuple):
    """Values of a Column variant."""

    label: str
    display_data: bool
    icon: Icon
    fixed_size: int | None
    song_order: db.SongOrder


class Column(enum.Enum):
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

    def display_data(self) -> str | None:
        return self.value.label if self.value.display_data else None

    def decoration_data(self) -> QIcon:
        return self.value.icon.icon()

    @classmethod
    def from_song_order(cls, song_order: db.SongOrder) -> Column:  # noqa: C901
        match song_order:
            case db.SongOrder.SAMPLE_URL:
                return Column.SAMPLE_URL
            case db.SongOrder.SONG_ID | db.SongOrder.NONE:
                return Column.SONG_ID
            case db.SongOrder.ARTIST:
                return Column.ARTIST
            case db.SongOrder.TITLE:
                return Column.TITLE
            case db.SongOrder.LANGUAGE:
                return Column.LANGUAGE
            case db.SongOrder.EDITION:
                return Column.EDITION
            case db.SongOrder.GOLDEN_NOTES:
                return Column.GOLDEN_NOTES
            case db.SongOrder.RATING:
                return Column.RATING
            case db.SongOrder.VIEWS:
                return Column.VIEWS
            case db.SongOrder.YEAR:
                return Column.YEAR
            case db.SongOrder.GENRE:
                return Column.GENRE
            case db.SongOrder.CREATOR:
                return Column.CREATOR
            case db.SongOrder.TAGS:
                return Column.TAGS
            case db.SongOrder.PINNED:
                return Column.PINNED
            case db.SongOrder.TXT:
                return Column.TXT
            case db.SongOrder.AUDIO:
                return Column.AUDIO
            case db.SongOrder.VIDEO:
                return Column.VIDEO
            case db.SongOrder.COVER:
                return Column.COVER
            case db.SongOrder.BACKGROUND:
                return Column.BACKGROUND
            case db.SongOrder.LAST_CHANGE:
                return Column.LAST_CHANGE
            case db.SongOrder.STATUS:
                return Column.DOWNLOAD_STATUS
            case unreachable:
                assert_never(unreachable)

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

    @staticmethod
    def from_index(index: int) -> Column:
        return COLUMNS[index]

    def index(self) -> int:
        return COLUMNS.index(self)


COLUMNS = list(Column)
