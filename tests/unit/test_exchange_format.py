"""Tests for importing and exporting USDB IDs"""

import os

import pytest

from usdb_syncer import SongId
from usdb_syncer.exchange_format import (
    UsdbIdFileParser,
    UsdbIdFileParserEmptyFileError,
    UsdbIdFileParserEmptyJsonArrayError,
    UsdbIdFileParserInvalidFormatError,
    UsdbIdFileParserInvalidJsonError,
    UsdbIdFileParserInvalidUrlError,
    UsdbIdFileParserInvalidUsdbIdError,
    UsdbIdFileParserMissingOrDublicateOptionFormatError,
    UsdbIdFileParserMissingSectionHeaderFormatError,
    UsdbIdFileParserMultipleUrlsFormatError,
    UsdbIdFileParserNoJsonArrayError,
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
    assert not parser.errors, f"should have no errors from {file}"
    assert parser.ids == expected_ids, f"wrong songids from {file}"


@pytest.mark.parametrize(
    "file,expected_error_instances,expected_error_info",
    [
        (
            "broken_format.desktop",
            [UsdbIdFileParserMissingSectionHeaderFormatError],
            [""],
        ),
        ("broken_format.url", [UsdbIdFileParserMissingSectionHeaderFormatError], [""]),
        ("broken_format.webloc", [UsdbIdFileParserInvalidFormatError], ["plist"]),
        (
            "broken_usdb_link.desktop",
            [UsdbIdFileParserInvalidUrlError],
            ["http://usdb.animux.de/index.phid=118"],
        ),
        (
            "broken_usdb_link.url",
            [UsdbIdFileParserInvalidUrlError],
            ["http://usdb.animux.de/index.phid=118"],
        ),
        (
            "broken_usdb_link.webloc",
            [UsdbIdFileParserInvalidUrlError],
            ["http://usdb.animux.de/index.phid=118"],
        ),
        (
            "dublicate_url_key.desktop",
            [UsdbIdFileParserMissingOrDublicateOptionFormatError],
            [""],
        ),
        (
            "dublicate_url_key.url",
            [UsdbIdFileParserMissingOrDublicateOptionFormatError],
            [""],
        ),
        ("dublicate_url_key.webloc", [UsdbIdFileParserMultipleUrlsFormatError], [""]),
        ("empty.desktop", [UsdbIdFileParserEmptyFileError], [""]),
        ("empty.url", [UsdbIdFileParserEmptyFileError], [""]),
        ("empty.webloc", [UsdbIdFileParserEmptyFileError], [""]),
        ("missing_url_key.desktop", [UsdbIdFileParserInvalidFormatError], ["URL"]),
        ("missing_url_key.url", [UsdbIdFileParserInvalidFormatError], ["URL"]),
        ("missing_url_key.webloc", [UsdbIdFileParserInvalidFormatError], ["string"]),
        ("wrong_middle_level.webloc", [UsdbIdFileParserInvalidFormatError], ["dict"]),
        (
            "wrong_top_level.desktop",
            [UsdbIdFileParserInvalidFormatError],
            ["Desktop Entry"],
        ),
        (
            "wrong_top_level.url",
            [UsdbIdFileParserInvalidFormatError],
            ["InternetShortcut"],
        ),
        ("wrong_top_level.webloc", [UsdbIdFileParserInvalidFormatError], ["plist"]),
        ("youtube.desktop", [UsdbIdFileParserInvalidUrlError], ["www.youtube.com"]),
        ("youtube.url", [UsdbIdFileParserInvalidUrlError], ["youtu.be"]),
        ("youtube.webloc", [UsdbIdFileParserInvalidUrlError], ["www.youtube.com"]),
        ("empty.usdb_ids", [UsdbIdFileParserEmptyFileError], [""]),
        ("ids_and_other_stuff.usdb_ids", [UsdbIdFileParserInvalidUsdbIdError], [""]),
        ("multi-column.usdb_ids", [UsdbIdFileParserInvalidUsdbIdError], [""]),
        ("broken.json", [UsdbIdFileParserInvalidJsonError], [""]),
        ("empty.json", [UsdbIdFileParserEmptyFileError], [""]),
        ("empty_array.json", [UsdbIdFileParserEmptyJsonArrayError], [""]),
        ("no_array.json", [UsdbIdFileParserNoJsonArrayError], [""]),
        ("missing_id_key.json", [UsdbIdFileParserInvalidUsdbIdError], [""]),
    ],
)
def test_invalid_song_id_imports_from_files(
    resource_dir: str,
    file: str,
    expected_error_instances: list[
        UsdbIdFileParserEmptyFileError
        | UsdbIdFileParserEmptyJsonArrayError
        | UsdbIdFileParserInvalidFormatError
        | UsdbIdFileParserInvalidJsonError
        | UsdbIdFileParserInvalidUrlError
        | UsdbIdFileParserInvalidUsdbIdError
        | UsdbIdFileParserNoJsonArrayError
    ],
    expected_error_info: list[str],
) -> None:
    path = os.path.join(resource_dir, "import", file)
    parser = UsdbIdFileParser(path)
    assert len(expected_error_instances) == len(
        expected_error_info
    ), f"array missmatch in test parameters for {file}"
    assert len(parser.errors) == len(
        expected_error_instances
    ), f"unexpected error length in {file}"
    for count, error in enumerate(parser.errors):
        assert isinstance(
            error, expected_error_instances[count]
        ), f"wrong {count}. error from {file}"
        assert (
            expected_error_info[count] in error.message
        ), f"missing specific info in error message from {file}"
    assert not parser.ids, f"should have no songids from {file}"
