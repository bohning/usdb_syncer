"""Wrapper for song data from USDB, rendered for presentation in the song table,
    plus information about locally existing files.
    """

import os
from functools import cache

import attrs
from PySide6.QtGui import QIcon
from unidecode import unidecode

from usdb_syncer.logger import get_logger
from usdb_syncer.notes_parser import SongTxt
from usdb_syncer.usdb_scraper import UsdbSong


@attrs.frozen(auto_attribs=True, kw_only=True)
class SongData:
    """Wrapper for song data from USDB, rendered for presentation in the song table,
    plus information about locally existing files.
    """

    data: UsdbSong
    searchable_text: str
    local_txt: bool
    local_audio: bool
    local_video: bool
    local_cover: bool
    local_background: bool

    @classmethod
    def from_usdb_song(cls, song: UsdbSong, song_dir: str) -> "SongData":
        folder = _song_folder_path(song, song_dir)
        txt = _get_song_txt(song, song_dir)
        return cls(
            data=song,
            searchable_text=_searchable_text(song),
            local_txt=bool(txt),
            local_audio=_file_exists(folder, txt.headers.mp3) if txt else False,
            local_video=_file_exists(folder, txt.headers.video) if txt else False,
            local_cover=_file_exists(folder, txt.headers.cover) if txt else False,
            local_background=_file_exists(folder, txt.headers.background)
            if txt
            else False,
        )

    def display_data(self, column: int) -> str:
        match column:
            case 0:
                return str(self.data.song_id)
            case 1:
                return self.data.artist
            case 2:
                return self.data.title
            case 3:
                return self.data.language
            case 4:
                return self.data.edition
            case 5:
                return yes_no_str(self.data.golden_notes)
            case 6:
                return rating_str(self.data.rating)
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


def _song_folder_path(song: UsdbSong, song_dir: str) -> str:
    return os.path.join(song_dir, f"{song.artist} - {song.title}", str(song.song_id))


def _get_song_txt(song: UsdbSong, song_dir: str) -> SongTxt | None:
    folder = os.path.join(song_dir, f"{song.artist} - {song.title}", str(song.song_id))
    if not os.path.exists(os.path.join(folder, f"{song.song_id}.usdb")):
        return None
    txt_path = os.path.join(folder, f"{song.artist} - {song.title}.txt")
    logger = get_logger(__file__, song.song_id)
    if os.path.exists(txt_path):
        with open(txt_path, encoding="utf-8") as file:
            return SongTxt.try_parse(file.read(), logger)
    return None


def _file_exists(folder: str, fname: str | None) -> bool:
    if not fname:
        return False
    return os.path.exists(os.path.join(folder, fname))


def _searchable_text(song: UsdbSong) -> str:
    return unidecode(
        " ".join(
            (str(song.song_id), song.artist, song.title, song.language, song.edition)
        )
    ).lower()


@cache
def rating_str(rating: int) -> str:
    return rating * "★"


def yes_no_str(yes: bool) -> str:
    return "Yes" if yes else "No"
