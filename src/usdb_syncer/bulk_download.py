"""Bulk download functionality for importing songs from CSV/TXT files."""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from usdb_syncer.logger import logger
from usdb_syncer.db import search_usdb_songs, SearchBuilder
from usdb_syncer.usdb_song import UsdbSong


class BulkDownloadParseError(Exception):
    """Raised when parsing a bulk import file fails."""

    pass


@dataclass
class BulkDownloadEntry:
    """Represents a single song entry from a bulk import file."""

    search_query: str


@dataclass
class BulkDownloadResult:
    """Result of searching for a bulk download entry."""

    entry: BulkDownloadEntry
    usdb_song: Optional[UsdbSong] = None
    error: Optional[str] = None


@dataclass
class DownloadSummary:
    """Summary of bulk download operation."""

    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def parse_bulk_import_file(path: Path) -> list[BulkDownloadEntry]:
    """
    Parse a bulk import file and return list of BulkDownloadEntry items.

    File format: Comma-separated list of search queries.
    Example:
        Song Title Artist Name, Another Song Another Artist

    Args:
        path: Path to the .txt file to parse

    Returns:
        List of BulkDownloadEntry items

    Raises:
        FileNotFoundError: If the file doesn't exist
        BulkDownloadParseError: If the file format is invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    entries: list[BulkDownloadEntry] = []

    try:
        with open(path, mode="r", encoding="utf-8") as f:
            content = f.read()

        # Replace newlines with spaces, then split by comma and clean up whitespace
        content = content.replace("\n", " ").replace("\r", " ")
        queries = [q.strip() for q in content.split(",") if q.strip()]

        for query in queries:
            entries.append(BulkDownloadEntry(search_query=query))

        if not entries:
            raise BulkDownloadParseError("No valid entries found in file")

        return entries

    except BulkDownloadParseError:
        raise
    except Exception as e:
        raise BulkDownloadParseError(f"Error parsing file: {e}")


def search_and_get_songs(entries: list[BulkDownloadEntry]) -> list[BulkDownloadResult]:
    """
    Search for USDB songs matching the bulk import entries.

    For each entry, searches the USDB database by title and artist,
    returning the first match if found, or an error message if not found.

    Args:
        entries: List of BulkDownloadEntry items to search for

    Returns:
        List of BulkDownloadResult items with search results or errors
    """
    results: list[BulkDownloadResult] = []

    for entry in entries:
        try:
            # Search the USDB database for matching songs
            search_builder = SearchBuilder(text=entry.search_query)
            matching_song_ids = list(search_usdb_songs(search_builder))

            if matching_song_ids:
                # Found a matching song
                usdb_song = UsdbSong.get(matching_song_ids[0])
                if usdb_song:
                    result = BulkDownloadResult(entry=entry, usdb_song=usdb_song)
                    logger.debug(f"Found song: {entry.search_query} -> {usdb_song.song_id}")
                else:
                    error_msg = f"Song ID found but data missing: {entry.search_query}"
                    result = BulkDownloadResult(entry=entry, error=error_msg)
                    logger.warning(error_msg)
            else:
                # No matching song found
                error_msg = f"Song not found: {entry.search_query}"
                result = BulkDownloadResult(entry=entry, error=error_msg)
                logger.warning(error_msg)

            results.append(result)

        except Exception as e:
            error_msg = f"Search error for {entry.search_query}: {e}"
            result = BulkDownloadResult(entry=entry, error=error_msg)
            logger.error(error_msg)
            results.append(result)

    return results


def download_and_add_songs(
    results: list[BulkDownloadResult],
    progress_callback: Callable[[int, int, str], None],
) -> DownloadSummary:
    """
    Download and add songs to the library.

    Uses the existing DownloadManager to queue audio downloads for songs 
    found in the search results.

    Args:
        results: List of BulkDownloadResult items to download
        progress_callback: Callable(current, total, song_name) for progress updates

    Returns:
        DownloadSummary with counts and error messages
    """
    from usdb_syncer.song_loader import DownloadManager
    from usdb_syncer.utils import ProgressProxy

    summary = DownloadSummary()
    total = len(results)
    
    songs_to_download: list[UsdbSong] = []

    for current, result in enumerate(results, start=1):
        query = result.entry.search_query
        progress_callback(current, total, query)

        # Skip results that have errors (song not found)
        if result.error:
            summary.failed += 1
            summary.errors.append(result.error)
            logger.warning(f"Skipping {query}: {result.error}")
            continue

        # Skip if no USDB song found
        if not result.usdb_song:
            error_msg = f"No song data for {query}"
            summary.failed += 1
            summary.errors.append(error_msg)
            logger.warning(error_msg)
            continue

        songs_to_download.append(result.usdb_song)
        summary.succeeded += 1
        logger.debug(f"Queued {query} for download")

    if songs_to_download:
        progress = ProgressProxy("Starting downloads...")
        DownloadManager.download(songs_to_download, progress)

    return summary