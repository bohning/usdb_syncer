"""Runnable for getting the available songs from USDB or the local cache."""

import json
import os
from typing import Callable

import appdirs
from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtGui import QIcon
from unidecode import unidecode

from usdb_syncer import usdb_scraper
from usdb_syncer.logger import get_logger
from usdb_syncer.notes_parser import NotesParseError, SongTxt
from usdb_syncer.usdb_scraper import SongMeta


class SyncedSongMeta:
    """SongMeta wrapper for use in the song table."""

    local_txt: bool = False
    local_audio: bool = False
    local_video: bool = False
    local_cover: bool = False
    local_background: bool = False

    def __init__(self, data: SongMeta, song_dir: str) -> None:
        self.data = data
        self.song_id = data.song_id
        self.song_id_str = str(data.song_id)
        self.golden_notes = "Yes" if data.golden_notes else "No"
        self.rating_str = data.rating_str()
        self.searchable_text = unidecode(
            " ".join(
                (
                    self.song_id_str,
                    self.data.artist,
                    self.data.title,
                    self.data.language,
                    self.data.edition,
                )
            )
        ).lower()
        self._sync_local_files(song_dir)

    def _sync_local_files(self, song_dir: str) -> None:
        folder = os.path.join(
            song_dir, f"{self.data.artist} - {self.data.title}", str(self.song_id)
        )
        if not os.path.exists(os.path.join(folder, f"{self.song_id}.usdb")):
            return
        txt_path = os.path.join(folder, f"{self.data.artist} - {self.data.title}.txt")
        if not os.path.exists(txt_path):
            return
        self.local_txt = True
        logger = get_logger(__file__, self.song_id)
        try:
            with open(txt_path, encoding="utf-8") as file:
                txt = SongTxt(file.read(), logger)
        except (NotesParseError, OSError):
            return
        self.local_audio = _file_exists(folder, txt.headers.mp3)
        self.local_video = _file_exists(folder, txt.headers.video)
        self.local_cover = _file_exists(folder, txt.headers.cover)
        self.local_background = _file_exists(folder, txt.headers.background)

    def display_data(self, column: int) -> str:
        match column:
            case 0:
                return self.song_id_str
            case 1:
                return self.data.artist
            case 2:
                return self.data.title
            case 3:
                return self.data.language
            case 4:
                return self.data.edition
            case 5:
                return self.golden_notes
            case 6:
                return self.rating_str
            case 7:
                return str(self.data.views)
            case _:
                return ""

    def decoration_data(self, column: int) -> QIcon | None:
        if (
            (column == 8 and self.local_txt)
            or (column == 9 and self.local_audio)
            or (column == 10 and self.local_video)
            or (column == 11 and self.local_cover)
            or (column == 12 and self.local_background)
        ):
            return QIcon(":/icons/tick.png")
        return None


class Signals(QObject):
    """Custom signals."""

    song_list = Signal(object)


class SongListFetcher(QRunnable):
    """Runnable for getting the available songs from USDB or the local cache."""

    def __init__(
        self,
        force_reload: bool,
        song_dir: str,
        on_done: Callable[[list[SyncedSongMeta]], None],
    ) -> None:
        super().__init__()
        self.force_reload = force_reload
        self.song_dir = song_dir
        self.signals = Signals()
        self.signals.song_list.connect(on_done)

    def run(self) -> None:
        available_songs = get_available_songs(self.force_reload)
        synced_songs = [SyncedSongMeta(s, self.song_dir) for s in available_songs]
        self.signals.song_list.emit(synced_songs)


def get_available_songs(force_reload: bool) -> list[SongMeta]:
    if force_reload or not (available_songs := load_available_songs()):
        available_songs = usdb_scraper.get_usdb_available_songs()
        dump_available_songs(available_songs)
    return available_songs


def load_available_songs() -> list[SongMeta] | None:
    path = available_songs_path()
    if not os.path.exists(path):
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
        appdirs.user_cache_dir("usdb_syncer", "bohning"), "available_songs.json"
    )


def _file_exists(folder: str, fname: str | None) -> bool:
    if not fname:
        return False
    return os.path.exists(os.path.join(folder, fname))
