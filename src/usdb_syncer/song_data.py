"""Wrapper for song data from USDB, rendered for presentation in the song table,
    plus information about locally existing files.
    """

import os
from functools import cache

import attrs
from PySide6.QtGui import QIcon
from unidecode import unidecode

from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.logger import get_logger
from usdb_syncer.notes_parser import SongTxt
from usdb_syncer.typing_helpers import assert_never
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

    def display_data(self, column: int) -> str | None:
        col = Column(column)
        match col:
            case Column.SONG_ID:
                return str(self.data.song_id)
            case Column.ARTIST:
                return self.data.artist
            case Column.TITLE:
                return self.data.title
            case Column.LANGUAGE:
                return self.data.language
            case Column.EDITION:
                return self.data.edition
            case Column.GOLDEN_NOTES:
                return yes_no_str(self.data.golden_notes)
            case Column.RATING:
                return rating_str(self.data.rating)
            case Column.VIEWS:
                return str(self.data.views)
            case Column.TXT | Column.AUDIO | Column.VIDEO | Column.COVER:  # pylint: disable=duplicate-code
                return None
            case Column.BACKGROUND:
                return None
            case _ as unreachable:
                assert_never(unreachable)

    def decoration_data(self, column: int) -> QIcon | None:
        col = Column(column)
        match col:
            case Column.SONG_ID | Column.ARTIST | Column.TITLE | Column.LANGUAGE:
                return None
            case Column.EDITION | Column.GOLDEN_NOTES | Column.RATING | Column.VIEWS:
                return None
            case Column.TXT:
                return optional_check_icon(self.local_txt)
            case Column.AUDIO:
                return optional_check_icon(self.local_audio)
            case Column.VIDEO:
                return optional_check_icon(self.local_video)
            case Column.COVER:
                return optional_check_icon(self.local_cover)
            case Column.BACKGROUND:
                return optional_check_icon(self.local_background)
            case _ as unreachable:
                assert_never(unreachable)


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


# Creating a QIcon without a QApplication gives a runtime error, so we can't put it
# in a global, but we also don't want to keep recreating it.
# So we store it in this convenience function.
@cache
def optional_check_icon(yes: bool) -> QIcon | None:
    return QIcon(":/icons/tick.png") if yes else None
