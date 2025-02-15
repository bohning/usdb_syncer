"""General-purpose utilities."""

import datetime
import functools
import itertools
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import requests
from appdirs import AppDirs
from packaging import version

from usdb_syncer import constants
from usdb_syncer.logger import logger

CACHE_LIFETIME = 60 * 60
_app_dirs = AppDirs("usdb_syncer", "bohning")


def is_bundle() -> bool:
    """True if the app is running from a bundle.

    https://pyinstaller.org/en/stable/runtime-information.html#run-time-information
    """
    return bool(getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", False))


def _root() -> Path:
    """Returns source root folder or temprory bundle folder if running as such."""
    if getattr(sys, "frozen", False) and (bundle := getattr(sys, "_MEIPASS", None)):
        return Path(bundle)
    return Path(__file__).parent.parent.parent.absolute()


def video_url_from_resource(resource: str) -> str | None:
    if "://" in resource:
        return resource
    if "/" in resource:
        return f"https://{resource}"
    vimeo_id_pattern = r"^\d{2,10}$"
    if re.match(vimeo_id_pattern, resource):
        return f"https://vimeo.com/{resource}"
    yt_id_pattern = r"^[A-Za-z0-9_-]{11}$"
    if re.match(yt_id_pattern, resource):
        return f"https://www.youtube.com/watch?v={resource}"
    return None


class AppPaths:
    """App data paths."""

    log = Path(_app_dirs.user_data_dir, "usdb_syncer.log")
    song_list = Path(_app_dirs.user_cache_dir, "available_songs.json")
    root = _root()
    fallback_song_list = Path(root, "data", "song_list.json")
    profile = Path(root, "usdb_syncer.prof")
    db = Path(_app_dirs.user_data_dir, "usdb_syncer.db")
    sql = Path(root, "src", "usdb_syncer", "db", "sql")
    addons = Path(_app_dirs.user_data_dir, "addons")

    @classmethod
    def make_dirs(cls) -> None:
        cls.addons.mkdir(parents=True, exist_ok=True)
        cls.song_list.parent.mkdir(parents=True, exist_ok=True)


class DirectoryCache:
    """Helper to keep track of directories.

    This is to avoid a race condition when two songs requiring the same folder name
    are downloaded concurrently.
    """

    _cache: dict[Path, float] = {}

    @classmethod
    def insert(cls, path: Path) -> bool:
        """True if path was not in the cache (or the entry had expired)."""
        now = time.time()
        if cls._cache.get(path, 0) + CACHE_LIFETIME < now:
            cls._cache[path] = now
            return True
        return False


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
        (?:[%#?&]|$)                # URL may contain additional parameters
        .*
        """
    if match := re.fullmatch(pattern, url, re.VERBOSE | re.IGNORECASE):
        return match.group(1)
    return None


def extract_vimeo_id(url: str) -> str | None:
    """Extracts the Vimeo id from a variety of URLs."""

    pattern = r"""
        (?:https?://)?
        (?:
            www\.
            |
            player\.
        )?
        (?:vimeo\.com/)
        (?:video/)?
        (\d{2,9})                   # the actual id
        (?:[%#?&]|$)                # URL may contain additonal parameters
        .*
        """
    if match := re.search(pattern, url, re.VERBOSE | re.IGNORECASE):
        return match.group(1)
    return None


def read_file_head(
    path: Path, length: int, encoding: str | None = None
) -> list[str] | None:
    """Return the first `length` lines of `path`. If `encoding` is None, try UTF-8 (with
    BOM) first, then cp1252.
    """
    for enc in [encoding] if encoding else ["utf-8-sig", "cp1252"]:
        try:
            with open(path, encoding=enc) as file:
                # strip line break
                return list(r[:-1] for r in itertools.islice(file, length))
        except UnicodeDecodeError:
            pass
    return None


FILENAME_REPLACEMENTS = (('?:"', ""), ("<", "("), (">", ")"), ("/\\|*", "-"))


def sanitize_filename(fname: str) -> str:
    for old, new in FILENAME_REPLACEMENTS:
        for char in old:
            fname = fname.replace(char, new)
    # trailing whitespace is handled inconsistently on OSes, and Windows does not like
    # trailing periods
    return fname.rstrip(" .")


def next_unique_directory(path: Path) -> Path:
    """Ensures directory name is unique by adding a suffix if necessary."""
    out_path = path
    suffix = 0
    while not DirectoryCache.insert(out_path) or out_path.exists():
        suffix += 1
        out_path = path.with_name(f"{path.name} ({suffix})")
    return out_path


def is_name_maybe_with_suffix(text: str, name: str) -> bool:
    """True if `text` is 'name' or 'name (n)' for the provided `name` and some number n."""
    if not text.startswith(name):
        return False
    tail = text.removeprefix(name)
    return not tail or re.fullmatch(r" \(\d+\)", tail) is not None


def path_matches_maybe_with_suffix(path: Path, search: Path) -> bool:
    """True if `path` matches `search`, with an optional suffix ` (n)` for some
    number n.
    """
    path = normalize_path(path)
    search = normalize_path(search)
    if path.parent != search.parent:
        return False
    return is_name_maybe_with_suffix(path.name, search.name)


def open_file_explorer(path: Path) -> None:
    logger.debug(f"Opening '{path}' with file explorer.")
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "linux":
        subprocess.run(["xdg-open", str(path)], check=True)
    else:
        subprocess.run(["open", str(path)], check=True)


def add_to_system_path(path: str) -> None:
    os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]


def normalize(text: str) -> str:
    """Return the Unicode NFC form of the string."""
    return unicodedata.normalize("NFC", text)


def normalize_path(path: Path) -> Path:
    return Path(*(normalize(p) for p in path.parts))


def compare_unicode_paths(lhs: Path, rhs: Path) -> bool:
    """Checks two paths for equality, taking into account implicit Unicode normalization
    on macOS.
    """
    if sys.platform == "darwin":
        return normalize(str(lhs)) == normalize(str(rhs))
    return lhs == rhs


def resource_file_ending(name: str) -> str:
    """Return the suffix or name, including " [BG]" and " [CO]"."""
    regex = re.compile(r".+?((?: \[(?:CO|BG)\])?\.[^.]+)")
    if match := regex.fullmatch(name):
        return match.group(1)
    return ""


def get_mtime(path: Path) -> int:
    """Helper for mtime in microseconds so it can be stored in db losslessly."""
    return int(os.path.getmtime(path) * 1_000_000)


@functools.cache
def format_timestamp(micros: int) -> str:
    return datetime.datetime.fromtimestamp(micros / 1_000_000).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def get_latest_version() -> str | None:
    response = requests.get(constants.GITHUB_API_LATEST, timeout=5)
    if response.status_code == 200:
        return response.json()["tag_name"]
    return None


def newer_version_available() -> str | None:
    if latest_version := get_latest_version():
        if version.parse(constants.VERSION) < version.parse(latest_version):
            logger.warning(
                f"USDB Syncer {latest_version} is available! "
                f"(You have {constants.VERSION}). Please download the latest release "
                f"from {constants.GITHUB_DL_LATEST}."
            )
            return latest_version
        logger.info(f"You are running the latest Syncer version {latest_version}.")
        return None

    logger.info("Could not determine the latest version.")
    return None
