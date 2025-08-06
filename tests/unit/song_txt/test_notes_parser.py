"""Tests for functions from the note_utils module."""

from pathlib import Path

from usdb_syncer.download_options import TxtOptions
from usdb_syncer.logger import logger
from usdb_syncer.settings import (
    Encoding,
    FixLinebreaks,
    FixSpaces,
    FixTitleCase,
    FormatVersion,
    Newline,
)
from usdb_syncer.song_txt import SongTxt


def test_notes_parser_normalized(resource_dir: str) -> None:
    folder = Path(resource_dir, "txt", "normalized")
    for path in folder.glob("*.txt"):
        with path.open(encoding="utf-8") as file:
            contents = file.read()
        txt = SongTxt.try_parse(contents, logger)
        assert str(txt) == contents, f"failed test for '{path}'"


def test_notes_parser_deviant(resource_dir: str) -> None:
    folder = Path(resource_dir, "txt", "deviant")
    for path in folder.glob("*_in.txt"):
        with path.open(encoding="utf-8") as file:
            contents = file.read()
        out_path = path.with_name(path.name.replace("_in.txt", "_out.txt"))
        with out_path.open(encoding="utf-8") as file:
            out = file.read()
        txt = SongTxt.try_parse(contents, logger)
        assert str(txt) == out, f"failed test for '{path}'"


def test_notes_parser_fixes(resource_dir: str) -> None:
    folder = Path(resource_dir, "txt", "fixes")
    for path in folder.glob("*_in.txt"):
        with path.open(encoding="utf-8") as file:
            contents = file.read()
        out_path = path.with_name(path.name.replace("_in.txt", "_out.txt"))
        with out_path.open(encoding="utf-8") as file:
            out = file.read()
        txt = SongTxt.parse(contents, logger)
        txt.fix(
            TxtOptions(
                encoding=Encoding.UTF_8,
                newline=Newline.CRLF,
                format_version=FormatVersion.V1_0_0,
                fix_title_case=FixTitleCase.DISABLE,
                fix_linebreaks=FixLinebreaks.USDX_STYLE,
                fix_first_words_capitalization=True,
                fix_spaces=FixSpaces.AFTER,
                fix_quotation_marks=True,
            )
        )
        assert str(txt) == out, f"failed test for '{path}'"


def test_notes_parser_invalid(resource_dir: str) -> None:
    folder = Path(resource_dir, "txt", "invalid")
    for path in folder.glob("*.txt"):
        with path.open(encoding="utf-8") as file:
            contents = file.read()
        txt = SongTxt.try_parse(contents, logger)
        assert txt is None, f"failed test for '{path}'"
