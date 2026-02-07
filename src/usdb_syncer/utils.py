"""General-purpose utilities."""

import datetime
import functools
import itertools
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from typing import ClassVar

import requests
import send2trash
from bs4 import BeautifulSoup, Tag
from packaging import version
from platformdirs import PlatformDirs
from unidecode import unidecode

import usdb_syncer
from usdb_syncer import constants, errors, settings, subprocessing
from usdb_syncer.logger import Logger, logger

CACHE_LIFETIME = 60 * 60
_platform_dirs = PlatformDirs("usdb_syncer", "bohning")


def _root() -> Path:
    """Return source root folder or temporary bundle folder if running as such."""
    if getattr(sys, "frozen", False) and (bundle := getattr(sys, "_MEIPASS", None)):
        return Path(bundle)
    return Path(__file__).parent.parent.parent.absolute()


def open_url_in_browser(url: str) -> None:
    """Safely open a URL in the user's default web browser, with platform-specific handling."""
    match sys.platform:
        case "win32":
            os.startfile(url)  # type: ignore[attr-defined]
        case "darwin":
            subprocess.run(["open", url], check=True)
        case "linux":
            subprocessing.run_clean(["xdg-open", url])
        case _:
            logger.error(f"Cannot open URLs on platform '{sys.platform}'.")


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


def _parse_polsy_html(html: str) -> list[str] | None:
    """Parse the HTML from polsy.org.uk and return a list of allowed countries."""
    soup = BeautifulSoup(html, "lxml")
    allowed_countries = []

    table = soup.find("table")
    if not table or not isinstance(table, Tag):
        return None

    rows = table.find_all("tr")[1:]

    for row in rows:
        if not isinstance(row, Tag):
            continue
        cols = row.find_all("td")
        if len(cols) < 2:
            continue
        if country_code := cols[0].text.split(" - ", 1)[0]:
            allowed_countries.append(country_code)

    return allowed_countries


def get_allowed_countries(resource: str) -> list[str] | None:
    """Fetch YouTube video availability information from polsy.org.uk."""
    url = f"https://polsy.org.uk/stuff/ytrestrict.cgi?agreed=on&ytid={resource}"
    response = requests.get(url, timeout=5)

    if not response.ok:
        return None

    return _parse_polsy_html(response.text)


def remove_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from a string."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def get_first_alphanum_upper(text: str) -> str | None:
    """Return the first uppercase alphanumeric character in a string."""
    for char in text:
        if char.isalnum():
            return unidecode(char)[0].upper()
    return None


class AppPaths:
    """App data paths."""

    log = Path(_platform_dirs.user_data_dir, "usdb_syncer.log")
    db = Path(_platform_dirs.user_data_dir, "usdb_syncer.db")
    addons = Path(_platform_dirs.user_data_dir, "addons")
    licenses = Path(_platform_dirs.user_data_dir, "licenses")
    license_hash = Path(_platform_dirs.user_data_dir, "license_hash.txt")
    song_list = Path(_platform_dirs.user_cache_dir, "available_songs.json")
    profile = Path(_platform_dirs.user_cache_dir, "usdb_syncer.prof")
    shared = (_root() / "shared") if constants.IS_SOURCE else None

    @classmethod
    def make_dirs(cls) -> None:
        cls.addons.mkdir(parents=True, exist_ok=True)
        cls.licenses.mkdir(parents=True, exist_ok=True)
        cls.song_list.parent.mkdir(parents=True, exist_ok=True)


class DirectoryCache:
    """Helper to keep track of directories.

    This is to avoid a race condition when two songs requiring the same folder name
    are downloaded concurrently.
    """

    _cache: ClassVar[dict[Path, float]] = {}

    @classmethod
    def insert(cls, path: Path) -> bool:
        """Return True if path was not in the cache (or the entry had expired)."""
        now = time.time()
        if cls._cache.get(path, 0) + CACHE_LIFETIME < now:
            cls._cache[path] = now
            return True
        return False


def extract_youtube_id(url: str) -> str | None:
    """Extract the YouTube id from a variety of URLs.

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
    """Extract the Vimeo id from a variety of URLs."""
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
    """Return the first `length` lines of `path`.

    If `encoding` is None, try UTF-8 (with
    BOM) first, then cp1252.
    """
    for enc in [encoding] if encoding else ["utf-8-sig", "cp1252"]:
        try:
            with path.open(encoding=enc) as file:
                # strip line break
                return [r[:-1] for r in itertools.islice(file, length)]
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
    """Ensure directory name is unique by adding a suffix if necessary."""
    out_path = path
    suffix = 0
    while not DirectoryCache.insert(out_path) or out_path.exists():
        suffix += 1
        out_path = path.with_name(f"{path.name} ({suffix})")
    return out_path


def is_name_maybe_with_suffix(text: str, name: str) -> bool:
    """Check if `text` is `name` or `name (n)`."""
    if not text.startswith(name):
        return False
    tail = text.removeprefix(name)
    return not tail or re.fullmatch(r" \(\d+\)", tail) is not None


def path_matches_maybe_with_suffix(path: Path, search: Path) -> bool:
    """Check if `path` matches `search` with an optional suffix.

    Return True if `path` matches `search` with an optional suffix ` (n)` for some
    number n.
    """
    path = normalize_path(path)
    search = normalize_path(search)
    if path.parent != search.parent:
        return False
    return is_name_maybe_with_suffix(path.name, search.name)


def open_path_or_file(path: Path) -> None:
    logger.debug(f"Opening '{path}' with file explorer.")
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "linux":
        subprocess.run(
            ["xdg-open", str(path)], check=True, env=subprocessing.get_env_clean()
        )
    else:
        subprocess.run(["open", str(path)], check=True)


def add_to_system_path(path: str) -> None:
    with subprocessing.environ_lock:
        os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]


def normalize(text: str) -> str:
    """Return the Unicode NFC form of the string."""
    return unicodedata.normalize("NFC", text)


def normalize_path(path: Path) -> Path:
    return Path(*(normalize(p) for p in path.parts))


def compare_unicode_paths(lhs: Path, rhs: Path) -> bool:
    """Check two paths for equality.

    Takes into account implicit Unicode normalization
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
    """Get mtime of path in microseconds."""
    return int(path.stat().st_mtime * 1_000_000)


@functools.cache
def format_timestamp(micros: int) -> str:
    return datetime.datetime.fromtimestamp(micros / 1_000_000).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def remove_url_params(url: str, logger: Logger | None = None) -> str:
    url_base, _, url_params = url.partition("&")
    if url_params and logger:
        logger.debug(f"Stripped superfluous query parameters from '{url}'.")
    return url_base


def get_latest_version() -> str | None:
    try:
        response = requests.get(constants.GITHUB_API_LATEST, timeout=5)
        response.raise_for_status()
        return response.json().get("tag_name")
    except requests.Timeout:
        logger.warning(
            "Failed to retrieve latest version from GitHub, API request timed out."
        )
    except requests.RequestException as e:
        logger.warning(f"Failed to retrieve latest version from GitHub, API error: {e}")
    return None


def newer_version_available() -> str | None:
    if latest_version := get_latest_version():
        if version.parse(usdb_syncer.__version__) < version.parse(latest_version):
            logger.warning(
                f"USDB Syncer {latest_version} is available! "
                f"(You have {usdb_syncer.__version__}). Please download the latest "
                f"release from {constants.GITHUB_DL_LATEST}."
            )
            return latest_version
        logger.info(f"You are running the latest Syncer version {latest_version}.")
        return None

    logger.info("Could not determine the latest version.")
    return None


def start_process_detached(command: list[str]) -> subprocess.Popen:
    """Start a process in a fully detached mode, cross-platform."""
    # We are not using a context manager here so that the app is launched
    # without blocking the syncer.
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(
        command, creationflags=flags, close_fds=True, env=subprocessing.get_env_clean()
    )


def get_media_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )
    return float(result.stdout)


def ffmpeg_is_available() -> bool:
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return True
    if (path := settings.get_ffmpeg_dir()) and path not in os.environ["PATH"]:
        # first run; restore path from settings
        add_to_system_path(path)
        if shutil.which("ffmpeg") and shutil.which("ffprobe"):
            return True
    return False


def deno_is_available() -> bool:
    if shutil.which("deno"):
        return True
    if (path := settings.get_deno_dir()) and path not in os.environ["PATH"]:
        # first run; restore path from settings
        add_to_system_path(path)
        if shutil.which("deno"):
            return True
    return False


def open_external_app(app: settings.SupportedApps, path: Path) -> None:
    logger.debug(f"Starting {app} with '{path}'.")
    executable = settings.get_app_path(app)
    if executable is None:
        return
    if executable.suffix == ".jar":
        cmd = ["java", "-jar", str(executable), str(path)]
    else:
        cmd = [str(executable), app.songpath_parameter(), str(path)]
    try:
        start_process_detached(cmd)
    except FileNotFoundError:
        logger.error(
            f"Failed to launch {app} from '{executable!s}', file not found. "
            "Please check the executable path in the settings."
        )
    except OSError:
        logger.exception(f"Failed to launch {app} from '{executable!s}', I/O error.")
    except subprocess.SubprocessError:
        logger.exception(
            f"Failed to launch {app} from '{executable!s}', subprocess error."
        )


def trash_or_delete_path(path: Path) -> None:
    if settings.get_trash_files():
        try:
            send2trash.send2trash(path)
        except send2trash.TrashPermissionError as err:
            raise errors.TrashError(path) from err
    else:
        shutil.rmtree(path) if path.is_dir() else path.unlink()
