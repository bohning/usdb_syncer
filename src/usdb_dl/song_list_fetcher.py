"""Runnable for getting the available songs from USDB or the local cache."""

import json
import os
import time
from typing import Callable

import appdirs
from PySide6.QtCore import QObject, QRunnable, Signal

from usdb_dl import usdb_scraper
from usdb_dl.usdb_scraper import SongMeta


class Signals(QObject):
    """Custom signals."""

    song_list = Signal(object)


class SongListFetcher(QRunnable):
    """Runnable for getting the available songs from USDB or the local cache."""

    def __init__(
        self, force_reload: bool, on_done: Callable[[list[SongMeta]], None]
    ) -> None:
        super().__init__()
        self.force_reload = force_reload
        self.signals = Signals()
        self.signals.song_list.connect(on_done)

    def run(self) -> None:
        self.signals.song_list.emit(get_available_songs(self.force_reload))


def get_available_songs(force_reload: bool) -> list[SongMeta]:
    if force_reload or not (available_songs := load_available_songs()):
        available_songs = usdb_scraper.get_usdb_available_songs()
        dump_available_songs(available_songs)
    return available_songs


def load_available_songs() -> list[SongMeta] | None:
    path = available_songs_path()
    if not has_recent_mtime(path) or not os.path.exists(path):
        return None
    with open(path, encoding="utf8") as file:
        try:
            return json.load(file, object_hook=lambda d: SongMeta(**d))
        except (json.decoder.JSONDecodeError, TypeError):
            return None


def dump_available_songs(available_songs: list[SongMeta]) -> None:
    os.makedirs(os.path.dirname(available_songs_path()), exist_ok=True)
    with open(available_songs_path(), "w", encoding="utf8") as file:
        json.dump(available_songs, file, cls=usdb_scraper.SongMetaEncoder)


def available_songs_path() -> str:
    return os.path.join(
        appdirs.user_cache_dir("usdb_dl", "bohning"), "available_songs.json"
    )


def has_recent_mtime(path: str, recent_secs: int = 60 * 60 * 24) -> bool:
    """True if the given path exists and its mtime is less than recent_secs in the past."""
    return os.path.exists(path) and time.time() - os.path.getmtime(path) < recent_secs
