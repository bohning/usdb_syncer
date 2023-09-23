"""Runnable for getting the available songs from USDB or the local cache."""

import json
from pathlib import Path

from requests import Session

from usdb_syncer import SongId, settings
from usdb_syncer.logger import get_logger
from usdb_syncer.song_data import LocalFiles, SongData
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.usdb_scraper import UsdbLoginError, get_usdb_available_songs
from usdb_syncer.usdb_song import UsdbSong, UsdbSongEncoder
from usdb_syncer.utils import AppPaths, try_read_unknown_encoding

_logger = get_logger(__file__)


def get_all_song_data(force_reload: bool) -> tuple[SongData, ...]:
    songs = get_available_songs(force_reload)
    local_files = find_local_files()
    return tuple(
        SongData.from_usdb_song(song, local_files.get(song.song_id, LocalFiles()))
        for song in songs
    )


def resync_song_data(data: tuple[SongData, ...]) -> tuple[SongData, ...]:
    local_files = find_local_files()
    return tuple(
        song.with_local_files(local_files.get(song.data.song_id, LocalFiles()))
        for song in data
    )


def get_available_songs(
    force_reload: bool, session: Session | None = None
) -> list[UsdbSong]:
    if force_reload:
        songs = []
        max_skip_id = SongId(0)
    else:
        songs = load_cached_songs() or []
        max_skip_id = max((song.song_id for song in songs), default=SongId(0))
    try:
        songs += get_usdb_available_songs(max_skip_id, session=session)
    except UsdbLoginError:
        _logger.debug("Skipping fetching new songs as there is no login.")
    return songs


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


def find_local_files() -> dict[SongId, LocalFiles]:
    local_files: dict[SongId, LocalFiles] = {}
    for path in settings.get_song_dir().glob("**/*.usdb"):
        if meta := SyncMeta.try_from_file(path):
            local_files[meta.song_id] = files = LocalFiles(usdb_path=path)
            if txt := _get_song_txt(
                meta=meta, folder=path.parent, parse_meta_tags=False
            ):
                files.txt = True
                files.audio = _file_exists(path.parent, txt.headers.mp3)
                files.video = _file_exists(path.parent, txt.headers.video)
                files.cover = _file_exists(path.parent, txt.headers.cover)
                files.background = _file_exists(path.parent, txt.headers.background)
    return local_files


def _get_song_txt(
    meta: SyncMeta, folder: Path, parse_meta_tags: bool = True
) -> SongTxt | None:
    if not meta.txt:
        return None
    txt_path = folder.joinpath(meta.txt.fname)
    logger = get_logger(__file__, meta.song_id)
    if txt_path.exists() and (contents := try_read_unknown_encoding(txt_path)):
        return SongTxt.try_parse(contents, logger, parse_meta_tags)
    return None


def _file_exists(folder: Path, fname: str | None) -> bool:
    if not fname:
        return False
    return folder.joinpath(fname).exists()
