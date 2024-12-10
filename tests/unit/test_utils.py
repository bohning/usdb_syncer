"""Tests for utils."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from usdb_syncer.constants import CLEANUP_DELETE_IMMEDIATELY_ENV_VAR
from usdb_syncer.utils import (
    extract_youtube_id,
    resource_file_ending,
    trash_or_delete_file_paths,
)

FAKE_YOUTUBE_ID = "fake_YT-id0"


def test_extract_youtube_id(resource_dir: Path) -> None:
    with resource_dir.joinpath("youtube_urls.txt").open(encoding="utf-8") as file:
        urls = file.read().splitlines()
    for url in urls:
        assert extract_youtube_id(url) == FAKE_YOUTUBE_ID


@pytest.mark.parametrize(
    "name,expected",
    [
        ("artist - title.mp3", ".mp3"),
        ("artist - title.mp3.m4a", ".m4a"),
        ("artist - title [BG].JPG", " [BG].JPG"),
    ],
)
def test_resource_file_ending(name: str, expected: str) -> None:
    assert resource_file_ending(name) == expected


@patch.dict(os.environ, {CLEANUP_DELETE_IMMEDIATELY_ENV_VAR: "True"})
@patch("usdb_syncer.utils.send2trash")
def test_trash_or_delete_file_paths_cleanup_immediately(
    send2trash_mock: MagicMock, tmp_path: Path
) -> None:
    path_1 = tmp_path / "foo.txt"
    path_2 = tmp_path / "foo"
    path_1.write_text("I am foo")
    path_2.mkdir()
    assert path_1.is_file()
    assert path_2.is_dir()
    trash_or_delete_file_paths(paths=[path_1, path_2])
    send2trash_mock.assert_not_called()
    assert not path_1.is_file()
    assert not path_2.is_dir()


@patch.dict(os.environ, clear=True)
@patch("usdb_syncer.utils.send2trash")
def test_trash_or_delete_file_paths_trash(send2trash_mock: MagicMock) -> None:
    path_1 = MagicMock()
    path_2 = MagicMock()
    trash_or_delete_file_paths(paths=[path_1, path_2])
    send2trash_mock.assert_called_once_with([path_1, path_2])
