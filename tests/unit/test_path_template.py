"""`PathTemplate` tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from usdb_syncer.path_template import (
    InvalidCharError,
    InvalidPlaceholderError,
    NotEnoughComponentsError,
    PathTemplate,
)
from usdb_syncer.usdb_song import UsdbSong


def test_parse_path_template(song: UsdbSong) -> None:
    assert song.sync_meta
    song.sync_meta.custom_data.set("key", "val")
    path = PathTemplate.parse(
        "songs/:*key:\\:year: // / :artist: - :title: \\"
    ).evaluate(song)
    assert path == Path("songs", "val", str(song.year), f"{song.artist} - {song.title}")


@pytest.mark.parametrize("char", '?:"<>|*.')
def test_parse_path_template_raises_forbidden_char_error(char: str) -> None:
    with pytest.raises(InvalidCharError) as error:
        PathTemplate.parse(f":artist: {char} :title: / song")
    assert error.value.char == char


@pytest.mark.parametrize("name", ("", "foo", "artists", "*"))
def test_parse_path_template_raises_unknown_name_error(name: str) -> None:
    with pytest.raises(InvalidPlaceholderError) as error:
        PathTemplate.parse(f":{name}: / :title:")
    assert error.value.name == name.removeprefix("*")


@pytest.mark.parametrize("template", ("", ":title:", "/ :title: / "))
def test_parse_path_template_raises_not_enough_components_error(template: str) -> None:
    with pytest.raises(NotEnoughComponentsError):
        PathTemplate.parse(template)
