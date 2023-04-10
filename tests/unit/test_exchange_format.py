"""Tests for importing and exporting USDB IDs"""

import os

import pytest

from usdb_syncer import SongId
from usdb_syncer.exchange_format import (
    UsdbIdFileParser,
    UsdbIdFileParserEmptyFileError,
    UsdbIdFileParserEmptyJsonArrayError,
    UsdbIdFileParserError,
    UsdbIdFileParserInvalidDomainMalformedUrlFormatError,
    UsdbIdFileParserInvalidJsonError,
    UsdbIdFileParserInvalidUsdbIdError,
    UsdbIdFileParserMissingKeyFormatError,
    UsdbIdFileParserMissingOrDublicateOptionFormatError,
    UsdbIdFileParserMissingSectionFormatError,
    UsdbIdFileParserMissingSectionHeaderFormatError,
    UsdbIdFileParserMissingTagFormatError,
    UsdbIdFileParserMissingUrlTagFormatError,
    UsdbIdFileParserMultipleUrlsFormatError,
    UsdbIdFileParserNoJsonArrayError,
    UsdbIdFileParserNoParametersMalformedUrlFormatError,
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
    parser = UsdbIdFileParser(path)
    assert not parser.error, f"should have no error from {file}"
    assert parser.ids == expected_ids, f"wrong songids from {file}"


@pytest.mark.parametrize(
    "file,expected_error",
    [
        ("broken_format.desktop", UsdbIdFileParserMissingSectionHeaderFormatError()),
        ("broken_format.url", UsdbIdFileParserMissingSectionHeaderFormatError()),
        ("broken_format.webloc", UsdbIdFileParserMissingTagFormatError("plist")),
        (
            "broken_usdb_link.desktop",
            UsdbIdFileParserNoParametersMalformedUrlFormatError(
                "http://usdb.animux.de/index.phid=118"
            ),
        ),
        (
            "broken_usdb_link.url",
            UsdbIdFileParserNoParametersMalformedUrlFormatError(
                "http://usdb.animux.de/index.phid=118"
            ),
        ),
        (
            "broken_usdb_link.webloc",
            UsdbIdFileParserNoParametersMalformedUrlFormatError(
                "http://usdb.animux.de/index.phid=118"
            ),
        ),
        (
            "dublicate_url_key.desktop",
            UsdbIdFileParserMissingOrDublicateOptionFormatError(),
        ),
        (
            "dublicate_url_key.url",
            UsdbIdFileParserMissingOrDublicateOptionFormatError(),
        ),
        ("dublicate_url_key.webloc", UsdbIdFileParserMultipleUrlsFormatError()),
        ("empty.desktop", UsdbIdFileParserEmptyFileError()),
        ("empty.url", UsdbIdFileParserEmptyFileError()),
        ("empty.webloc", UsdbIdFileParserEmptyFileError()),
        ("missing_url_key.desktop", UsdbIdFileParserMissingKeyFormatError("URL")),
        ("missing_url_key.url", UsdbIdFileParserMissingKeyFormatError("URL")),
        ("missing_url_key.webloc", UsdbIdFileParserMissingUrlTagFormatError("string")),
        ("wrong_middle_level.webloc", UsdbIdFileParserMissingTagFormatError("dict")),
        (
            "wrong_top_level.desktop",
            UsdbIdFileParserMissingSectionFormatError("Desktop Entry"),
        ),
        (
            "wrong_top_level.url",
            UsdbIdFileParserMissingSectionFormatError("InternetShortcut"),
        ),
        ("wrong_top_level.webloc", UsdbIdFileParserMissingTagFormatError("plist")),
        (
            "youtube.desktop",
            UsdbIdFileParserInvalidDomainMalformedUrlFormatError(
                "https://www.youtube.com/watch?v=IkLpSgnEqw4", "www.youtube.com"
            ),
        ),
        (
            "youtube.url",
            UsdbIdFileParserInvalidDomainMalformedUrlFormatError(
                "https://youtu.be/StZcUAPRRac", "youtu.be"
            ),
        ),
        (
            "youtube.webloc",
            UsdbIdFileParserInvalidDomainMalformedUrlFormatError(
                "https://www.youtube.com/watch?v=IkLpSgnEqw4", "www.youtube.com"
            ),
        ),
        ("empty.usdb_ids", UsdbIdFileParserEmptyFileError()),
        ("ids_and_other_stuff.usdb_ids", UsdbIdFileParserInvalidUsdbIdError()),
        ("multi-column.usdb_ids", UsdbIdFileParserInvalidUsdbIdError()),
        ("broken.json", UsdbIdFileParserInvalidJsonError()),
        ("empty.json", UsdbIdFileParserEmptyFileError()),
        ("empty_array.json", UsdbIdFileParserEmptyJsonArrayError()),
        ("no_array.json", UsdbIdFileParserNoJsonArrayError()),
        ("missing_id_key.json", UsdbIdFileParserMissingKeyFormatError("id")),
    ],
)
def test_invalid_song_id_imports_from_files(
    resource_dir: str, file: str, expected_error: UsdbIdFileParserError
) -> None:
    path = os.path.join(resource_dir, "import", file)
    parser = UsdbIdFileParser(path)
    assert repr(parser.error) == repr(expected_error), f"wrong error from {file}"
    assert not parser.ids, f"should have no songids from {file}"
