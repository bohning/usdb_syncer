"""Tests for importing and exporting USDB IDs"""

import os

from usdb_syncer import SongId
from usdb_syncer.exchange_format import get_song_ids_from_files

ids_per_file: dict[str, list[SongId]] = {
    "youtube.url": [],
    "piano_man.url": [SongId(3327)],
    "ids.csv": [
        SongId(1),
        SongId(29020),
        SongId(3),
        SongId(10396),
        SongId(117),
        SongId(11111),
    ],
    "empty.csv": [],
    "multi-column.csv": [SongId(1), SongId(29020), SongId(3)],
}


def test_import_song_ids_from_files(resource_dir: str) -> None:
    for file, expected_ids in ids_per_file.items():
        path = os.path.join(resource_dir, "import", file)
        assert (
            get_song_ids_from_files(path) == expected_ids
        ), f"wrong songids from {file}"
