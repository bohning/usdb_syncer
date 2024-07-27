"""`PathTemplate` tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from usdb_syncer.path_template import (
    InvalidCharError,
    NotEnoughComponentsError,
    PathTemplate,
    UnknownPlaceholderError,
)
from usdb_syncer.usdb_song import UsdbSong


def test_parse_path_template(song: UsdbSong) -> None:
    path = PathTemplate.parse(":year: // / :artist: - :title: \\").evaluate(song)
    assert path == Path(str(song.year), f"{song.artist} - {song.title}")


@pytest.mark.parametrize("char", '?:"<>|*.')
def test_parse_path_template_raises_forbidden_char_error(char: str) -> None:
    with pytest.raises(InvalidCharError) as error:
        PathTemplate.parse(f":artist: {char} :title: / song")
    assert error.value.char == char


@pytest.mark.parametrize("name", ("", "foo", "artists"))
def test_parse_path_template_raises_unknown_name_error(name: str) -> None:
    with pytest.raises(UnknownPlaceholderError) as error:
        PathTemplate.parse(f":{name}: / :title:")
    assert error.value.name == name


@pytest.mark.parametrize("template", ("", ":title:", "/ :title: / "))
def test_parse_path_template_raises_not_enough_components_error(template: str) -> None:
    with pytest.raises(NotEnoughComponentsError):
        PathTemplate.parse(template)
