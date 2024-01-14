"""Database utilities."""

import enum
import sqlite3
import time
from pathlib import Path
from typing import Iterable

import attrs

from usdb_syncer import SongId, SyncMetaId, errors, settings
from usdb_syncer.utils import AppPaths

SCHEMA_VERSION = 1


class _SqlCache:
    _cache: dict[str, str] = {}

    @classmethod
    def get(cls, name: str) -> str:
        if (stmt := cls._cache.get(name)) is None:
            cls._cache[name] = stmt = AppPaths.sql.joinpath(name).read_text("utf8")
        return stmt


class _DbState:
    """Singleton for managing the global database connection."""

    _connection: sqlite3.Connection | None = None

    @classmethod
    def connect(cls, db_path: Path | str) -> None:
        cls._connection = sqlite3.connect(db_path, check_same_thread=False)
        _validate_schema(cls._connection)

    @classmethod
    def connection(cls) -> sqlite3.Connection:
        if cls._connection is None:
            raise errors.DatabaseError("Not connected to database!")
        return cls._connection

    @classmethod
    def close(cls) -> None:
        if _DbState._connection is not None:
            _DbState._connection.close()
            _DbState._connection = None


def _validate_schema(connection: sqlite3.Connection) -> None:
    meta_table = connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'meta'"
    ).fetchone()
    if meta_table is None:
        connection.executescript(_SqlCache.get("setup_script.sql"))
        connection.execute(
            "INSERT INTO meta (id, version, ctime) VALUES (1, ?, ?)",
            (SCHEMA_VERSION, time.time()),
        )
        connection.commit()
    else:
        row = connection.execute("SELECT version FROM meta").fetchone()
        if not row or row[0] != SCHEMA_VERSION:
            raise errors.UnknownSchemaError


def connect(db_path: Path | str) -> None:
    _DbState.connect(db_path)


def close() -> None:
    _DbState.close()


def commit() -> None:
    _DbState.connection().commit()


def rollback() -> None:
    _DbState.connection().rollback()


@attrs.define
class SearchBuilder:
    """Helper for building a where clause to find songs."""

    artists: list[str] = attrs.field(factory=list)
    titles: list[str] = attrs.field(factory=list)
    editions: list[str] = attrs.field(factory=list)
    languages: list[str] = attrs.field(factory=list)
    golden_notes: bool | None = None
    ratings: list[int] = attrs.field(factory=list)
    views: list[tuple[int, int | None]] = attrs.field(factory=list)

    def _where_clause(self) -> str:
        filters = (
            _in_values_clause("usdb_song.artist", self.artists),
            _in_values_clause("usdb_song.title", self.titles),
            _in_values_clause("usdb_song.edition", self.editions),
            _in_values_clause("usdb_song.language", self.languages),
            "usdb_song.golden_notes = ?" if self.golden_notes is not None else "",
            _in_values_clause("usdb_song.rating", self.ratings),
            _in_ranges_clause("usdb_song.views", self.views),
        )
        return " AND ".join(filter(None, filters))

    def parameters(self) -> tuple[str | int | bool, ...]:
        return (
            *self.artists,
            *self.titles,
            *self.editions,
            *self.languages,
            *([] if self.golden_notes is None else [self.golden_notes]),
            *self.ratings,
            *(val for views in self.views for val in views if val is not None),
        )

    def statement(self) -> str:
        where = self._where_clause()
        where = f" WHERE {where}" if where else ""
        return f"SELECT usdb_song.song_id FROM usdb_song{where}"


def _in_values_clause(attribute: str, values: list) -> str:
    return f"{attribute} IN ({', '.join('?'*len(values))})" if values else ""


def _in_ranges_clause(attribute: str, values: list[tuple[int, int | None]]) -> str:
    return " OR ".join(
        f"{attribute} >= ?{'' if val[1] is None else f' AND {attribute} < ?'}"
        for val in values
    )


### UsdbSong


def get_usdb_song(song_id: SongId) -> tuple | None:
    stmt = f"{_SqlCache.get('select_usdb_song.sql')} WHERE usdb_song.song_id = :song_id"
    params = {"folder": settings.get_song_dir().as_posix(), "song_id": song_id}
    return _DbState.connection().execute(stmt, params).fetchone()


def delete_usdb_song(song_id: SongId) -> None:
    _DbState.connection().execute("DELETE FROM usdb_song WHERE song_id = ?", (song_id,))


@attrs.define(frozen=True, slots=False)
class UsdbSongParams:
    """Parameters for inserting or updating a USDB song."""

    song_id: SongId
    artist: str
    title: str
    language: str
    edition: str
    golden_notes: bool
    rating: int
    views: int


def upsert_usdb_song(params: UsdbSongParams) -> None:
    stmt = _SqlCache.get("upsert_usdb_song.sql")
    _DbState.connection().execute(stmt, params.__dict__)


def upsert_usdb_songs(params: Iterable[UsdbSongParams]) -> None:
    stmt = _SqlCache.get("upsert_usdb_song.sql")
    _DbState.connection().executemany(stmt, (p.__dict__ for p in params))


def usdb_song_count() -> int:
    return _DbState.connection().execute("SELECT count(*) FROM usdb_song").fetchone()[0]


def max_usdb_song_id() -> SongId:
    row = _DbState.connection().execute("SELECT max(song_id) FROM usdb_song").fetchone()
    return SongId(row[0] or 0)


def delete_all_usdb_songs() -> None:
    _DbState.connection().execute("DELETE FROM usdb_song")


def all_local_usdb_songs() -> Iterable[SongId]:
    stmt = "SELECT DISTINCT song_id FROM sync_meta"
    return (SongId(i) for i in _DbState.connection().execute(stmt))


def search_usdb_songs(search: SearchBuilder) -> Iterable[SongId]:
    return (
        SongId(r[0])
        for r in _DbState.connection().execute(search.statement(), search.parameters())
    )


def usdb_song_artists() -> list[tuple[str, int]]:
    stmt = "SELECT artist, COUNT(*) FROM usdb_song GROUP BY artist ORDER BY artist"
    return _DbState.connection().execute(stmt).fetchall()


def usdb_song_titles() -> list[tuple[str, int]]:
    stmt = "SELECT title, COUNT(*) FROM usdb_song GROUP BY title ORDER BY title"
    return _DbState.connection().execute(stmt).fetchall()


def usdb_song_editions() -> list[tuple[str, int]]:
    stmt = "SELECT edition, COUNT(*) FROM usdb_song GROUP BY edition ORDER BY edition"
    return _DbState.connection().execute(stmt).fetchall()


def usdb_song_languages() -> list[tuple[str, int]]:
    stmt = (
        "SELECT language, COUNT(*) FROM usdb_song GROUP BY language ORDER BY language"
    )
    return _DbState.connection().execute(stmt).fetchall()


### SyncMeta


def get_sync_metas(folder: Path) -> list[tuple]:
    stmt = _SqlCache.get("select_sync_meta.sql")
    params = {"folder": folder.as_posix()}
    return _DbState.connection().execute(stmt, params).fetchall()


@attrs.define(frozen=True, slots=False)
class SyncMetaParams:
    """Parameters for inserting or updating a sync meta."""

    sync_meta_id: SyncMetaId
    song_id: SongId
    path: str
    mtime: float
    meta_tags: str
    pinned: bool


def upsert_sync_meta(params: SyncMetaParams) -> None:
    stmt = _SqlCache.get("upsert_sync_meta.sql")
    _DbState.connection().execute(stmt, params.__dict__)


def upsert_sync_metas(params: Iterable[SyncMetaParams]) -> None:
    stmt = _SqlCache.get("upsert_sync_meta.sql")
    _DbState.connection().executemany(stmt, (p.__dict__ for p in params))


def delete_sync_meta(sync_meta_id: SyncMetaId) -> None:
    _DbState.connection().execute(
        "DELETE FROM sync_meta WHERE sync_meta_id = ?", (sync_meta_id,)
    )


def delete_sync_metas(ids: tuple[SyncMetaId, ...]) -> None:
    id_str = ", ".join("?" for _ in range(len(ids)))
    _DbState.connection().execute(
        f"DELETE FROM sync_meta WHERE sync_meta_id IN ({id_str})", ids
    )


### ResourceFile


class ResourceFileKind(str, enum.Enum):
    """Kinds of resource files."""

    TXT = "txt"
    AUDIO = "audio"
    VIDEO = "video"
    COVER = "cover"
    BACKGROUND = "background"


@attrs.define(frozen=True, slots=False)
class ResourceFileParams:
    """Parameters for inserting or updating a resource file."""

    sync_meta_id: SyncMetaId
    kind: ResourceFileKind
    fname: str
    mtime: float
    resource: str


def delete_resource_files(ids: Iterable[tuple[SyncMetaId, ResourceFileKind]]) -> None:
    params = tuple(param for i, k in ids for param in (int(i), k.value))
    tuples = ", ".join("(?, ?)" for _ in range(len(params) // 2))
    _DbState.connection().execute(
        f"DELETE FROM resource_file WHERE (sync_meta_id, kind) IN ({tuples})", params
    )


def upsert_resource_files(params: Iterable[ResourceFileParams]) -> None:
    stmt = _SqlCache.get("upsert_resource_file.sql")
    _DbState.connection().executemany(stmt, (p.__dict__ for p in params))
