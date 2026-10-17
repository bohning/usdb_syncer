"""Tests for song status tooltips."""

from pathlib import Path

from usdb_syncer.db import JobStatus
from usdb_syncer.gui.song_table.table_model import status_tooltip
from usdb_syncer.sync_meta import Resource, ResourceFile, ResourceFileImage


def test_status_tooltip_shows_image_dimensions(tmp_path: Path) -> None:
    image = ResourceFileImage(
        "cover.jpg", 0, "https://example.com/cover.jpg", width=640, height=480
    )
    image._is_in_sync = True

    tooltip = status_tooltip(Resource(JobStatus.SUCCESS, image), tmp_path)

    assert tooltip == "cover.jpg (640x480)"


def test_status_tooltip_omits_unavailable_image_dimensions(tmp_path: Path) -> None:
    image = ResourceFileImage("cover.jpg", 0, "https://example.com/cover.jpg")
    image._is_in_sync = True

    tooltip = status_tooltip(Resource(JobStatus.SUCCESS, image), tmp_path)

    assert tooltip == "cover.jpg"


def test_status_tooltip_omits_dimensions_for_non_image_resources(
    tmp_path: Path,
) -> None:
    file = ResourceFile("song.mp3", 0, "https://example.com/song.mp3")
    file._is_in_sync = True

    tooltip = status_tooltip(Resource(JobStatus.SUCCESS, file), tmp_path)

    assert tooltip == "song.mp3"
