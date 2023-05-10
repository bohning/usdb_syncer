"""Table model for song data."""

from enum import IntEnum
from functools import cache
from typing import assert_never

from PySide6.QtCore import QModelIndex, QPersistentModelIndex
from PySide6.QtGui import QIcon, QPaintDevice
from PySide6.QtWidgets import QHeaderView

from usdb_syncer import SongId

QIndex = QModelIndex | QPersistentModelIndex


class Column(IntEnum):
    """Table columns."""

    SONG_ID = 0
    ARTIST = 1
    TITLE = 2
    LANGUAGE = 3
    EDITION = 4
    GOLDEN_NOTES = 5
    RATING = 6
    VIEWS = 7
    TXT = 8
    AUDIO = 9
    VIDEO = 10
    COVER = 11
    BACKGROUND = 12
    DOWNLOAD_STATUS = 13

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
            case _ as unreachable:
                assert_never(unreachable)

    def display_in_batch_view(self) -> bool:
        return self in (self.SONG_ID, self.ARTIST, self.TITLE, self.DOWNLOAD_STATUS)

    def fixed_size(self, header: QHeaderView, window: QPaintDevice) -> int | None:
        match self:
            case Column.SONG_ID:
                return _horizontal_size(str(SongId(0)), header, window)
            case Column.VIEWS:
                return _horizontal_size("99999", header, window)
            case Column.RATING:
                return _horizontal_size("★★★★★", header, window)
            case Column.GOLDEN_NOTES:
                return _horizontal_size("Yes", header, window)
            case (
                Column.ARTIST
                | Column.TITLE
                | Column.LANGUAGE
                | Column.EDITION
                | Column.DOWNLOAD_STATUS
            ):
                return None
            case (
                Column.TXT
                | Column.AUDIO
                | Column.VIDEO
                | Column.COVER
                | Column.BACKGROUND
            ):
                return 24
            case _ as unreachable:
                assert_never(unreachable)


def _horizontal_size(text: str, header: QHeaderView, window: QPaintDevice) -> int:
    return (
        int(header.fontMetrics().horizontalAdvance(text) * window.devicePixelRatio())
        # for rounding down
        + 1
        # for cell padding
        + 2 * 3
    )
