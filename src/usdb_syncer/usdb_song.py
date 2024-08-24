"""Meta data about a song that USDB shows in the result list."""

from __future__ import annotations

from json import JSONEncoder
from typing import Any, Iterable, Type

import attrs

from usdb_syncer import SongId, db
from usdb_syncer.constants import UsdbStrings
from usdb_syncer.db import DownloadStatus
from usdb_syncer.sync_meta import SyncMeta


@attrs.define(kw_only=True)
class UsdbSong:
    """Meta data about a song that USDB shows in the result list."""

    song_id: SongId
    artist: str
    title: str
    genre: str
    year: int | None = None
    language: str
    creator: str
    edition: str
    golden_notes: bool
    rating: int
    views: int
    sample_url: str
    # not in USDB song list
    tags: str = ""
    # internal
    sync_meta: SyncMeta | None = None
    status: DownloadStatus = DownloadStatus.NONE
    is_playing: bool = False

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
        genre: str,
        year: str,
        language: str,
        creator: str,
        edition: str,
        golden_notes: str,
        rating: str,
        views: str,
        sample_url: str,
    ) -> UsdbSong:
        return cls(
            song_id=SongId.parse(song_id),
            artist=artist,
            title=title,
            genre=genre,
            year=int(year) if len(year) == 4 and year.isdigit() else None,
            language=language,
            creator=creator,
            edition=edition,
            golden_notes=golden_notes == strings.YES,
            rating=rating.count("star.png"),
            views=int(views),
            sample_url=sample_url,
        )

    @classmethod
    def from_db_row(cls, song_id: SongId, row: tuple) -> UsdbSong:
        assert len(row) == 36
        return cls(
            song_id=song_id,
            artist=row[1],
            title=row[2],
            language=row[3],
            edition=row[4],
            golden_notes=bool(row[5]),  # else would be 0/1 instead of False/True
            rating=row[6],
            views=row[7],
            sample_url=row[8],
            year=row[9],
            genre=row[10],
            creator=row[11],
            tags=row[12],
            status=DownloadStatus(row[13]),
            is_playing=bool(row[14]),
            sync_meta=None if row[15] is None else SyncMeta.from_db_row(row[15:]),
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

    def remove_sync_meta(self) -> None:
        if self.sync_meta:
            self.sync_meta.delete()
            self.sync_meta = None
            _UsdbSongCache.update(self)

    @classmethod
    def delete_all(cls) -> None:
        db.delete_all_usdb_songs()
        _UsdbSongCache.clear()

    def upsert(self) -> None:
        db.upsert_usdb_song(self.db_params())
        db.upsert_usdb_songs_languages([(self.song_id, self.languages())])
        db.upsert_usdb_songs_genres([(self.song_id, self.genres())])
        db.upsert_usdb_songs_creators([(self.song_id, self.creators())])
        if self.sync_meta:
            self.sync_meta.upsert()
        _UsdbSongCache.update(self)

    @classmethod
    def upsert_many(cls, songs: list[UsdbSong]) -> None:
        db.upsert_usdb_songs(song.db_params() for song in songs)
        db.upsert_usdb_songs_languages([(s.song_id, s.languages()) for s in songs])
        db.upsert_usdb_songs_genres([(s.song_id, s.genres()) for s in songs])
        db.upsert_usdb_songs_creators([(s.song_id, s.creators()) for s in songs])
        SyncMeta.upsert_many([song.sync_meta for song in songs if song.sync_meta])
        for song in songs:
            _UsdbSongCache.update(song)

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
            sample_url=self.sample_url,
            year=self.year,
            genre=self.genre,
            creator=self.creator,
            tags=self.tags,
            status=self.status,
            is_playing=self.is_playing,
        )

    def is_local(self) -> bool:
        return self.sync_meta is not None and self.sync_meta.path is not None

    def is_pinned(self) -> bool:
        return self.sync_meta is not None and self.sync_meta.pinned

    def languages(self) -> Iterable[str]:
        return (l for lang in self.language.split(",") if (l := lang.strip()))

    def genres(self) -> Iterable[str]:
        return (l for lang in self.genre.split(",") if (l := lang.strip()))

    def creators(self) -> Iterable[str]:
        return (l for lang in self.creator.split(",") if (l := lang.strip()))

    @classmethod
    def clear_cache(cls) -> None:
        _UsdbSongCache.clear()


class UsdbSongEncoder(JSONEncoder):
    """Custom JSON encoder"""

    def default(self, o: Any) -> Any:
        if isinstance(o, UsdbSong):
            fields = attrs.fields(UsdbSong)
            filt = attrs.filters.exclude(
                fields.status, fields.sync_meta, fields.is_playing
            )
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
