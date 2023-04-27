"""General-purpose utilities."""

import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

from appdirs import AppDirs

_app_dirs = AppDirs("usdb_syncer", "bohning")


def _root() -> Path:
    """Returns source root folder or temprory bundle folder if running as such.

    https://pyinstaller.org/en/stable/runtime-information.html#run-time-information
    """
    if getattr(sys, "frozen", False) and (bundle := getattr(sys, "_MEIPASS", None)):
        return Path(bundle)
    return Path(__file__).parent.parent.parent.absolute()


class AppPaths:
    """App data paths."""

    log = Path(_app_dirs.user_data_dir, "usdb_syncer.log")
    song_list = Path(_app_dirs.user_cache_dir, "available_songs.json")
    root = _root()
    fallback_song_list = Path(root, "data", "song_list.json")

    @classmethod
    def make_dirs(cls) -> None:
        cls.log.parent.mkdir(parents=True, exist_ok=True)
        cls.song_list.parent.mkdir(parents=True, exist_ok=True)


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
    for old, new in FILENAME_REPLACEMENTS:
        for char in old:
            fname = fname.replace(char, new)
    if fname.endswith("."):
        fname = fname.rstrip(" .")  # Windows does not like trailing periods
    return fname


def next_unique_directory(path: Path) -> Path:
    """Ensures directory name is unique by adding a suffix if necessary."""
    out_path = path
    suffix = 0
    while out_path.exists():
        suffix += 1
        out_path = path.with_name(f"{path.name} ({suffix})")
    return out_path


def is_name_maybe_with_suffix(text: str, name: str) -> bool:
    """True if `text` is 'name' or 'name (n)' for the provided `name` and some number n."""
    if not text.startswith(name):
        return False
    tail = text.removeprefix(name)
    return not tail or re.fullmatch(r" \(\d+\)", tail) is not None


def open_file_explorer(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "linux":
        subprocess.run(["xdg-open", str(path)], check=True)
    else:
        subprocess.run(["open", str(path)], check=True)


def add_to_system_path(path: str) -> None:
    os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]


def normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def resource_file_ending(name: str) -> str:
    """Return the suffix or name, including " [BG]" and " [CO]"."""
    regex = re.compile(r".+?((?: \[(?:CO|BG)\])?\.[^.]+)")
    if match := regex.fullmatch(name):
        return match.group(1)
    return ""
