"""Table model for song data."""

from __future__ import annotations

import enum
from enum import IntEnum
from typing import assert_never

from PySide6.QtGui import QIcon

from usdb_syncer import db
from usdb_syncer.gui.icons import Icon


class Column(IntEnum):
    """Table columns."""

    SAMPLE_URL = 0
    SONG_ID = enum.auto()
    ARTIST = enum.auto()
    TITLE = enum.auto()
    LANGUAGE = enum.auto()
    EDITION = enum.auto()
    GOLDEN_NOTES = enum.auto()
    RATING = enum.auto()
    VIEWS = enum.auto()
    YEAR = enum.auto()
    GENRE = enum.auto()
    CREATOR = enum.auto()
    TAGS = enum.auto()
    PINNED = enum.auto()
    TXT = enum.auto()
    AUDIO = enum.auto()
    VIDEO = enum.auto()
    COVER = enum.auto()
    BACKGROUND = enum.auto()
    DOWNLOAD_STATUS = enum.auto()

    def display_data(self) -> str | None:  # noqa: C901
        match self:
            case Column.SONG_ID:
                return "ID"
            case Column.ARTIST:
                return "Artist"
            case Column.TITLE:
                return "Title"
            case Column.LANGUAGE:
                return "Language"
            case Column.EDITION:
                return "Edition"
            case Column.YEAR:
                return "Year"
            case Column.GENRE:
                return "Genre"
            case Column.CREATOR:
                return "Creator"
            case Column.TAGS:
                return "Tags"
            case Column.DOWNLOAD_STATUS:
                return "Status"
            case (
                Column.SAMPLE_URL
                | Column.GOLDEN_NOTES
                | Column.RATING
                | Column.VIEWS
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

    def decoration_data(self) -> QIcon:  # noqa: C901
        match self:
            case Column.SAMPLE_URL:
                icon = Icon.AUDIO_SAMPLE
            case Column.SONG_ID:
                icon = Icon.ID
            case Column.ARTIST:
                icon = Icon.ARTIST
            case Column.TITLE:
                icon = Icon.TITLE
            case Column.LANGUAGE:
                icon = Icon.LANGUAGE
            case Column.EDITION:
                icon = Icon.EDITION
            case Column.GOLDEN_NOTES:
                icon = Icon.GOLDEN_NOTES
            case Column.RATING:
                icon = Icon.RATING
            case Column.VIEWS:
                icon = Icon.VIEWS
            case Column.YEAR:
                icon = Icon.CALENDAR
            case Column.GENRE:
                icon = Icon.GENRE
            case Column.CREATOR:
                icon = Icon.CREATOR
            case Column.TAGS:
                icon = Icon.TAGS
            case Column.TXT:
                icon = Icon.TEXT
            case Column.AUDIO:
                icon = Icon.AUDIO
            case Column.VIDEO:
                icon = Icon.VIDEO
            case Column.COVER:
                icon = Icon.COVER
            case Column.BACKGROUND:
                icon = Icon.BACKGROUND
            case Column.DOWNLOAD_STATUS:
                icon = Icon.DOWNLOAD
            case Column.PINNED:
                icon = Icon.PIN
            case _ as unreachable:
                assert_never(unreachable)
        return icon.icon()

    def fixed_size(self) -> int | None:
        match self:
            case (
                Column.ARTIST
                | Column.TITLE
                | Column.LANGUAGE
                | Column.EDITION
                | Column.DOWNLOAD_STATUS
                | Column.SONG_ID
                | Column.VIEWS
                | Column.RATING
                | Column.GOLDEN_NOTES
                | Column.YEAR
                | Column.GENRE
                | Column.CREATOR
                | Column.TAGS
            ):
                return None
            case (
                Column.SAMPLE_URL
                | Column.TXT
                | Column.AUDIO
                | Column.VIDEO
                | Column.COVER
                | Column.BACKGROUND
                | Column.PINNED
            ):
                return 24
            case _ as unreachable:
                assert_never(unreachable)

    def song_order(self) -> db.SongOrder:  # noqa: C901
        match self:
            case Column.SAMPLE_URL:
                return db.SongOrder.SAMPLE_URL
            case Column.SONG_ID:
                return db.SongOrder.SONG_ID
            case Column.ARTIST:
                return db.SongOrder.ARTIST
            case Column.TITLE:
                return db.SongOrder.TITLE
            case Column.LANGUAGE:
                return db.SongOrder.LANGUAGE
            case Column.EDITION:
                return db.SongOrder.EDITION
            case Column.GOLDEN_NOTES:
                return db.SongOrder.GOLDEN_NOTES
            case Column.RATING:
                return db.SongOrder.RATING
            case Column.VIEWS:
                return db.SongOrder.VIEWS
            case Column.YEAR:
                return db.SongOrder.YEAR
            case Column.GENRE:
                return db.SongOrder.GENRE
            case Column.CREATOR:
                return db.SongOrder.CREATOR
            case Column.TAGS:
                return db.SongOrder.TAGS
            case Column.PINNED:
                return db.SongOrder.PINNED
            case Column.TXT:
                return db.SongOrder.TXT
            case Column.AUDIO:
                return db.SongOrder.AUDIO
            case Column.VIDEO:
                return db.SongOrder.VIDEO
            case Column.COVER:
                return db.SongOrder.COVER
            case Column.BACKGROUND:
                return db.SongOrder.BACKGROUND
            case Column.DOWNLOAD_STATUS:
                return db.SongOrder.STATUS
            case unreachable:
                assert_never(unreachable)

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
            case db.SongOrder.STATUS:
                return Column.DOWNLOAD_STATUS
            case unreachable:
                assert_never(unreachable)
