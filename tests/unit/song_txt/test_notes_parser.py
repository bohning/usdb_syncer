"""Tests for functions from the note_utils module."""

import os
from glob import glob

from usdb_syncer.logger import get_logger
from usdb_syncer.song_txt import SongTxt

_logger = get_logger(__file__)


def test_notes_parser_normalized(resource_dir: str) -> None:
    folder = os.path.join(resource_dir, "txt", "normalized")
    for path in glob(f"{folder}/*.txt"):
        with open(path, encoding="utf-8") as file:
            contents = file.read()
        txt = SongTxt.try_parse(contents, _logger)
        assert str(txt) == contents, f"failed test for '{path}'"


def test_notes_parser_deviant(resource_dir: str) -> None:
    folder = os.path.join(resource_dir, "txt", "deviant")
    for path in glob(f"{folder}/*_in.txt"):
        with open(path, encoding="utf-8") as file:
            contents = file.read()
        with open(path.replace("_in.txt", "_out.txt"), encoding="utf-8") as file:
            out = file.read()
        txt = SongTxt.try_parse(contents, _logger)
        assert str(txt) == out, f"failed test for '{path}'"


def test_notes_parser_fixes(resource_dir: str) -> None:
    folder = os.path.join(resource_dir, "txt", "fixes")
    for path in glob(f"{folder}/*_in.txt"):
        with open(path, encoding="utf-8") as file:
            contents = file.read()
        with open(path.replace("_in.txt", "_out.txt"), encoding="utf-8") as file:
            out = file.read()
        txt = SongTxt.parse(contents, _logger)
        txt.fix()
        assert str(txt) == out, f"failed test for '{path}'"


def test_notes_parser_invalid(resource_dir: str) -> None:
    folder = os.path.join(resource_dir, "txt", "invalid")
    for path in glob(f"{folder}/*.txt"):
        with open(path, encoding="utf-8") as file:
            contents = file.read()
        txt = SongTxt.try_parse(contents, _logger)
        assert txt is None, f"failed test for '{path}'"
