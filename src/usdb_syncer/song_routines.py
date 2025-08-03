"""High-level routines for USDB and local songs."""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

import attrs
import requests
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
from usdb_syncer.usdb_scraper import get_updated_songs_from_usdb
from usdb_syncer.usdb_song import UsdbSong, UsdbSongEncoder
from usdb_syncer.utils import AppPaths


def load_available_songs_and_sync_meta(folder: Path, force_reload: bool) -> None:
    """Load available songs from USDB and synchronize the sync meta folder."""
    with db.transaction():
        result = load_available_songs(force_reload=force_reload)
        synchronize_sync_meta_folder(folder, not result.synced_with_usdb)
        SyncMeta.reset_active(folder)
    UsdbSong.clear_cache()
    initialize_auto_downloads(result.new_songs)


@attrs.define
class LoadSongsResult:
    """Result of loading songs from cache and USDB."""

    new_songs: set[SongId] = attrs.field(factory=set)
    synced_with_usdb: bool = False


def load_available_songs(
    force_reload: bool, session: Session | None = None
) -> LoadSongsResult:
    """True if USDB was queried successfully."""
    result = LoadSongsResult()
    if force_reload:
        last = db.LastUsdbUpdate.zero()
        UsdbSong.delete_all()
    elif (last := db.LastUsdbUpdate.get()).is_zero() and (songs := load_cached_songs()):
        UsdbSong.upsert_many(songs)
        result.new_songs.update((s.song_id for s in songs))
        last = db.LastUsdbUpdate.get()
    try:
        songs = get_updated_songs_from_usdb(last, session=session)
    except errors.UsdbLoginError:
        logger.debug("Skipping fetching new songs as there is no login.")
    except requests.exceptions.ConnectionError:
        logger.debug("", exc_info=True)
        logger.error("Failed to fetch new songs; check network connection.")
    else:
        result.synced_with_usdb = True
        if songs:
            UsdbSong.upsert_many(songs)
            result.new_songs.update((s.song_id for s in songs))
    return result


def initialize_auto_downloads(updates: set[SongId]) -> None:
    if not utils.ffmpeg_is_available():
        return
    download_ids = set(db.SavedSearch.get_subscribed_song_ids()).intersection(updates)
    if settings.get_auto_update():
        search = db.SearchBuilder(statuses=[db.DownloadStatus.OUTDATED])
        download_ids.update(db.search_usdb_songs(search))
    songs = [s for i in download_ids if (s := UsdbSong.get(i))]
    if not songs:
        return
    for song in songs:
        song.status = db.DownloadStatus.PENDING
    with db.transaction():
        UsdbSong.upsert_many(songs)
    events.DownloadsRequested(len(songs)).post()
    DownloadManager.download(songs)


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


@attrs.define
class _SyncMetaFolderSyncer:
    folder: Path
    keep_unknown_song_ids: bool
    db_metas: dict[SyncMetaId, SyncMeta]
    song_ids: set[SongId]
    to_upsert: list[SyncMeta]
    found_metas: set[SyncMetaId]

    @classmethod
    def new(cls, folder: Path, keep_unknown_song_ids: bool) -> _SyncMetaFolderSyncer:
        return cls(
            folder=folder,
            keep_unknown_song_ids=keep_unknown_song_ids,
            db_metas={m.sync_meta_id: m for m in SyncMeta.get_in_folder(folder)},
            song_ids=set(db.all_song_ids()),
            to_upsert=[],
            found_metas=set(),
        )

    def process(self) -> None:
        for path in _iterate_usdb_files_in_folder_recursively(folder=self.folder):
            self._process_path(path)
        SyncMeta.delete_many_in_folder(
            self.folder, tuple(self.db_metas.keys() - self.found_metas)
        )
        SyncMeta.upsert_many(self.to_upsert)

    def _process_path(self, path: Path) -> None:
        if meta_id := SyncMetaId.from_path(path):
            if meta_id in self.found_metas:
                utils.trash_or_delete_path(path)
                logger.warning(f"Trashed duplicated meta file: '{path}'")
                return
            self.found_metas.add(meta_id)

        meta = None if meta_id is None else self.db_metas.get(meta_id)

        if meta_id is not None and meta and meta.mtime == utils.get_mtime(path):
            self._process_unchanged_file(path, meta)
        else:
            self._process_changed_or_new_file(path)

    def _process_unchanged_file(self, path: Path, meta: SyncMeta) -> None:
        if not utils.compare_unicode_paths(path, meta.path):
            meta.path = path
            self.to_upsert.append(meta)
            logger.info(f"Meta file was moved: '{path}'.")

    def _process_changed_or_new_file(self, path: Path) -> None:
        if not (meta := SyncMeta.try_from_file(path)):
            return
        if meta.song_id in self.song_ids:
            # file was changed and maybe moved
            self.to_upsert.append(meta)
            if meta.sync_meta_id in self.db_metas:
                logger.info(f"Updated meta file from disk: '{path}'.")
            else:
                logger.info(f"New meta file found on disk: '{path}'.")
        elif not self.keep_unknown_song_ids:
            logger.info(f"{meta.song_id.usdb_detail_url()} no longer exists on USDB.")
            if settings.get_trash_remotely_deleted_songs():
                logger.info(f"Deleting '{path.parent}' locally as well.")
                utils.trash_or_delete_path(path.parent)


def synchronize_sync_meta_folder(folder: Path, keep_unknown_song_ids: bool) -> None:
    _SyncMetaFolderSyncer.new(folder, keep_unknown_song_ids).process()


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
