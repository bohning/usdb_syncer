"""Tests for utils."""

import os

from usdb_dl.utils import extract_youtube_id

FAKE_YOUTUBE_ID = "fake_YT-id0"


def test_extract_youtube_id(resource_dir: str) -> None:
    with open(os.path.join(resource_dir, "youtube_urls.txt"), encoding="utf-8") as file:
        urls = file.read().splitlines()
    for url in urls:
        assert extract_youtube_id(url) == FAKE_YOUTUBE_ID
