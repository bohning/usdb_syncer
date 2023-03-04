"""Tests for importing and exporting USDB IDs"""

import os

from usdb_syncer import SongId
from usdb_syncer.exchange_format import USDBIDFileParser

KEY_IDS = "ids"
KEY_ERRORS = "errors"

ids_per_file: dict[str, dict] = {
    "youtube.url": {
        KEY_IDS: [],
        KEY_ERRORS: ["Found URL has invalid domain: youtu.be"],
    },
    "piano_man.url": {KEY_IDS: [SongId(3327)], KEY_ERRORS: []},
    "usdb_non_php.url": {KEY_IDS: [SongId(26380)], KEY_ERRORS: []},
    "usdb_http.url": {KEY_IDS: [SongId(279)], KEY_ERRORS: []},
    "usdb_short.url": {KEY_IDS: [SongId(1001)], KEY_ERRORS: []},
    "broken_usdb_link.url": {
        KEY_IDS: [],
        KEY_ERRORS: [
            "Found URL has no query parameters: http://usdb.animux.de/index.phid=118"
        ],
    },
    "ids_and_other_stuff.usdb_ids": {
        KEY_IDS: [],
        KEY_ERRORS: ["Invalid USDB ID in file"],
    },
    "ids.usdb_ids": {
        KEY_IDS: [
            SongId(1),
            SongId(29020),
            SongId(3),
            SongId(10396),
            SongId(117),
            SongId(1001),
            SongId(11111),
        ],
        KEY_ERRORS: [],
    },
    "ids_LF.usdb_ids": {
        KEY_IDS: [
            SongId(1),
            SongId(29020),
            SongId(3),
            SongId(10396),
            SongId(117),
            SongId(1001),
            SongId(11111),
        ],
        KEY_ERRORS: [],
    },
    "empty.usdb_ids": {KEY_IDS: [], KEY_ERRORS: ["empty file"]},
    "multi-column.usdb_ids": {KEY_IDS: [], KEY_ERRORS: ["Invalid USDB ID in file"]},
    "ids.json": {KEY_IDS: [SongId(1), SongId(11586), SongId(3)], KEY_ERRORS: []},
    "ids_LF.json": {KEY_IDS: [SongId(1), SongId(24112), SongId(3)], KEY_ERRORS: []},
    "ids_inline.json": {KEY_IDS: [SongId(1), SongId(29020), SongId(3)], KEY_ERRORS: []},
    "macos-weblink.webloc": {KEY_IDS: [SongId(25930)], KEY_ERRORS: []},
    "linux-weblink.desktop": {KEY_IDS: [SongId(17590)], KEY_ERRORS: []},
}


def test_import_song_ids_from_files(resource_dir: str) -> None:
    for file, expected in ids_per_file.items():
        path = os.path.join(resource_dir, "import", file)
        parser = USDBIDFileParser(path)
        assert parser.errors == expected[KEY_ERRORS], f"wrong errors from {file}"
        assert parser.ids == expected[KEY_IDS], f"wrong songids from {file}"
