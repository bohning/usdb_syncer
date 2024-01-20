"""Tests for utils."""

from pathlib import Path

import pytest

from usdb_syncer.utils import extract_youtube_id, resource_file_ending

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
