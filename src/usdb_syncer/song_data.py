"""Wrapper for song data from USDB, rendered for presentation in the song table,
plus information about locally existing files.
"""

from __future__ import annotations

from functools import cache

import attrs
from PySide6.QtGui import QIcon
from unidecode import unidecode

from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.typing_helpers import assert_never
from usdb_syncer.usdb_scraper import UsdbSong


class FuzzySearchText:
    """Song data for robust searching."""

    def __init__(self, song: UsdbSong) -> None:
        self.song_id = str(song.song_id)
        self.artist = fuzz_text(song.artist)
        self.title = fuzz_text(song.title)
        self.language = fuzz_text(song.language)
        self.edition = fuzz_text(song.edition)

    def __contains__(self, text: str) -> bool:
        return any(
            text in attr
            for attr in (
                self.song_id,
                self.artist,
                self.title,
                self.language,
                self.edition,
            )
        )


# common word variations
REPLACEMENTS = (
    (" vs. ", " vs  "),
    (" & ", " and "),
    ("&", " and "),
    (" + ", " and "),
    (" ft. ", " feat. "),
    (" ft ", " feat. "),
    (" feat ", " feat. "),
    ("!", ""),
    ("?", ""),
    ("/", ""),
)


def fuzz_text(text: str) -> str:
    text = unidecode(text).lower()
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    return text


@attrs.define
class LocalFiles:
    """The path of a .usdb file and if which files exist in the same folder."""

    usdb_path: str | None = None
    txt: bool = False
    audio: bool = False
    video: bool = False
    cover: bool = False
    background: bool = False

    @classmethod
    def from_sync_meta(cls, usdb_path: str, sync_meta: SyncMeta) -> LocalFiles:
        return cls(
            usdb_path=usdb_path,
            txt=bool(sync_meta.txt),
            audio=bool(sync_meta.audio),
            video=bool(sync_meta.video),
            cover=bool(sync_meta.cover),
            background=bool(sync_meta.background),
        )


@attrs.frozen(auto_attribs=True)
class SongData:
    """Wrapper for song data from USDB, rendered for presentation in the song table,
    plus information about locally existing files.
    """

    data: UsdbSong
    fuzzy_text: FuzzySearchText
    local_files: LocalFiles

    @classmethod
    def from_usdb_song(cls, song: UsdbSong, local_files: LocalFiles) -> SongData:
        return cls(song, FuzzySearchText(song), local_files)

    def with_local_files(self, local_files: LocalFiles) -> SongData:
        return SongData(self.data, self.fuzzy_text, local_files)

    def display_data(self, column: int) -> str | None:
        col = Column(column)
        match col:
            case Column.SONG_ID:
                return str(self.data.song_id)
            case Column.ARTIST:
                return self.data.artist
            case Column.TITLE:
                return self.data.title
            case Column.LANGUAGE:
                return self.data.language
            case Column.EDITION:
                return self.data.edition
            case Column.GOLDEN_NOTES:
                return yes_no_str(self.data.golden_notes)
            case Column.RATING:
                return rating_str(self.data.rating)
            case Column.VIEWS:
                return str(self.data.views)
            case Column.TXT | Column.AUDIO | Column.VIDEO | Column.COVER | \
                Column.BACKGROUND:  # fmt:skip
                return None
            case _ as unreachable:
                assert_never(unreachable)

    def decoration_data(self, column: int) -> QIcon | None:
        col = Column(column)
        match col:
            case Column.SONG_ID | Column.ARTIST | Column.TITLE | Column.LANGUAGE | \
                Column.EDITION | Column.GOLDEN_NOTES | Column.RATING | Column.VIEWS:  # fmt:skip
                return None
            case Column.TXT:
                return optional_check_icon(self.local_files.txt)
            case Column.AUDIO:
                return optional_check_icon(self.local_files.audio)
            case Column.VIDEO:
                return optional_check_icon(self.local_files.video)
            case Column.COVER:
                return optional_check_icon(self.local_files.cover)
            case Column.BACKGROUND:
                return optional_check_icon(self.local_files.background)
            case _ as unreachable:
                assert_never(unreachable)


@cache
def rating_str(rating: int) -> str:
    return rating * "★"


def yes_no_str(yes: bool) -> str:
    return "Yes" if yes else "No"


# Creating a QIcon without a QApplication gives a runtime error, so we can't put it
# in a global, but we also don't want to keep recreating it.
# So we store it in this convenience function.
@cache
def optional_check_icon(yes: bool) -> QIcon | None:
    return QIcon(":/icons/tick.png") if yes else None
