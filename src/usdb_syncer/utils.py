"""General-purpose utilities."""

import os
import re

from appdirs import AppDirs

_app_dirs = AppDirs("usdb_syncer", "bohning")


class AppPaths:
    """App data paths."""

    log = os.path.join(_app_dirs.user_data_dir, "usdb_syncer.log")
    song_list = os.path.join(_app_dirs.user_cache_dir, "available_songs.json")

    @classmethod
    def make_dirs(cls) -> None:
        os.makedirs(os.path.dirname(cls.log), exist_ok=True)
        os.makedirs(os.path.dirname(cls.song_list), exist_ok=True)


def extract_youtube_id(url: str) -> str | None:
    """Extracts the YouTube id from a variety of URLs.

    Partially taken from `https://regexr.com/531i0`.
    """

    pattern = r"""
        (?:https?://)?
        (?:www\.)?
        (?:m\.)?
        (?:
            youtube\.com/
            |
            youtube-nocookie\.com/
            |
            youtu\.be               # no '/' because id may follow immediately
        )
        \S*
        (?:/|%3D|v=|vi=)
        ([0-9a-z_-]{11})            # the actual id
        (?:[%#?&]|$)                # URL may contain additonal parameters
        .*
        """
    if match := re.search(pattern, url, re.VERBOSE | re.IGNORECASE):
        return match.group(1)
    return None


def try_read_unknown_encoding(path: str) -> str | None:
    for codec in ["utf-8-sig", "cp1252"]:
        try:
            with open(path, encoding=codec) as file:
                return file.read()
        except UnicodeDecodeError:
            pass
    return None


FILENAME_REPLACEMENTS = (('?:"', ""), ("<", "("), (">", ")"), ("/\\|*", "-"))


def sanitize_filename(fname: str) -> str:
    for (old, new) in FILENAME_REPLACEMENTS:
        for char in old:
            fname = fname.replace(char, new)
    return fname
