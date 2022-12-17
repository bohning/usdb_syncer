"""General-purpose utilities."""

import os
import re
import subprocess
import sys

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


def next_unique_directory(path: str) -> str:
    """Ensures directory name is unique by adding a suffix if necessary."""
    out_path = path
    suffix = 0
    while os.path.exists(out_path):
        suffix += 1
        out_path = f"{path} ({suffix})"
    return out_path


def is_name_maybe_with_suffix(text: str, name: str) -> bool:
    """True if `text` is 'name' or 'name (n)' for the provided `name` and some number n."""
    if not text.startswith(name):
        return False
    tail = text.removeprefix(name)
    return not tail or re.fullmatch(r" \(\d+\)", tail) is not None


def open_file_explorer(path: str) -> None:
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "linux":
        subprocess.run(["xdg-open", path], check=True)
    else:
        subprocess.run(["open", path], check=True)


def add_to_system_path(path: str) -> None:
    os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]
