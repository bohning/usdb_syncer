"""High-level routines for USDB and local songs."""

import json
import os
from collections.abc import Generator
from importlib import resources
from importlib.abc import Traversable
from pathlib import Path

import requests
import send2trash
from requests import Session

from usdb_syncer import (
    SongId,
    SyncMetaId,
    data,
    db,
    errors,
    events,
    settings,
    song_txt,
    utils,
)
from usdb_syncer.logger import error_logger, logger
from usdb_syncer.song_loader import DownloadManager
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.usdb_scraper import get_usdb_available_songs
from usdb_syncer.usdb_song import UsdbSong, UsdbSongEncoder
from usdb_syncer.utils import AppPaths


def load_available_songs(force_reload: bool, session: Session | None = None) -> None:
    if force_reload:
        max_skip_id = SongId(0)
        UsdbSong.delete_all()
    elif (max_skip_id := db.max_usdb_song_id()) == 0 and (songs := load_cached_songs()):
        UsdbSong.upsert_many(songs)
        max_skip_id = db.max_usdb_song_id()
    try:
        songs = get_usdb_available_songs(max_skip_id, session=session)
    except errors.UsdbLoginError:
        logger.debug("Skipping fetching new songs as there is no login.")
        return
    except requests.exceptions.ConnectionError:
        logger.debug("", exc_info=True)
        logger.error("Failed to fetch new songs; check network connection.")
        return
    if songs:
        UsdbSong.upsert_many(songs)
        _download_subscribed_songs(songs)


def _download_subscribed_songs(songs: list[UsdbSong]) -> None:
    if not settings.ffmpeg_is_available():
        return
    subscribed = set(db.SavedSearch.get_subscribed_song_ids())
    to_download = []
    if subscribed:
        for song in songs:
            if song.song_id in subscribed:
                song.status = db.DownloadStatus.PENDING
                UsdbSong.upsert(song)
                to_download.append(song)
    if to_download:
        events.DownloadsRequested(len(to_download)).post()
        DownloadManager.download(to_download)


def load_cached_songs() -> list[UsdbSong] | None:
    if AppPaths.song_list.exists():
        path: Path | Traversable = AppPaths.song_list
    elif (resource := resources.files(data).joinpath("song_list.json")).is_file():
        path = resource
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


def _iterate_usdb_files_in_folder_recursively(
    folder: Path,
) -> Generator[Path, None, None]:
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".usdb") and not file.startswith("."):
                yield Path(root) / file


def synchronize_sync_meta_folder(folder: Path) -> None:
    db_metas = {m.sync_meta_id: m for m in SyncMeta.get_in_folder(folder)}
    song_ids = set(db.all_song_ids())
    to_upsert: list[SyncMeta] = []
    found_metas: set[SyncMetaId] = set()

    for path in _iterate_usdb_files_in_folder_recursively(folder=folder):
        if meta_id := SyncMetaId.from_path(path):
            if meta_id in found_metas:
                send2trash.send2trash(path)
                logger.warning(f"Trashed duplicated meta file: '{path}'")
                continue
            found_metas.add(meta_id)

        meta = None if meta_id is None else db_metas.get(meta_id)

        if meta_id is not None and meta and meta.mtime == utils.get_mtime(path):
            # file is unchanged
            if not utils.compare_unicode_paths(path, meta.path):
                meta.path = path
                to_upsert.append(meta)
                logger.info(f"Meta file was moved: '{path}'.")
            continue

        if meta := SyncMeta.try_from_file(path):
            if meta.song_id in song_ids:
                # file was changed and maybe moved
                to_upsert.append(meta)
                if meta.sync_meta_id in db_metas:
                    logger.info(f"Updated meta file from disk: '{path}'.")
                else:
                    logger.info(f"New meta file found on disk: '{path}'.")
            else:
                logger.info(
                    f"{meta.song_id.usdb_detail_url()} no longer exists: '{path}'."
                )

    SyncMeta.delete_many(tuple(db_metas.keys() - found_metas))
    SyncMeta.upsert_many(to_upsert)


def find_local_songs(directory: Path) -> set[SongId]:
    matched_rows: set[SongId] = set()
    for path in directory.glob("**/*.txt"):
        if headers := try_parse_txt_headers(path):
            name = headers.artist_title_str()
            if matches := list(
                db.find_similar_usdb_songs(
                    utils.normalize(headers.artist), utils.normalize(headers.title)
                )
            ):
                plural = "es" if len(matches) > 1 else ""
                logger.info(f"{len(matches)} match{plural} for '{name}'.")
                matched_rows.update(matches)
            else:
                logger.warning(f"No matches for '{name}'.")
    return matched_rows


def try_parse_txt_headers(path: Path) -> song_txt.Headers | None:
    if lines := utils.read_file_head(path, 20):
        try:
            return song_txt.Headers.parse(lines, error_logger)
        except errors.HeadersParseError:
            return None
    return None
