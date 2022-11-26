"""Runnable for getting the available songs from USDB or the local cache."""

import json
import os
from typing import Callable

import appdirs
from PySide6.QtCore import QObject, QRunnable, Signal

from usdb_syncer import usdb_scraper
from usdb_syncer.usdb_scraper import UsdbSong


class Signals(QObject):
    """Custom signals."""

    song_list = Signal(object)


class SongListFetcher(QRunnable):
    """Runnable for getting the available songs from USDB or the local cache and
    crawling the song directory for associated local files.
    """

    def __init__(
        self,
        force_reload: bool,
        song_dir: str,
        on_done: Callable[[list[UsdbSong]], None],
    ) -> None:
        super().__init__()
        self.force_reload = force_reload
        self.song_dir = song_dir
        self.signals = Signals()
        self.signals.song_list.connect(on_done)

    def run(self) -> None:
        self.signals.song_list.emit(get_available_songs(self.force_reload))


def get_available_songs(force_reload: bool) -> list[UsdbSong]:
    if force_reload or not (available_songs := load_available_songs()):
        available_songs = usdb_scraper.get_usdb_available_songs()
        dump_available_songs(available_songs)
    return available_songs


def load_available_songs() -> list[UsdbSong] | None:
    path = available_songs_path()
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf8") as file:
        try:
            return json.load(file, object_hook=lambda d: UsdbSong(**d))
        except (json.decoder.JSONDecodeError, TypeError):
            return None


def dump_available_songs(available_songs: list[UsdbSong]) -> None:
    os.makedirs(os.path.dirname(available_songs_path()), exist_ok=True)
    with open(available_songs_path(), "w", encoding="utf8") as file:
        json.dump(available_songs, file, cls=usdb_scraper.SongMetaEncoder)


def available_songs_path() -> str:
    return os.path.join(
        appdirs.user_cache_dir("usdb_syncer", "bohning"), "available_songs.json"
    )
