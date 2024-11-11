"""Tests for functions from the note_utils module."""

import os
from glob import glob

from usdb_syncer.download_options import TxtOptions
from usdb_syncer.logger import logger
from usdb_syncer.settings import (
    Encoding,
    FixLinebreaks,
    FixSpaces,
    FormatVersion,
    Newline,
)
from usdb_syncer.song_txt import SongTxt


def test_notes_parser_normalized(resource_dir: str) -> None:
    folder = os.path.join(resource_dir, "txt", "normalized")
    for path in glob(f"{folder}/*.txt"):
        with open(path, encoding="utf-8") as file:
            contents = file.read()
        txt = SongTxt.try_parse(contents, logger)
        assert str(txt) == contents, f"failed test for '{path}'"


def test_notes_parser_deviant(resource_dir: str) -> None:
    folder = os.path.join(resource_dir, "txt", "deviant")
    for path in glob(f"{folder}/*_in.txt"):
        with open(path, encoding="utf-8") as file:
            contents = file.read()
        with open(path.replace("_in.txt", "_out.txt"), encoding="utf-8") as file:
            out = file.read()
        txt = SongTxt.try_parse(contents, logger)
        assert str(txt) == out, f"failed test for '{path}'"


def test_notes_parser_fixes(resource_dir: str) -> None:
    folder = os.path.join(resource_dir, "txt", "fixes")
    for path in glob(f"{folder}/*_in.txt"):
        with open(path, encoding="utf-8") as file:
            contents = file.read()
        with open(path.replace("_in.txt", "_out.txt"), encoding="utf-8") as file:
            out = file.read()
        txt = SongTxt.parse(contents, logger)
        txt.fix(
            TxtOptions(
                encoding=Encoding.UTF_8,
                newline=Newline.CRLF,
                format_version=FormatVersion.V1_0_0,
                fix_linebreaks=FixLinebreaks.USDX_STYLE,
                fix_first_words_capitalization=True,
                fix_spaces=FixSpaces.AFTER,
                fix_quotation_marks=True,
            )
        )
        assert str(txt) == out, f"failed test for '{path}'"


def test_notes_parser_invalid(resource_dir: str) -> None:
    folder = os.path.join(resource_dir, "txt", "invalid")
    for path in glob(f"{folder}/*.txt"):
        with open(path, encoding="utf-8") as file:
            contents = file.read()
        txt = SongTxt.try_parse(contents, logger)
        assert txt is None, f"failed test for '{path}'"
