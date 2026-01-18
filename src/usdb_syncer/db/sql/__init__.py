"""Data directory for SQL scripts."""

from __future__ import annotations

import enum
import functools
from importlib import resources


class Sql(enum.Enum):
    """Utility class to read and cache SQL files."""

    INSERT_ACTIVE_SYNC_META = "insert_active_sync_meta.sql"
    INSERT_ACTIVE_SYNC_METAS = "insert_active_sync_metas.sql"
    SELECT_SONG_ID = "select_song_id.sql"
    SELECT_SYNC_META = "select_sync_meta.sql"
    SELECT_UNIQUE_SEARCH_NAME = "select_unique_search_name.sql"
    SELECT_USDB_SONG = "select_usdb_song.sql"
    SETUP_SESSION_SCRIPT = "setup_session_script.sql"
    UPSERT_CUSTOM_META_DATA = "upsert_custom_meta_data.sql"
    UPSERT_RESOURCE = "upsert_resource.sql"
    UPSERT_SYNC_META = "upsert_sync_meta.sql"
    UPSERT_USDB_SONG = "upsert_usdb_song.sql"
    UPSERT_USDB_SONG_PLAYING = "upsert_usdb_song_playing.sql"
    UPSERT_USDB_SONG_STATUS = "upsert_usdb_song_status.sql"

    # size is limited by number of enum variants, so lru checks are redundant
    @functools.lru_cache(maxsize=None)
    def text(self) -> str:
        return self.text_uncached()

    def text_uncached(self) -> str:
        return resources.files(__package__).joinpath(self.value).read_text("utf8")

    @staticmethod
    def migration_text(version: int) -> str:
        return (
            resources.files(__package__)
            .joinpath(f"{version}_migration.sql")
            .read_text("utf8")
        )
