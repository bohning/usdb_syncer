"""Wrapper for song data from USDB, rendered for presentation in the song table,
plus information about locally existing files.
"""

from __future__ import annotations

import enum
from enum import Enum
from pathlib import Path
from typing import Callable, assert_never

import attrs
from unidecode import unidecode

from usdb_syncer import SongId
from usdb_syncer.logger import get_logger
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.usdb_scraper import UsdbSong

_logger = get_logger(__file__)


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
    FILE_IO = enum.auto()
    UNKNOWN = enum.auto()


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
    pinned: bool = False
    txt: bool = False
    audio: bool = False
    video: bool = False
    cover: bool = False
    background: bool = False

    @classmethod
    def from_sync_meta(cls, usdb_path: Path, sync_meta: SyncMeta) -> LocalFiles:
        return cls(
            usdb_path=usdb_path,
            pinned=sync_meta.pinned,
            txt=bool(sync_meta.txt),
            audio=bool(sync_meta.audio),
            video=bool(sync_meta.video),
            cover=bool(sync_meta.cover),
            background=bool(sync_meta.background),
        )

    def try_update_sync_meta(self, modifier: Callable[[SyncMeta], None]) -> None:
        if not self.usdb_path:
            return
        meta = SyncMeta.try_from_file(self.usdb_path)
        if not meta:
            _logger.error(
                f"Failed to parse file: '{self.usdb_path}'. "
                "Redownload the song to continue."
            )
            return
        modifier(meta)
        meta.to_file(self.usdb_path.parent)


class DownloadStatus(Enum):
    """Status of song in download queue."""

    NONE = enum.auto()
    PENDING = enum.auto()
    DOWNLOADING = enum.auto()
    FAILED = enum.auto()

    def __str__(self) -> str:
        match self:
            case DownloadStatus.NONE:
                return ""
            case DownloadStatus.PENDING:
                return "Pending"
            case DownloadStatus.DOWNLOADING:
                return "Downloading"
            case DownloadStatus.FAILED:
                return "Failed"
            case _ as unreachable:
                assert_never(unreachable)

    def can_be_downloaded(self) -> bool:
        return self in (DownloadStatus.NONE, DownloadStatus.FAILED)


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
