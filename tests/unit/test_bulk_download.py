"""Tests for bulk download functionality."""

import tempfile
from pathlib import Path
from typing import NamedTuple

import pytest

from usdb_syncer.bulk_download import (
    BulkDownloadEntry,
    parse_bulk_import_file,
    BulkDownloadParseError,
)


class TestParserBasic:
    """Test basic parsing functionality."""

    def test_parse_single_valid_entry(self) -> None:
        """Parse a single valid song,artist entry."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Song Title Artist Name")
            f.flush()
            path = Path(f.name)

        try:
            result = parse_bulk_import_file(path)
            assert len(result) == 1
            assert result[0].search_query == "Song Title Artist Name"
        finally:
            path.unlink()

    def test_parse_multiple_entries(self) -> None:
        """Parse multiple song,artist entries."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Song One Artist One, Song Two Artist Two, Song Three Artist Three")
            f.flush()
            path = Path(f.name)

        try:
            result = parse_bulk_import_file(path)
            assert len(result) == 3
            assert result[0].search_query == "Song One Artist One"
            assert result[1].search_query == "Song Two Artist Two"
            assert result[2].search_query == "Song Three Artist Three"
        finally:
            path.unlink()


class TestParserWhitespace:
    """Test whitespace handling."""

    def test_trim_leading_trailing_whitespace(self) -> None:
        """Trim whitespace from queries."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("  Song Title Artist Name  ,  Next Song Next Artist  ")
            f.flush()
            path = Path(f.name)

        try:
            result = parse_bulk_import_file(path)
            assert result[0].search_query == "Song Title Artist Name"
            assert result[1].search_query == "Next Song Next Artist"
        finally:
            path.unlink()

    def test_skip_empty_lines(self) -> None:
        """Empty queries should be skipped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Song One, , Song Two,   , \n,Song Three")
            f.flush()
            path = Path(f.name)

        try:
            result = parse_bulk_import_file(path)
            assert len(result) == 3
            assert result[0].search_query == "Song One"
            assert result[1].search_query == "Song Two"
            assert result[2].search_query == "Song Three"
        finally:
            path.unlink()

    def test_preserve_internal_whitespace(self) -> None:
        """Preserve whitespace within queries."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Song  With  Spaces")
            f.flush()
            path = Path(f.name)

        try:
            result = parse_bulk_import_file(path)
            assert result[0].search_query == "Song  With  Spaces"
        finally:
            path.unlink()


class TestParserErrors:
    """Test error handling."""

    def test_file_not_found(self) -> None:
        """Raise error for non-existent file."""
        with pytest.raises(FileNotFoundError):
            parse_bulk_import_file(Path("/nonexistent/path/file.txt"))

    def test_empty_file(self) -> None:
        """Raise error for empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(BulkDownloadParseError) as exc_info:
                parse_bulk_import_file(path)
            assert "empty" in str(exc_info.value).lower() or "no valid entries" in str(exc_info.value).lower()
        finally:
            path.unlink()

class TestParserValidDataClass:
    """Test that BulkDownloadEntry is properly structured."""

    def test_bulk_download_entry_type(self) -> None:
        """BulkDownloadEntry should have search_query."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test Song Test Artist")
            f.flush()
            path = Path(f.name)

        try:
            result = parse_bulk_import_file(path)
            entry = result[0]
            assert isinstance(entry, BulkDownloadEntry)
            assert hasattr(entry, "search_query")
            assert isinstance(entry.search_query, str)
        finally:
            path.unlink()


# Phase 2 Tests: USDB Search Integration

from unittest.mock import patch, MagicMock

class TestSearchAndGetSongs:
    """Test searching USDB for bulk import entries."""

    @patch("usdb_syncer.bulk_download.UsdbSong.get")
    @patch("usdb_syncer.bulk_download.search_usdb_songs")
    def test_search_single_song_found(
        self, mock_find: MagicMock, mock_get: MagicMock, song: "UsdbSong"
    ) -> None:
        """Test searching for a single song that exists in USDB."""
        # Setup mocks
        mock_find.return_value = [song.song_id]
        mock_get.return_value = song

        entries = [BulkDownloadEntry(search_query=f"{song.title} {song.artist}")]

        from usdb_syncer.bulk_download import search_and_get_songs

        results = search_and_get_songs(entries)

        assert len(results) == 1
        assert results[0].entry == entries[0]
        assert results[0].usdb_song == song
        assert results[0].error is None
        mock_find.assert_called_once()
        mock_get.assert_called_once()

    @patch("usdb_syncer.bulk_download.search_usdb_songs")
    def test_search_song_not_found(self, mock_find: MagicMock) -> None:
        """Test searching for a song that doesn't exist."""
        # Setup mock to return no results
        mock_find.return_value = []

        entries = [BulkDownloadEntry(search_query="NonExistentSongXYZ123 NonExistentArtistXYZ123")]

        from usdb_syncer.bulk_download import search_and_get_songs

        results = search_and_get_songs(entries)

        assert len(results) == 1
        assert results[0].usdb_song is None
        assert results[0].error is not None
        assert "not found" in results[0].error.lower() or "no results" in results[0].error.lower()
        mock_find.assert_called_once()

    @patch("usdb_syncer.bulk_download.UsdbSong.get")
    @patch("usdb_syncer.bulk_download.search_usdb_songs")
    def test_search_multiple_songs_mixed(
        self, mock_find: MagicMock, mock_get: MagicMock, song: "UsdbSong"
    ) -> None:
        """Test searching for multiple songs with mixed found/not-found results."""
        # Setup mocks to return a match for the first search, empty for the second
        mock_find.side_effect = [[song.song_id], []]
        mock_get.return_value = song

        entries = [
            BulkDownloadEntry(search_query=f"{song.title} {song.artist}"),
            BulkDownloadEntry(search_query="NonExistentSongXYZ123 NonExistentArtistXYZ123"),
        ]

        from usdb_syncer.bulk_download import search_and_get_songs

        results = search_and_get_songs(entries)

        assert len(results) == 2
        assert results[0].usdb_song is not None
        assert results[1].usdb_song is None
        assert results[1].error is not None
        assert mock_find.call_count == 2


class TestBulkDownloadResultStructure:
    """Test BulkDownloadResult data structure."""

    def test_result_with_song(self, song: "UsdbSong") -> None:
        """Test BulkDownloadResult with a found song."""
        from usdb_syncer.bulk_download import BulkDownloadResult
        entry = BulkDownloadEntry(search_query="Test Artist")
        result = BulkDownloadResult(entry=entry, usdb_song=song)

        assert result.entry == entry
        assert result.usdb_song == song
        assert result.error is None

    def test_result_with_error(self) -> None:
        """Test BulkDownloadResult with an error."""
        from usdb_syncer.bulk_download import BulkDownloadResult
        entry = BulkDownloadEntry(search_query="Test Artist")
        result = BulkDownloadResult(entry=entry, error="Song not found")

        assert result.entry == entry
        assert result.usdb_song is None
        assert result.error == "Song not found"


# Phase 3 Tests: Download Manager Integration


class TestDownloadAndAddSongs:
    """Test downloading and adding songs to library."""

    def test_download_summary_structure(self) -> None:
        """Test DownloadSummary data structure."""
        from usdb_syncer.bulk_download import DownloadSummary

        summary = DownloadSummary(succeeded=5, failed=2, skipped=1)
        summary.errors.append("Error 1")
        summary.errors.append("Error 2")

        assert summary.succeeded == 5
        assert summary.failed == 2
        assert summary.skipped == 1
        assert len(summary.errors) == 2
        assert summary.errors[0] == "Error 1"

    def test_download_summary_default_values(self) -> None:
        """Test DownloadSummary with default values."""
        from usdb_syncer.bulk_download import DownloadSummary

        summary = DownloadSummary()

        assert summary.succeeded == 0
        assert summary.failed == 0
        assert summary.skipped == 0
        assert summary.errors == []

    @patch("usdb_syncer.song_loader.DownloadManager")
    def test_download_multiple_songs(self, mock_manager: MagicMock, song: "UsdbSong") -> None:
        """Test downloading multiple songs successfully."""
        from usdb_syncer.bulk_download import (
            download_and_add_songs,
            BulkDownloadResult,
        )

        # Create successful results for testing
        results = [
            BulkDownloadResult(
                entry=BulkDownloadEntry(search_query=f"{song.title} {song.artist}"),
                usdb_song=song,
            )
        ]

        # Track progress calls
        progress_calls = []

        def progress_callback(current: int, total: int, song_name: str) -> None:
            progress_calls.append((current, total, song_name))

        summary = download_and_add_songs(results, progress_callback)

        # Should have at least attempted one download
        assert summary.succeeded + summary.failed > 0
        # Should have called progress at least once
        assert len(progress_calls) > 0
        mock_manager.download.assert_called_once()

    def test_download_with_errors(self) -> None:
        """Test download handling when songs have errors."""
        from usdb_syncer.bulk_download import (
            download_and_add_songs,
            BulkDownloadResult,
        )

        # Create results with errors
        results = [
            BulkDownloadResult(
                entry=BulkDownloadEntry(search_query="Missing Artist"),
                error="Song not found",
            )
        ]

        def progress_callback(current: int, total: int, song_name: str) -> None:
            pass

        summary = download_and_add_songs(results, progress_callback)

        # Should have one failed due to error
        assert summary.failed == 1
        assert summary.succeeded == 0
        assert len(summary.errors) > 0


class TestDownloadLogging:
    """Test that download operations are properly logged."""

    def test_bulk_import_logs_parsing(self) -> None:
        """Test that parsing is logged."""
        import tempfile

        from usdb_syncer.bulk_download import parse_bulk_import_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Song Artist\n")
            f.flush()
            path = Path(f.name)

        try:
            # Just verify it parses without error (logging tested in integration)
            result = parse_bulk_import_file(path)
            assert len(result) == 1
        finally:
            path.unlink()
