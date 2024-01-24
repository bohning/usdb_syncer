"""Meta data about a song that USDB shows in the result list."""

from __future__ import annotations

import enum
from json import JSONEncoder
from typing import Any, Type, assert_never

import attrs

from usdb_syncer import SongId, db
from usdb_syncer.constants import UsdbStrings
from usdb_syncer.sync_meta import SyncMeta


class DownloadStatus(enum.Enum):
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

    def can_be_aborted(self) -> bool:
        return self in (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING)


@attrs.define(kw_only=True)
class UsdbSong:
    """Meta data about a song that USDB shows in the result list."""

    song_id: SongId
    artist: str
    title: str
    language: str
    edition: str
    golden_notes: bool
    rating: int
    views: int
    sync_meta: SyncMeta | None = None
    status: DownloadStatus = DownloadStatus.NONE

    @classmethod
    def from_json(cls, dct: dict[str, Any]) -> UsdbSong:
        dct["song_id"] = SongId(dct["song_id"])
        return cls(**dct)

    @classmethod
    def from_html(
        cls,
        strings: Type[UsdbStrings],
        *,
        song_id: str,
        artist: str,
        title: str,
        language: str,
        edition: str,
        golden_notes: str,
        rating: str,
        views: str,
    ) -> UsdbSong:
        return cls(
            song_id=SongId.parse(song_id),
            artist=artist,
            title=title,
            language=language,
            edition=edition,
            golden_notes=golden_notes == strings.YES,
            rating=rating.count("star.png"),
            views=int(views),
        )

    @classmethod
    def from_db_row(cls, song_id: SongId, row: tuple) -> UsdbSong:
        assert len(row) == 29
        return cls(
            song_id=song_id,
            artist=row[1],
            title=row[2],
            language=row[3],
            edition=row[4],
            golden_notes=row[5],
            rating=row[6],
            views=row[7],
            sync_meta=None if row[8] is None else SyncMeta.from_db_row(row[8:]),
        )

    @classmethod
    def get(cls, song_id: SongId) -> UsdbSong | None:
        if song := _UsdbSongCache.get(song_id):
            return song
        if row := db.get_usdb_song(song_id):
            song = UsdbSong.from_db_row(song_id, row)
            _UsdbSongCache.update(song)
            return song
        return None

    def delete(self) -> None:
        db.delete_usdb_song(self.song_id)
        _UsdbSongCache.remove(self.song_id)

    @classmethod
    def delete_all(cls) -> None:
        db.delete_all_usdb_songs()
        _UsdbSongCache.clear()

    def upsert(self) -> None:
        db.upsert_usdb_song(self.db_params())
        if self.sync_meta:
            self.sync_meta.upsert()
        _UsdbSongCache.remove(self.song_id)

    @classmethod
    def upsert_many(cls, songs: list[UsdbSong]) -> None:
        db.upsert_usdb_songs(song.db_params() for song in songs)
        SyncMeta.upsert_many([song.sync_meta for song in songs if song.sync_meta])
        for song in songs:
            _UsdbSongCache.remove(song.song_id)

    def db_params(self) -> db.UsdbSongParams:
        return db.UsdbSongParams(
            song_id=self.song_id,
            artist=self.artist,
            title=self.title,
            language=self.language,
            edition=self.edition,
            golden_notes=self.golden_notes,
            rating=self.rating,
            views=self.views,
        )

    def is_local(self) -> bool:
        return self.sync_meta is not None and self.sync_meta.path is not None

    def is_pinned(self) -> bool:
        return self.sync_meta is not None and self.sync_meta.pinned

    @classmethod
    def clear_cache(cls) -> None:
        _UsdbSongCache.clear()


class UsdbSongEncoder(JSONEncoder):
    """Custom JSON encoder"""

    def default(self, o: Any) -> Any:
        if isinstance(o, UsdbSong):
            fields = attrs.fields(UsdbSong)
            filt = attrs.filters.exclude(fields.status, fields.sync_meta)
            dct = attrs.asdict(o, recurse=False, filter=filt)
            return dct
        return super().default(o)


class _UsdbSongCache:
    """Cache for songs loaded from the DB."""

    _songs: dict[SongId, UsdbSong] = {}

    @classmethod
    def get(cls, song_id: SongId) -> UsdbSong | None:
        return cls._songs.get(song_id)

    @classmethod
    def update(cls, song: UsdbSong) -> None:
        cls._songs[song.song_id] = song

    @classmethod
    def remove(cls, song_id: SongId) -> None:
        if song_id in cls._songs:
            del cls._songs[song_id]

    @classmethod
    def clear(cls) -> None:
        cls._songs = {}
