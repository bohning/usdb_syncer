"""Tests for song resource status icons."""

from pathlib import Path

import pytest

from usdb_syncer.db import JobStatus
from usdb_syncer.gui.icons import Icon
from usdb_syncer.gui.song_table.column import status_icon
from usdb_syncer.sync_meta import Resource, ResourceFileImage


@pytest.mark.parametrize(
    ("dimensions", "expected_ratio", "expected_icon"),
    [
        ((800, 800), (1, 1), Icon.SUCCESS),
        ((1920, 1080), (16, 9), Icon.SUCCESS),
        ((800, 600), (1, 1), Icon.SUCCESS_ASPECTRATIO),
        ((1920, 1200), (16, 9), Icon.SUCCESS_ASPECTRATIO),
        ((None, None), (16, 9), Icon.SUCCESS),
        ((800, None), (1, 1), Icon.SUCCESS),
        ((None, 800), (1, 1), Icon.SUCCESS),
    ],
)
@pytest.mark.parametrize("job_status", [JobStatus.SUCCESS, JobStatus.SUCCESS_UNCHANGED])
def test_status_icon_checks_image_ratio(
    tmp_path: Path,
    dimensions: tuple[int | None, int | None],
    expected_ratio: tuple[int, int],
    expected_icon: Icon,
    job_status: JobStatus,
) -> None:
    image_file = ResourceFileImage(
        "image.jpg",
        0,
        "https://example.com/image.jpg",
        width=dimensions[0],
        height=dimensions[1],
    )
    image_file._is_in_sync = True

    icon = status_icon(Resource(job_status, image_file), tmp_path, expected_ratio)

    assert icon is expected_icon


def test_status_icon_preserves_local_change_indicator_for_images(
    tmp_path: Path,
) -> None:
    image_file = ResourceFileImage(
        "image.jpg", 0, "https://example.com/image.jpg", width=800, height=800
    )
    image_file._is_in_sync = False

    icon = status_icon(Resource(JobStatus.SUCCESS, image_file), tmp_path, (1, 1))

    assert icon is Icon.SUCCESS_CHANGES
