"""Table model for song data."""

from __future__ import annotations

import enum
from enum import IntEnum
from functools import cache
from typing import assert_never

from PySide6.QtGui import QIcon

from usdb_syncer import db


class Column(IntEnum):
    """Table columns."""

    SONG_ID = 0
    ARTIST = enum.auto()
    TITLE = enum.auto()
    LANGUAGE = enum.auto()
    EDITION = enum.auto()
    GOLDEN_NOTES = enum.auto()
    RATING = enum.auto()
    VIEWS = enum.auto()
    PINNED = enum.auto()
    TXT = enum.auto()
    AUDIO = enum.auto()
    VIDEO = enum.auto()
    COVER = enum.auto()
    BACKGROUND = enum.auto()
    DOWNLOAD_STATUS = enum.auto()

    def display_data(self) -> str | None:
        match self:
            case Column.ARTIST:
                return "Artist"
            case Column.TITLE:
                return "Title"
            case Column.LANGUAGE:
                return "Language"
            case Column.EDITION:
                return "Edition"
            case Column.DOWNLOAD_STATUS:
                return "Status"
            case (
                Column.SONG_ID
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

    # https://github.com/PyCQA/pylint/issues/7857
    @cache  # pylint: disable=method-cache-max-size-none
    def decoration_data(self) -> QIcon:
        match self:
            case Column.SONG_ID:
                return QIcon(":/icons/id.png")
            case Column.ARTIST:
                return QIcon(":/icons/artist.png")
            case Column.TITLE:
                return QIcon(":/icons/title.png")
            case Column.LANGUAGE:
                return QIcon(":/icons/language.png")
            case Column.EDITION:
                return QIcon(":/icons/edition.png")
            case Column.GOLDEN_NOTES:
                return QIcon(":/icons/golden_notes.png")
            case Column.RATING:
                return QIcon(":/icons/rating.png")
            case Column.VIEWS:
                return QIcon(":/icons/views.png")
            case Column.TXT:
                return QIcon(":/icons/text.png")
            case Column.AUDIO:
                return QIcon(":/icons/audio.png")
            case Column.VIDEO:
                return QIcon(":/icons/video.png")
            case Column.COVER:
                return QIcon(":/icons/cover.png")
            case Column.BACKGROUND:
                return QIcon(":/icons/background.png")
            case Column.DOWNLOAD_STATUS:
                return QIcon(":/icons/status.png")
            case Column.PINNED:
                return QIcon(":/icons/pin.png")
            case _ as unreachable:
                assert_never(unreachable)

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
            ):
                return None
            case (
                Column.TXT
                | Column.AUDIO
                | Column.VIDEO
                | Column.COVER
                | Column.BACKGROUND
                | Column.PINNED
            ):
                return 24
            case _ as unreachable:
                assert_never(unreachable)

    def song_order(self) -> db.SongOrder:
        match self:
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
                return db.SongOrder.SYNC_TIME
            case unreachable:
                assert_never(unreachable)
