"""Tests for importing and exporting USDB IDs"""

import os

import pytest

from usdb_syncer import SongId
from usdb_syncer.exchange_format import USDBIDFileParser


@pytest.mark.parametrize(
    "file,expected_ids,expected_errors",
    [
        (
            "broken_format.desktop",
            [],
            ["invalid file format: missing a section header"],
        ),
        ("broken_format.url", [], ["invalid file format: missing a section header"]),
        ("broken_format.webloc", [], ["invalid file format: missing tag 'plist'"]),
        (
            "broken_usdb_link.desktop",
            [],
            ["found URL has no query parameters: http://usdb.animux.de/index.phid=118"],
        ),
        (
            "broken_usdb_link.url",
            [],
            ["found URL has no query parameters: http://usdb.animux.de/index.phid=118"],
        ),
        (
            "broken_usdb_link.webloc",
            [],
            ["found URL has no query parameters: http://usdb.animux.de/index.phid=118"],
        ),
        (
            "dublicate_url_key.desktop",
            [],
            ["invalid file format: missing or dublicate option"],
        ),
        (
            "dublicate_url_key.url",
            [],
            ["invalid file format: missing or dublicate option"],
        ),
        (
            "dublicate_url_key.webloc",
            [],
            ["invalid file format: multiple URLs detected"],
        ),
        ("empty.desktop", [], ["invalid file format: missing section 'Desktop Entry'"]),
        ("empty.url", [], ["invalid file format: missing section 'InternetShortcut'"]),
        ("empty.webloc", [], ["invalid file format: missing tag 'plist'"]),
        ("missing_url_key.desktop", [], ["invalid file format: missing key 'URL'"]),
        ("missing_url_key.url", [], ["invalid file format: missing key 'URL'"]),
        (
            "missing_url_key.webloc",
            [],
            ["invalid file format: missing URL tag 'string'"],
        ),
        ("piano_man.desktop", [SongId(3327)], []),
        ("piano_man.url", [SongId(3327)], []),
        ("piano_man.webloc", [SongId(3327)], []),
        ("usdb_non_php.desktop", [SongId(17590)], []),
        ("usdb_non_php.url", [SongId(26380)], []),
        ("usdb_non_php.webloc", [SongId(25930)], []),
        ("usdb_http.desktop", [SongId(279)], []),
        ("usdb_http.url", [SongId(279)], []),
        ("usdb_http.webloc", [SongId(279)], []),
        ("usdb_short.desktop", [SongId(1001)], []),
        ("usdb_short.url", [SongId(1001)], []),
        ("usdb_short.webloc", [SongId(1001)], []),
        ("wrong_middle_level.webloc", [], ["invalid file format: missing tag 'dict'"]),
        (
            "wrong_top_level.desktop",
            [],
            ["invalid file format: missing section 'Desktop Entry'"],
        ),
        (
            "wrong_top_level.url",
            [],
            ["invalid file format: missing section 'InternetShortcut'"],
        ),
        ("wrong_top_level.webloc", [], ["invalid file format: missing tag 'plist'"]),
        ("youtube.desktop", [], ["found URL has invalid domain: www.youtube.com"]),
        ("youtube.url", [], ["found URL has invalid domain: youtu.be"]),
        ("youtube.webloc", [], ["found URL has invalid domain: www.youtube.com"]),
        ("empty.usdb_ids", [], ["empty file"]),
        ("ids_and_other_stuff.usdb_ids", [], ["invalid USDB ID in file"]),
        (
            "ids.usdb_ids",
            [
                SongId(1),
                SongId(29020),
                SongId(3),
                SongId(10396),
                SongId(117),
                SongId(1001),
                SongId(11111),
            ],
            [],
        ),
        (
            "ids_LF.usdb_ids",
            [
                SongId(1),
                SongId(29020),
                SongId(3),
                SongId(10396),
                SongId(117),
                SongId(1001),
                SongId(11111),
            ],
            [],
        ),
        ("multi-column.usdb_ids", [], ["invalid USDB ID in file"]),
        ("broken.json", [], ["invalid JSON format"]),
        ("empty.json", [], ["empty file"]),
        ("empty_array.json", [], ["empty JSON array"]),
        ("ids.json", [SongId(1), SongId(11586), SongId(3)], []),
        ("ids_inline.json", [SongId(1), SongId(29020), SongId(3)], []),
        ("ids_LF.json", [SongId(1), SongId(24112), SongId(3)], []),
        ("missing_id_key.json", [], ["invalid or missing USDB ID in file"]),
    ],
)
def test_import_song_ids_from_files(
    resource_dir: str, file: str, expected_ids: list[SongId], expected_errors: list[str]
) -> None:
    path = os.path.join(resource_dir, "import", file)
    parser = USDBIDFileParser(path)
    assert parser.errors == expected_errors, f"wrong errors from {file}"
    assert parser.ids == expected_ids, f"wrong songids from {file}"
