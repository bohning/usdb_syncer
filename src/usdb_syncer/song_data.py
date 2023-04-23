"""Wrapper for song data from USDB, rendered for presentation in the song table,
plus information about locally existing files.
"""

from __future__ import annotations

import enum
from enum import Enum
from functools import cache
from pathlib import Path

import attrs
from PySide6.QtGui import QIcon
from unidecode import unidecode

from usdb_syncer import SongId
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


class DownloadErrorReason(Enum):
    """Reason for a failed song download."""

    NOT_LOGGED_IN = enum.auto()
    NOT_FOUND = enum.auto()

    def message(self) -> str:
        match self:
            case DownloadErrorReason.NOT_LOGGED_IN:
                return (
                    "Aborted; not logged in. Log in to USDB in your browser and "
                    "select the browser in the USDB Syncer settings."
                )
            case DownloadErrorReason.NOT_FOUND:
                return "Could not find song on USDB!"
            case _ as unreachable:
                assert_never(unreachable)


@attrs.define
class DownloadResult:
    """Result of a song download to be passed by signal."""

    song_id: SongId
    data: SongData | None = None
    error: DownloadErrorReason | None = None


@attrs.define
class LocalFiles:
    """The path of a .usdb file and which files exist in the same folder."""

    usdb_path: Path | None = None
    txt: bool = False
    audio: bool = False
    video: bool = False
    cover: bool = False
    background: bool = False

    @classmethod
    def from_sync_meta(cls, usdb_path: Path, sync_meta: SyncMeta) -> LocalFiles:
        return cls(
            usdb_path=usdb_path,
            txt=bool(sync_meta.txt),
            audio=bool(sync_meta.audio),
            video=bool(sync_meta.video),
            cover=bool(sync_meta.cover),
            background=bool(sync_meta.background),
        )


class DownloadStatus(Enum):
    """Status of song in download queue."""

    NONE = 0
    STAGED = 1
    PENDING = 2
    DOWNLOADING = 3
    DONE = 4
    FAILED = 5

    def __str__(self) -> str:  # pylint: disable=invalid-str-returned
        match self:
            case DownloadStatus.NONE | DownloadStatus.STAGED:
                return ""
            case DownloadStatus.PENDING:
                return "Pending"
            case DownloadStatus.DOWNLOADING:
                return "Downloading"
            case DownloadStatus.DONE:
                return "Done"
            case DownloadStatus.FAILED:
                return "Failed"
            case _ as unreachable:
                assert_never(unreachable)

    def can_be_unstaged(self) -> bool:
        return self in (
            DownloadStatus.STAGED,
            DownloadStatus.DONE,
            DownloadStatus.FAILED,
        )

    def can_be_downloaded(self) -> bool:
        return self in (
            DownloadStatus.NONE,
            DownloadStatus.STAGED,
            DownloadStatus.FAILED,
        )


@attrs.define
class SongData:
    """Wrapper for song data from USDB, rendered for presentation in the song table,
    plus information about locally existing files.
    """

    data: UsdbSong
    fuzzy_text: FuzzySearchText
    local_files: LocalFiles
    status: DownloadStatus

    @classmethod
    def from_usdb_song(
        cls,
        song: UsdbSong,
        local_files: LocalFiles,
        status: DownloadStatus = DownloadStatus.NONE,
    ) -> SongData:
        return cls(song, FuzzySearchText(song), local_files, status)

    def with_local_files(self, local_files: LocalFiles) -> SongData:
        return SongData(self.data, self.fuzzy_text, local_files, self.status)

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
            case Column.DOWNLOAD_STATUS:
                return str(self.status)
            case (
                Column.TXT
                | Column.AUDIO
                | Column.VIDEO
                | Column.COVER
                | Column.BACKGROUND
            ):
                return None
            case _ as unreachable:
                assert_never(unreachable)

    def decoration_data(self, column: int) -> QIcon | None:
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
            ):
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

    def sort_data(self, column: int) -> int | str | bool:
        col = Column(column)
        match col:
            case Column.SONG_ID:
                return int(self.data.song_id)
            case Column.ARTIST:
                return self.data.artist
            case Column.TITLE:
                return self.data.title
            case Column.LANGUAGE:
                return self.data.language
            case Column.EDITION:
                return self.data.edition
            case Column.GOLDEN_NOTES:
                return self.data.golden_notes
            case Column.RATING:
                return self.data.rating
            case Column.VIEWS:
                return self.data.views
            case Column.TXT:
                return self.local_files.txt
            case Column.AUDIO:
                return self.local_files.audio
            case Column.VIDEO:
                return self.local_files.video
            case Column.COVER:
                return self.local_files.cover
            case Column.BACKGROUND:
                return self.local_files.background
            case Column.DOWNLOAD_STATUS:
                return self.status.value
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
