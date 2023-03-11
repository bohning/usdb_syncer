"""Table model for song data."""

from enum import Enum, IntEnum
from functools import cache

from PySide6.QtCore import QModelIndex, QPersistentModelIndex
from PySide6.QtGui import QIcon

from usdb_syncer.typing_helpers import assert_never

QIndex = QModelIndex | QPersistentModelIndex


class CustomRole(int, Enum):
    """Custom values expanding Qt.QItemDataRole."""

    ALL_DATA = 100


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
            case Column.SONG_ID | Column.GOLDEN_NOTES | Column.RATING | Column.VIEWS | \
                Column.TXT | Column.AUDIO | Column.VIDEO | Column.COVER:  # fmt:skip
                return None
            case Column.BACKGROUND:
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
            case _ as unreachable:
                assert_never(unreachable)
