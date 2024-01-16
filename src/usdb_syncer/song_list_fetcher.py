"""Runnable for getting the available songs from USDB or the local cache."""

import json
from pathlib import Path

from requests import Session

from usdb_syncer import SongId, SyncMetaId, db, errors, utils
from usdb_syncer.logger import get_logger
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.usdb_scraper import get_usdb_available_songs
from usdb_syncer.usdb_song import UsdbSong, UsdbSongEncoder
from usdb_syncer.utils import AppPaths

_logger = get_logger(__file__)


def load_available_songs(force_reload: bool, session: Session | None = None) -> None:
    if force_reload:
        max_skip_id = SongId(0)
        db.delete_all_usdb_songs()
    elif (max_skip_id := db.max_usdb_song_id()) == 0 and (songs := load_cached_songs()):
        UsdbSong.upsert_many(songs)
        max_skip_id = db.max_usdb_song_id()
    try:
        songs = get_usdb_available_songs(max_skip_id, session=session)
    except errors.UsdbLoginError:
        _logger.debug("Skipping fetching new songs as there is no login.")
    else:
        if songs:
            UsdbSong.upsert_many(songs)
    finally:
        db.rollback()


def load_cached_songs() -> list[UsdbSong] | None:
    if AppPaths.song_list.exists():
        path = AppPaths.song_list
    elif AppPaths.fallback_song_list.exists():
        path = AppPaths.fallback_song_list
    else:
        return None
    with path.open(encoding="utf8") as file:
        try:
            return json.load(file, object_hook=UsdbSong.from_json)
        except (json.decoder.JSONDecodeError, TypeError, KeyError):
            return None


def dump_available_songs(songs: list[UsdbSong], target: Path | None = None) -> None:
    with (target or AppPaths.song_list).open("w", encoding="utf8") as file:
        json.dump(songs, file, cls=UsdbSongEncoder)


# def find_local_files() -> dict[SongId, LocalFiles]:
#     return {
#         meta.song_id: LocalFiles.from_sync_meta(path, meta)
#         for path in settings.get_song_dir().glob("**/*.usdb")
#         if (meta := SyncMeta.try_from_file(path))
#     }


def synchronize_sync_meta_folder(folder: Path) -> None:
    db_metas = {m.sync_meta_id: m for m in SyncMeta.get_in_folder(folder)}
    to_upsert: list[SyncMeta] = []
    for path in folder.glob("**/*.usdb"):
        meta_id = SyncMetaId.from_path(path)
        meta = None if meta_id is None else db_metas.get(meta_id)
        if meta_id is not None and meta and meta.mtime == utils.get_mtime(path):
            del db_metas[meta_id]
            continue
        if meta := SyncMeta.try_from_file(path):
            to_upsert.append(meta)
            if meta.sync_meta_id in db_metas:
                del db_metas[meta.sync_meta_id]
                _logger.info(f"Updated meta file from disk: '{path}'.")
            else:
                _logger.info(f"New meta file found on disk: '{path}'.")
    SyncMeta.delete_many(tuple(db_metas.keys()), commit=False)
    SyncMeta.upsert_many(to_upsert, commit=False)
