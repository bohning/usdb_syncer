"""Tests for importing and exporting USDB IDs"""

import os

import pytest

from usdb_syncer import SongId
from usdb_syncer.exchange_format import (
    USDBIDFileParser,
    USDBIDFileParserEmptyFileError,
    USDBIDFileParserEmptyJSONArrayError,
    USDBIDFileParserInvalidFormatError,
    USDBIDFileParserInvalidJSONError,
    USDBIDFileParserInvalidURLError,
    USDBIDFileParserInvalidUSDBIDError,
    USDBIDFileParserMissingOrDublicateOptionFormatError,
    USDBIDFileParserMissingSectionHeaderFormatError,
    USDBIDFileParserMultipleURLsFormatError,
    USDBIDFileParserNoJSONArrayError,
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
    parser = USDBIDFileParser(path)
    assert not parser.errors, f"should have no errors from {file}"
    assert parser.ids == expected_ids, f"wrong songids from {file}"


@pytest.mark.parametrize(
    "file,expected_error_instances,expected_error_info",
    [
        (
            "broken_format.desktop",
            [USDBIDFileParserMissingSectionHeaderFormatError],
            [""],
        ),
        ("broken_format.url", [USDBIDFileParserMissingSectionHeaderFormatError], [""]),
        ("broken_format.webloc", [USDBIDFileParserInvalidFormatError], ["plist"]),
        (
            "broken_usdb_link.desktop",
            [USDBIDFileParserInvalidURLError],
            ["http://usdb.animux.de/index.phid=118"],
        ),
        (
            "broken_usdb_link.url",
            [USDBIDFileParserInvalidURLError],
            ["http://usdb.animux.de/index.phid=118"],
        ),
        (
            "broken_usdb_link.webloc",
            [USDBIDFileParserInvalidURLError],
            ["http://usdb.animux.de/index.phid=118"],
        ),
        (
            "dublicate_url_key.desktop",
            [USDBIDFileParserMissingOrDublicateOptionFormatError],
            [""],
        ),
        (
            "dublicate_url_key.url",
            [USDBIDFileParserMissingOrDublicateOptionFormatError],
            [""],
        ),
        ("dublicate_url_key.webloc", [USDBIDFileParserMultipleURLsFormatError], [""]),
        ("empty.desktop", [USDBIDFileParserEmptyFileError], [""]),
        ("empty.url", [USDBIDFileParserEmptyFileError], [""]),
        ("empty.webloc", [USDBIDFileParserEmptyFileError], [""]),
        ("missing_url_key.desktop", [USDBIDFileParserInvalidFormatError], ["URL"]),
        ("missing_url_key.url", [USDBIDFileParserInvalidFormatError], ["URL"]),
        ("missing_url_key.webloc", [USDBIDFileParserInvalidFormatError], ["string"]),
        ("wrong_middle_level.webloc", [USDBIDFileParserInvalidFormatError], ["dict"]),
        (
            "wrong_top_level.desktop",
            [USDBIDFileParserInvalidFormatError],
            ["Desktop Entry"],
        ),
        (
            "wrong_top_level.url",
            [USDBIDFileParserInvalidFormatError],
            ["InternetShortcut"],
        ),
        ("wrong_top_level.webloc", [USDBIDFileParserInvalidFormatError], ["plist"]),
        ("youtube.desktop", [USDBIDFileParserInvalidURLError], ["www.youtube.com"]),
        ("youtube.url", [USDBIDFileParserInvalidURLError], ["youtu.be"]),
        ("youtube.webloc", [USDBIDFileParserInvalidURLError], ["www.youtube.com"]),
        ("empty.usdb_ids", [USDBIDFileParserEmptyFileError], [""]),
        ("ids_and_other_stuff.usdb_ids", [USDBIDFileParserInvalidUSDBIDError], [""]),
        ("multi-column.usdb_ids", [USDBIDFileParserInvalidUSDBIDError], [""]),
        ("broken.json", [USDBIDFileParserInvalidJSONError], [""]),
        ("empty.json", [USDBIDFileParserEmptyFileError], [""]),
        ("empty_array.json", [USDBIDFileParserEmptyJSONArrayError], [""]),
        ("no_array.json", [USDBIDFileParserNoJSONArrayError], [""]),
        ("missing_id_key.json", [USDBIDFileParserInvalidUSDBIDError], [""]),
    ],
)
def test_invalid_song_id_imports_from_files(
    resource_dir: str,
    file: str,
    expected_error_instances: list[
        USDBIDFileParserEmptyFileError
        | USDBIDFileParserEmptyJSONArrayError
        | USDBIDFileParserInvalidFormatError
        | USDBIDFileParserInvalidJSONError
        | USDBIDFileParserInvalidURLError
        | USDBIDFileParserInvalidUSDBIDError
        | USDBIDFileParserNoJSONArrayError
    ],
    expected_error_info: list[str],
) -> None:
    path = os.path.join(resource_dir, "import", file)
    parser = USDBIDFileParser(path)
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
