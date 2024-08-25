"""Database utilities."""

from __future__ import annotations

import contextlib
import enum
import json
import os
import sqlite3
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Generator, Iterable, Iterator, assert_never, cast

import attrs
from more_itertools import batched

from usdb_syncer import SongId, SyncMetaId, errors, logger
from usdb_syncer.utils import AppPaths

SCHEMA_VERSION = 4

# https://www.sqlite.org/limits.html
_SQL_VARIABLES_LIMIT = 32766


_logger = logger.get_logger(__file__)


class _SqlCache:
    _cache: dict[str, str] = {}

    @classmethod
    def get(cls, name: str, cache: bool = True) -> str:
        if (stmt := cls._cache.get(name)) is None:
            stmt = AppPaths.sql.joinpath(name).read_text("utf8")
            if cache:
                cls._cache[name] = stmt
        return stmt


class _LocalConnection(threading.local):
    """A thread-local database connection."""

    connection: sqlite3.Connection | None = None


class _DbState:
    """Singleton for managing the global database connection."""

    _local: _LocalConnection = _LocalConnection()

    @classmethod
    def connect(cls, db_path: Path | str, trace: bool = False) -> None:
        if cls._local.connection:
            raise errors.DatabaseError("Already connected to database!")
        cls._local.connection = sqlite3.connect(
            db_path, check_same_thread=False, isolation_level=None
        )
        if trace:
            cls._local.connection.set_trace_callback(_logger.debug)
        _validate_schema(cls._local.connection)

    @classmethod
    def connection(cls) -> sqlite3.Connection:
        if cls._local.connection is None:
            raise errors.DatabaseError("Not connected to database!")
        return cls._local.connection

    @classmethod
    def close(cls) -> None:
        if _DbState._local.connection is not None:
            _DbState._local.connection.close()
            _DbState._local.connection = None


@contextlib.contextmanager
def transaction() -> Generator[None, None, None]:
    try:
        _DbState.connection().execute("BEGIN IMMEDIATE")
        yield None
    except Exception:  # pylint: disable=broad-except
        _DbState.connection().rollback()
        raise
    _DbState.connection().commit()


def _validate_schema(connection: sqlite3.Connection) -> None:
    meta_table = connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'meta'"
    ).fetchone()
    if meta_table is None:
        version = 0
    else:
        row = connection.execute("SELECT version FROM meta WHERE id = 1").fetchone()
        if not row or row[0] > SCHEMA_VERSION:
            raise errors.UnknownSchemaError
        version = row[0]
    for ver in range(version + 1, SCHEMA_VERSION + 1):
        connection.executescript(_SqlCache.get(f"{ver}_migration.sql", cache=False))
        _logger.debug(f"Database migrated to version {ver}.")
    if version < SCHEMA_VERSION:
        connection.execute(
            "INSERT INTO meta (id, version, ctime) VALUES (1, :version, :ctime) "
            "ON CONFLICT (id) DO UPDATE SET version = :version",
            {"version": SCHEMA_VERSION, "ctime": int(time.time() * 1_000_000)},
        )
    connection.executescript(_SqlCache.get("setup_session_script.sql", cache=False))


def connect(db_path: Path | str) -> None:
    _DbState.connect(db_path, trace=bool(os.environ.get("TRACESQL")))


def close() -> None:
    _DbState.close()


@contextlib.contextmanager
def managed_connection(db_path: Path | str) -> Generator[None, None, None]:
    try:
        _DbState.connect(db_path)
        yield None
    finally:
        _DbState.close()


class DownloadStatus(enum.IntEnum):
    """Status of song in download queue."""

    NONE = 0
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


class SongOrder(enum.Enum):
    """Attributes songs can be sorted by."""

    NONE = 0
    SAMPLE_URL = enum.auto()
    SONG_ID = enum.auto()
    ARTIST = enum.auto()
    TITLE = enum.auto()
    EDITION = enum.auto()
    LANGUAGE = enum.auto()
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
    STATUS = enum.auto()

    def sql(self) -> str | None:
        match self:
            case SongOrder.NONE:
                return None
            case SongOrder.SAMPLE_URL:
                return (
                    "CASE WHEN session_usdb_song.is_playing = true THEN 0"
                    " WHEN audio.sync_meta_id IS NOT NULL THEN 1"
                    " WHEN usdb_song.sample_url != '' THEN 2 ELSE 3 END"
                )
            case SongOrder.SONG_ID:
                return "usdb_song.song_id"
            case SongOrder.ARTIST:
                return "usdb_song.artist"
            case SongOrder.TITLE:
                return "usdb_song.title"
            case SongOrder.EDITION:
                return "usdb_song.edition"
            case SongOrder.LANGUAGE:
                return "usdb_song.language"
            case SongOrder.GOLDEN_NOTES:
                return "usdb_song.golden_notes"
            case SongOrder.RATING:
                return "usdb_song.rating"
            case SongOrder.VIEWS:
                return "usdb_song.views"
            case SongOrder.YEAR:
                return "usdb_song.year"
            case SongOrder.GENRE:
                return "usdb_song.genre"
            case SongOrder.CREATOR:
                return "usdb_song.creator"
            case SongOrder.TAGS:
                return "usdb_song.tags"
            case SongOrder.PINNED:
                return "sync_meta.pinned"
            case SongOrder.TXT:
                return "txt.sync_meta_id IS NULL"
            case SongOrder.AUDIO:
                return "audio.sync_meta_id IS NULL"
            case SongOrder.VIDEO:
                return "video.sync_meta_id IS NULL"
            case SongOrder.COVER:
                return "cover.sync_meta_id IS NULL"
            case SongOrder.BACKGROUND:
                return "background.sync_meta_id IS NULL"
            case SongOrder.STATUS:
                return (
                    "coalesce(session_usdb_song.status, sync_meta.mtime,"
                    # max integer in SQLite
                    " 9223372036854775807)"
                )


@attrs.define
class SearchBuilder:
    """Helper for building a where clause to find songs."""

    order: SongOrder = SongOrder.NONE
    descending: bool = False
    text: str = ""
    artists: list[str] = attrs.field(factory=list)
    titles: list[str] = attrs.field(factory=list)
    editions: list[str] = attrs.field(factory=list)
    ratings: list[int] = attrs.field(factory=list)
    statuses: list[DownloadStatus] = attrs.field(factory=list)
    languages: list[str] = attrs.field(factory=list)
    views: list[tuple[int, int | None]] = attrs.field(factory=list)
    years: list[int] = attrs.field(factory=list)
    genres: list[str] = attrs.field(factory=list)
    creators: list[str] = attrs.field(factory=list)
    golden_notes: bool | None = None
    downloaded: bool | None = None

    def filters(self) -> Iterator[str]:
        if _fts5_phrases(self.text):
            yield (
                "usdb_song.song_id IN (SELECT rowid FROM fts_usdb_song WHERE"
                " fts_usdb_song MATCH ?)"
            )
        for vals, col in (
            (self.artists, "usdb_song.artist"),
            (self.titles, "usdb_song.title"),
            (self.editions, "usdb_song.edition"),
            (self.ratings, "usdb_song.rating"),
            (self.years, "usdb_song.year"),
            (self.statuses, "session_usdb_song.status"),
        ):
            if vals:
                yield _in_values_clause(col, cast(list, vals))
        if self.languages:
            yield (
                "usdb_song.song_id IN (SELECT song_id FROM usdb_song_language WHERE"
                f" {_in_values_clause('language', self.languages)})"
            )
        if self.genres:
            yield (
                "usdb_song.song_id IN (SELECT song_id FROM usdb_song_genre WHERE"
                f" {_in_values_clause('genre', self.genres)})"
            )
        if self.creators:
            yield (
                "usdb_song.song_id IN (SELECT song_id FROM usdb_song_creator WHERE"
                f" {_in_values_clause('creator', self.creators)})"
            )
        if self.views:
            yield _in_ranges_clause("usdb_song.views", self.views)
        if self.golden_notes is not None:
            yield "usdb_song.golden_notes = ?"
        if self.downloaded is not None:
            yield f"sync_meta.sync_meta_id IS {'NOT ' if self.downloaded else ''}NULL"

    def _where_clause(self) -> str:
        where = " AND ".join(self.filters())
        return f" WHERE {where}" if where else ""

    def _order_by_clause(self) -> str:
        if sql := self.order.sql():
            return f" ORDER BY {sql} {'DESC' if self.descending else 'ASC'}"
        return ""

    def parameters(self) -> Iterator[str | int | bool]:
        if text := _fts5_phrases(self.text):
            yield text
        yield from self.artists
        yield from self.titles
        yield from self.editions
        yield from self.ratings
        yield from self.years
        yield from self.statuses
        yield from self.languages
        yield from self.genres
        yield from self.creators
        for min_views, max_views in self.views:
            yield min_views
            if max_views is not None:
                yield max_views
        if self.golden_notes is not None:
            yield self.golden_notes

    def statement(self) -> str:
        select_from = _SqlCache.get("select_song_id.sql")
        where = self._where_clause()
        order_by = self._order_by_clause()
        return f"{select_from}{where}{order_by}"

    def to_json(self) -> str:
        return json.dumps(self, cls=_SearchEnoder)

    @classmethod
    def from_json(cls, json_str: str) -> SearchBuilder | None:
        fields = attrs.fields(cls)
        try:
            dct = json.loads(json_str)
            dct[fields.order.name] = SongOrder(dct[fields.order.name])
            dct[fields.statuses.name] = [
                DownloadStatus(s) for s in dct[fields.statuses.name]
            ]
            dct[fields.views.name] = [tuple(l) for l in dct[fields.views.name]]
            return cls(**dct)
        except (
            json.decoder.JSONDecodeError,
            UnicodeDecodeError,
            TypeError,
            KeyError,
            ValueError,
        ):
            _logger.debug(traceback.format_exc())
        return None


class _SearchEnoder(json.JSONEncoder):
    """Custom encoder for a search."""

    def default(self, o: Any) -> Any:
        if isinstance(o, SearchBuilder):
            return attrs.asdict(o, recurse=False)
        if isinstance(o, enum.Enum):
            return o.value
        return super().default(o)


@attrs.define
class SavedSearch:
    """A search saved to the database by the user."""

    name: str
    search: SearchBuilder
    is_default: bool = False
    subscribed: bool = False

    def insert(self) -> None:
        self.name = (
            _DbState.connection()
            .execute(
                _SqlCache.get("insert_saved_search.sql"),
                {
                    "name": self.name,
                    "search": self.search.to_json(),
                    "is_default": self.is_default,
                    "subscribed": self.subscribed,
                },
            )
            .fetchone()
        )[0]

    def delete(self) -> None:
        _DbState.connection().execute(
            "DELETE FROM saved_search WHERE name = ?", (self.name,)
        )

    @classmethod
    def get(cls, name: str) -> SavedSearch | None:
        stmt = (
            "SELECT name, search, is_default, subscribed FROM saved_search"
            " WHERE name = ?"
        )
        row = _DbState.connection().execute(stmt, (name,)).fetchone()
        if row and (search := cls._validate_saved_search_row(*row)):
            return search
        return None

    @classmethod
    def get_default(cls) -> SavedSearch | None:
        stmt = (
            "SELECT name, search, is_default, subscribed FROM saved_search"
            " WHERE is_default = true"
        )
        row = _DbState.connection().execute(stmt).fetchone()
        if row and (search := cls._validate_saved_search_row(*row)):
            return search
        return None

    def update(self, new_name: str | None = None) -> None:
        self.name = (
            _DbState.connection()
            .execute(
                _SqlCache.get("update_saved_search.sql"),
                {
                    "old_name": self.name,
                    "new_name": new_name or self.name,
                    "search": self.search.to_json(),
                    "is_default": self.is_default,
                    "subscribed": self.subscribed,
                },
            )
            .fetchone()
        )[0]

    @classmethod
    def load_saved_searches(
        cls, subscribed_only: bool = False
    ) -> Iterable[SavedSearch]:
        stmt = (
            "SELECT name, search, is_default, subscribed FROM saved_search"
            f"{' WHERE subscribed' if subscribed_only else ''} ORDER BY name"
        )
        return (
            search
            for row in _DbState.connection().execute(stmt).fetchall()
            if (search := cls._validate_saved_search_row(*row))
        )

    @classmethod
    def _validate_saved_search_row(
        cls, name: str, json_str: str, is_default: int, subscribed: int
    ) -> SavedSearch | None:
        if search := SearchBuilder.from_json(json_str):
            return cls(name, search, bool(is_default), bool(subscribed))
        _DbState.connection().execute(
            "DELETE FROM saved_search WHERE name = ?", (name,)
        )
        _logger.warning(f"Dropped invalid saved search '{name}'.")
        return None

    @classmethod
    def get_subscribed_song_ids(cls) -> Iterable[SongId]:
        if not (searches := list(cls.load_saved_searches(subscribed_only=True))):
            return []
        for search in searches:
            search.search.order = SongOrder.NONE
        stmt = "\nUNION\n".join(s.search.statement() for s in searches)
        params = tuple(p for s in searches for p in s.search.parameters())
        return (SongId(r[0]) for r in _DbState.connection().execute(stmt, params))


def _in_values_clause(attribute: str, values: list) -> str:
    return f"{attribute} IN ({', '.join('?' * len(values))})"


def _in_ranges_clause(attribute: str, values: list[tuple[int, int | None]]) -> str:
    return " OR ".join(
        f"{attribute} >= ?{'' if val[1] is None else f' AND {attribute} < ?'}"
        for val in values
    )


def _fts5_phrases(text: str) -> str:
    """Turns each whitespace-separated word into an FTS5 prefix phrase."""
    return " ".join(f'"{s}"*' for s in text.replace('"', "").split(" ") if s)


def _fts5_start_phrase(text: str) -> str:
    """Turns the entire string into an FTS5 initial phrase."""
    return f'''^ "{text.replace('"', "")}"'''


### UsdbSong


def get_usdb_song(song_id: SongId) -> tuple | None:
    stmt = f"{_SqlCache.get('select_usdb_song.sql')} WHERE usdb_song.song_id = ?"
    return _DbState.connection().execute(stmt, (song_id,)).fetchone()


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
    sample_url: str
    year: int | None
    genre: str
    creator: str
    tags: str
    status: DownloadStatus
    is_playing: bool


def upsert_usdb_song(params: UsdbSongParams) -> None:
    stmt = _SqlCache.get("upsert_usdb_song.sql")
    _DbState.connection().execute(stmt, params.__dict__)
    stmt = _SqlCache.get("upsert_session_usdb_song.sql")
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
    return (SongId(r[0]) for r in _DbState.connection().execute(stmt))


def all_song_ids() -> Iterable[SongId]:
    rows = _DbState.connection().execute("SELECT song_id FROM usdb_song")
    return (SongId(r[0]) for r in rows)


def search_usdb_songs(search: SearchBuilder) -> Iterable[SongId]:
    rows = _DbState.connection().execute(search.statement(), tuple(search.parameters()))
    return (SongId(r[0]) for r in rows)


def find_similar_usdb_songs(artist: str, title: str) -> Iterable[SongId]:
    stmt = "SELECT rowid FROM fts_usdb_song WHERE artist MATCH ? AND title MATCH ?"
    params = (_fts5_start_phrase(artist), _fts5_start_phrase(title))
    return (SongId(r[0]) for r in _DbState.connection().execute(stmt, params))


### song filters


def upsert_usdb_songs_languages(params: list[tuple[SongId, Iterable[str]]]) -> None:
    _DbState.connection().execute(
        f"DELETE FROM usdb_song_language WHERE {_in_values_clause('song_id', params)}",
        tuple(t[0] for t in params),
    )
    _DbState.connection().executemany(
        "INSERT INTO usdb_song_language (song_id, language) VALUES (?, ?)",
        ((song_id, lang) for song_id, langs in params for lang in langs),
    )


def upsert_usdb_songs_genres(params: list[tuple[SongId, Iterable[str]]]) -> None:
    _DbState.connection().execute(
        f"DELETE FROM usdb_song_genre WHERE {_in_values_clause('song_id', params)}",
        tuple(t[0] for t in params),
    )
    _DbState.connection().executemany(
        "INSERT INTO usdb_song_genre (song_id, genre) VALUES (?, ?)",
        ((song_id, lang) for song_id, langs in params for lang in langs),
    )


def upsert_usdb_songs_creators(params: list[tuple[SongId, Iterable[str]]]) -> None:
    _DbState.connection().execute(
        f"DELETE FROM usdb_song_creator WHERE {_in_values_clause('song_id', params)}",
        tuple(t[0] for t in params),
    )
    _DbState.connection().executemany(
        "INSERT INTO usdb_song_creator (song_id, creator) VALUES (?, ?)",
        ((song_id, lang) for song_id, langs in params for lang in langs),
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
        "SELECT language, COUNT(*) FROM usdb_song_language GROUP BY language ORDER BY"
        " language"
    )
    return _DbState.connection().execute(stmt).fetchall()


def usdb_song_years() -> list[tuple[int, int]]:
    stmt = (
        "SELECT year, COUNT(*) FROM usdb_song WHERE year IS NOT NULL "
        "GROUP BY year ORDER BY year"
    )
    return _DbState.connection().execute(stmt).fetchall()


def usdb_song_genres() -> list[tuple[str, int]]:
    stmt = "SELECT genre, COUNT(*) FROM usdb_song_genre GROUP BY genre ORDER BY genre"
    return _DbState.connection().execute(stmt).fetchall()


def usdb_song_creators() -> list[tuple[str, int]]:
    stmt = "SELECT creator, COUNT(*) FROM usdb_song_creator GROUP BY creator ORDER BY creator"
    return _DbState.connection().execute(stmt).fetchall()


def search_usdb_song_artists(search: str) -> set[str]:
    stmt = "SELECT artist FROM fts_usdb_song WHERE artist MATCH ?"
    rows = _DbState.connection().execute(stmt, (_fts5_phrases(search),)).fetchall()
    return set(row[0] for row in rows)


def search_usdb_song_titles(search: str) -> set[str]:
    stmt = "SELECT title FROM fts_usdb_song WHERE title MATCH ?"
    rows = _DbState.connection().execute(stmt, (_fts5_phrases(search),)).fetchall()
    return set(row[0] for row in rows)


def search_usdb_song_editions(search: str) -> set[str]:
    stmt = "SELECT edition FROM fts_usdb_song WHERE edition MATCH ?"
    rows = _DbState.connection().execute(stmt, (_fts5_phrases(search),)).fetchall()
    return set(row[0] for row in rows)


def search_usdb_song_languages(search: str) -> set[str]:
    stmt = "SELECT language FROM fts_usdb_song WHERE language MATCH ?"
    rows = _DbState.connection().execute(stmt, (_fts5_phrases(search),)).fetchall()
    return set(row[0] for row in rows)


def search_usdb_song_years(search: str) -> set[int]:
    stmt = "SELECT year FROM fts_usdb_song WHERE year MATCH ?"
    rows = _DbState.connection().execute(stmt, (_fts5_phrases(search),)).fetchall()
    return set(row[0] for row in rows)


def search_usdb_song_genres(search: str) -> set[str]:
    stmt = "SELECT genre FROM fts_usdb_song WHERE genre MATCH ?"
    rows = _DbState.connection().execute(stmt, (_fts5_phrases(search),)).fetchall()
    return set(row[0] for row in rows)


def search_usdb_song_creators(search: str) -> set[str]:
    stmt = "SELECT creator FROM fts_usdb_song WHERE creator MATCH ?"
    rows = _DbState.connection().execute(stmt, (_fts5_phrases(search),)).fetchall()
    return set(row[0] for row in rows)


### SyncMeta


def get_in_folder(folder: Path) -> list[tuple]:
    stmt = f"{_SqlCache.get('select_sync_meta.sql')} WHERE path GLOB ? || '/*'"
    return _DbState.connection().execute(stmt, (folder.as_posix(),)).fetchall()


def reset_active_sync_metas(folder: Path) -> None:
    _DbState.connection().execute("DELETE FROM active_sync_meta")
    params = {"folder": folder.as_posix()}
    _DbState.connection().execute(_SqlCache.get("insert_active_sync_metas.sql"), params)


def update_active_sync_metas(folder: Path, song_id: SongId) -> None:
    _DbState.connection().execute(
        "DELETE FROM active_sync_meta WHERE song_id = ?", (song_id,)
    )
    params = {"folder": folder.as_posix(), "song_id": song_id}
    _DbState.connection().execute(_SqlCache.get("insert_active_sync_meta.sql"), params)


@attrs.define(frozen=True, slots=False)
class SyncMetaParams:
    """Parameters for inserting or updating a sync meta."""

    sync_meta_id: SyncMetaId
    song_id: SongId
    path: str
    mtime: int
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
    for batch in batched(ids, _SQL_VARIABLES_LIMIT):
        id_str = ", ".join("?" for _ in range(len(batch)))
        _DbState.connection().execute(
            f"DELETE FROM sync_meta WHERE sync_meta_id IN ({id_str})", batch
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
    mtime: int
    resource: str


def delete_resource_files(ids: Iterable[tuple[SyncMetaId, ResourceFileKind]]) -> None:
    for batch in batched(ids, _SQL_VARIABLES_LIMIT // 2):
        params = tuple(param for i, k in batch for param in (int(i), k.value))
        tuples = ", ".join("(?, ?)" for _ in range(len(params) // 2))
        _DbState.connection().execute(
            f"DELETE FROM resource_file WHERE (sync_meta_id, kind) IN ({tuples})",
            params,
        )


def upsert_resource_files(params: Iterable[ResourceFileParams]) -> None:
    stmt = _SqlCache.get("upsert_resource_file.sql")
    _DbState.connection().executemany(stmt, (p.__dict__ for p in params))
