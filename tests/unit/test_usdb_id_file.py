"""Tests for importing and exporting USDB IDs"""

import os

import pytest

from usdb_syncer import SongId
from usdb_syncer.usdb_id_file import (
    UsdbIdFileEmptyFileError,
    UsdbIdFileEmptySongsArrayError,
    UsdbIdFileError,
    UsdbIdFileInvalidDomainMalformedUrlFormatError,
    UsdbIdFileInvalidJsonError,
    UsdbIdFileInvalidUsdbIdError,
    UsdbIdFileMissingKeyFormatError,
    UsdbIdFileMissingOrDuplicateOptionFormatError,
    UsdbIdFileMissingSectionFormatError,
    UsdbIdFileMissingSectionHeaderFormatError,
    UsdbIdFileMissingTagFormatError,
    UsdbIdFileMissingUrlTagFormatError,
    UsdbIdFileMultipleUrlsFormatError,
    UsdbIdFileNoParametersMalformedUrlFormatError,
    UsdbIdFileWrongJsonSongsFormatError,
    parse_usdb_id_file,
)


@pytest.mark.parametrize(
    "file,expected_ids",
    [
        ("piano_man.desktop", [SongId(3327)]),
        ("piano_man.url", [SongId(3327)]),
        ("piano_man.webloc", [SongId(3327)]),
        ("usdb_non_php.desktop", [SongId(17590)]),
        ("usdb_non_php.url", [SongId(26380)]),
        ("usdb_non_php.webloc", [SongId(25930)]),
        ("usdb_http.desktop", [SongId(279)]),
        ("usdb_http.url", [SongId(279)]),
        ("usdb_http.webloc", [SongId(279)]),
        ("usdb_short.desktop", [SongId(1001)]),
        ("usdb_short.url", [SongId(1001)]),
        ("usdb_short.webloc", [SongId(1001)]),
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
        ),
        ("ids.json", [SongId(1), SongId(11586), SongId(3)]),
        ("ids_inline.json", [SongId(1), SongId(29020), SongId(3)]),
        ("ids_LF.json", [SongId(1), SongId(24112), SongId(3)]),
    ],
)
def test_valid_song_id_imports_from_files(
    resource_dir: str, file: str, expected_ids: list[SongId]
) -> None:
    path = os.path.join(resource_dir, "import", file)
    song_ids = parse_usdb_id_file(path)
    assert song_ids == expected_ids, f"wrong songids from {file}"


@pytest.mark.parametrize(
    "file,expected_error",
    [
        ("broken_format.desktop", UsdbIdFileMissingSectionHeaderFormatError()),
        ("broken_format.url", UsdbIdFileMissingSectionHeaderFormatError()),
        ("broken_format.webloc", UsdbIdFileMissingTagFormatError("plist")),
        (
            "broken_usdb_link.desktop",
            UsdbIdFileNoParametersMalformedUrlFormatError(
                "http://usdb.animux.de/index.phid=118"
            ),
        ),
        (
            "broken_usdb_link.url",
            UsdbIdFileNoParametersMalformedUrlFormatError(
                "http://usdb.animux.de/index.phid=118"
            ),
        ),
        (
            "broken_usdb_link.webloc",
            UsdbIdFileNoParametersMalformedUrlFormatError(
                "http://usdb.animux.de/index.phid=118"
            ),
        ),
        ("duplicate_url_key.desktop", UsdbIdFileMissingOrDuplicateOptionFormatError()),
        ("duplicate_url_key.url", UsdbIdFileMissingOrDuplicateOptionFormatError()),
        ("duplicate_url_key.webloc", UsdbIdFileMultipleUrlsFormatError()),
        ("empty.desktop", UsdbIdFileEmptyFileError()),
        ("empty.url", UsdbIdFileEmptyFileError()),
        ("empty.webloc", UsdbIdFileEmptyFileError()),
        ("missing_url_key.desktop", UsdbIdFileMissingKeyFormatError("URL")),
        ("missing_url_key.url", UsdbIdFileMissingKeyFormatError("URL")),
        ("missing_url_key.webloc", UsdbIdFileMissingUrlTagFormatError("string")),
        ("wrong_middle_level.webloc", UsdbIdFileMissingTagFormatError("dict")),
        (
            "wrong_top_level.desktop",
            UsdbIdFileMissingSectionFormatError("Desktop Entry"),
        ),
        (
            "wrong_top_level.url",
            UsdbIdFileMissingSectionFormatError("InternetShortcut"),
        ),
        ("wrong_top_level.webloc", UsdbIdFileMissingTagFormatError("plist")),
        (
            "youtube.desktop",
            UsdbIdFileInvalidDomainMalformedUrlFormatError(
                "https://www.youtube.com/watch?v=IkLpSgnEqw4", "www.youtube.com"
            ),
        ),
        (
            "youtube.url",
            UsdbIdFileInvalidDomainMalformedUrlFormatError(
                "https://youtu.be/StZcUAPRRac", "youtu.be"
            ),
        ),
        (
            "youtube.webloc",
            UsdbIdFileInvalidDomainMalformedUrlFormatError(
                "https://www.youtube.com/watch?v=IkLpSgnEqw4", "www.youtube.com"
            ),
        ),
        ("empty.usdb_ids", UsdbIdFileEmptyFileError()),
        ("ids_and_other_stuff.usdb_ids", UsdbIdFileInvalidUsdbIdError()),
        ("multi-column.usdb_ids", UsdbIdFileInvalidUsdbIdError()),
        ("broken.json", UsdbIdFileInvalidJsonError()),
        ("empty.json", UsdbIdFileEmptyFileError()),
        ("empty_object.json", UsdbIdFileMissingKeyFormatError("songs")),
        ("empty_array.json", UsdbIdFileEmptySongsArrayError("songs")),
        ("no_array.json", UsdbIdFileWrongJsonSongsFormatError("songs")),
        ("missing_id_key.json", UsdbIdFileMissingKeyFormatError("id")),
        ("missing_top_structure.json", UsdbIdFileInvalidJsonError()),
        ("wrong_top_level.json", UsdbIdFileMissingKeyFormatError("songs")),
    ],
)
def test_invalid_song_id_imports_from_files(
    resource_dir: str, file: str, expected_error: UsdbIdFileError
) -> None:
    path = os.path.join(resource_dir, "import", file)
    with pytest.raises(type(expected_error)) as exc_info:
        song_ids = parse_usdb_id_file(path)
        assert exc_info.getrepr() == repr(expected_error), f"wrong error from {file}"
        assert not song_ids, f"should have no songids from {file}"
