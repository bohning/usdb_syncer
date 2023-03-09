"""Tests for importing and exporting USDB IDs"""

import os

from usdb_syncer import SongId
from usdb_syncer.exchange_format import USDBIDFileParser

KEY_IDS = "ids"
KEY_ERRORS = "errors"

ids_per_file: dict[str, dict] = {
    "broken_format.desktop": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing a section header"],
    },
    "broken_format.url": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing a section header"],
    },
    "broken_format.webloc": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing tag 'plist'"],
    },
    "broken_usdb_link.desktop": {
        KEY_IDS: [],
        KEY_ERRORS: [
            "Found URL has no query parameters: http://usdb.animux.de/index.phid=118"
        ],
    },
    "broken_usdb_link.url": {
        KEY_IDS: [],
        KEY_ERRORS: [
            "Found URL has no query parameters: http://usdb.animux.de/index.phid=118"
        ],
    },
    "broken_usdb_link.webloc": {
        KEY_IDS: [],
        KEY_ERRORS: [
            "Found URL has no query parameters: http://usdb.animux.de/index.phid=118"
        ],
    },
    "dublicate_url_key.desktop": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing or dublicate option"],
    },
    "dublicate_url_key.url": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing or dublicate option"],
    },
    "dublicate_url_key.webloc": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: multiple URLs detected"],
    },
    "empty.desktop": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing section 'Desktop Entry'"],
    },
    "empty.url": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing section 'InternetShortcut'"],
    },
    "empty.webloc": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing tag 'plist'"],
    },
    "missing_url_key.desktop": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing key 'URL'"],
    },
    "missing_url_key.url": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing key 'URL'"],
    },
    "missing_url_key.webloc": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing URL tag 'string'"],
    },
    "piano_man.desktop": {KEY_IDS: [SongId(3327)], KEY_ERRORS: []},
    "piano_man.url": {KEY_IDS: [SongId(3327)], KEY_ERRORS: []},
    "piano_man.webloc": {KEY_IDS: [SongId(3327)], KEY_ERRORS: []},
    "usdb_non_php.desktop": {KEY_IDS: [SongId(17590)], KEY_ERRORS: []},
    "usdb_non_php.url": {KEY_IDS: [SongId(26380)], KEY_ERRORS: []},
    "usdb_non_php.webloc": {KEY_IDS: [SongId(25930)], KEY_ERRORS: []},
    "usdb_http.desktop": {KEY_IDS: [SongId(279)], KEY_ERRORS: []},
    "usdb_http.url": {KEY_IDS: [SongId(279)], KEY_ERRORS: []},
    "usdb_http.webloc": {KEY_IDS: [SongId(279)], KEY_ERRORS: []},
    "usdb_short.desktop": {KEY_IDS: [SongId(1001)], KEY_ERRORS: []},
    "usdb_short.url": {KEY_IDS: [SongId(1001)], KEY_ERRORS: []},
    "usdb_short.webloc": {KEY_IDS: [SongId(1001)], KEY_ERRORS: []},
    "wrong_middle_level.webloc": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing tag 'dict'"],
    },
    "wrong_top_level.desktop": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing section 'Desktop Entry'"],
    },
    "wrong_top_level.url": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing section 'InternetShortcut'"],
    },
    "wrong_top_level.webloc": {
        KEY_IDS: [],
        KEY_ERRORS: ["invalid file format: missing tag 'plist'"],
    },
    "youtube.desktop": {
        KEY_IDS: [],
        KEY_ERRORS: ["Found URL has invalid domain: www.youtube.com"],
    },
    "youtube.url": {
        KEY_IDS: [],
        KEY_ERRORS: ["Found URL has invalid domain: youtu.be"],
    },
    "youtube.webloc": {
        KEY_IDS: [],
        KEY_ERRORS: ["Found URL has invalid domain: www.youtube.com"],
    },
    "empty.usdb_ids": {KEY_IDS: [], KEY_ERRORS: ["empty file"]},
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
    "multi-column.usdb_ids": {KEY_IDS: [], KEY_ERRORS: ["Invalid USDB ID in file"]},
    "broken.json": {
        KEY_IDS: [],
        KEY_ERRORS: [
            "invalid JSON format: Expecting ',' delimiter: line 3 column 18 (char 23)"
        ],
    },
    "empty.json": {KEY_IDS: [], KEY_ERRORS: ["empty file"]},
    "empty_array.json": {KEY_IDS: [], KEY_ERRORS: ["Empty JSON array"]},
    "ids.json": {KEY_IDS: [SongId(1), SongId(11586), SongId(3)], KEY_ERRORS: []},
    "ids_inline.json": {KEY_IDS: [SongId(1), SongId(29020), SongId(3)], KEY_ERRORS: []},
    "ids_LF.json": {KEY_IDS: [SongId(1), SongId(24112), SongId(3)], KEY_ERRORS: []},
    "missing_id_key.json": {
        KEY_IDS: [],
        KEY_ERRORS: ["Invalid or missing USDB ID in file"],
    },
}


def test_import_song_ids_from_files(resource_dir: str) -> None:
    for file, expected in ids_per_file.items():
        path = os.path.join(resource_dir, "import", file)
        parser = USDBIDFileParser(path)
        assert parser.errors == expected[KEY_ERRORS], f"wrong errors from {file}"
        assert parser.ids == expected[KEY_IDS], f"wrong songids from {file}"
