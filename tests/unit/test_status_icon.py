"""Tests for song resource status icons."""

from pathlib import Path

import pytest

from usdb_syncer import settings
from usdb_syncer.db import JobStatus
from usdb_syncer.gui.icons import Icon
from usdb_syncer.gui.song_table import column as song_table_column
from usdb_syncer.gui.song_table.column import Column, status_icon
from usdb_syncer.sync_meta import Resource, ResourceFileImage
from usdb_syncer.usdb_song import UsdbSong


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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    dimensions: tuple[int | None, int | None],
    expected_ratio: tuple[int, int],
    expected_icon: Icon,
    job_status: JobStatus,
) -> None:
    monkeypatch.setattr(
        settings,
        "get_cover_quality_indicators",
        lambda: settings.CoverQualityIndicators.ENABLE_1000,
    )
    image_file = ResourceFileImage(
        "image.jpg",
        0,
        "https://example.com/image.jpg",
        width=dimensions[0],
        height=dimensions[1],
    )
    image_file._is_in_sync = True

    icon = status_icon(
        Resource(job_status, image_file),
        tmp_path,
        expected_ratio,
        quality_indicators_enabled=True,
    )

    assert icon is expected_icon


def test_status_icon_preserves_local_change_indicator_for_images(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        settings,
        "get_cover_quality_indicators",
        lambda: settings.CoverQualityIndicators.ENABLE_1000,
    )
    image_file = ResourceFileImage(
        "image.jpg", 0, "https://example.com/image.jpg", width=800, height=800
    )
    image_file._is_in_sync = False

    icon = status_icon(
        Resource(JobStatus.SUCCESS, image_file),
        tmp_path,
        (1, 1),
        quality_indicators_enabled=True,
    )

    assert icon is Icon.SUCCESS_CHANGES


@pytest.mark.parametrize(
    ("dimensions", "thresholds", "expected_ratio", "expected_icon"),
    [
        ((1000, 1000), ((1000, 1000), (500, 500)), (1, 1), Icon.SUCCESS),
        ((1200, 1000), ((1000, 1000), (500, 500)), (1, 1), Icon.SUCCESS_ASPECTRATIO),
        ((999, 999), ((1000, 1000), (500, 500)), (1, 1), Icon.SUCCESS_MEDIUM),
        (
            (999, 800),
            ((1000, 1000), (500, 500)),
            (1, 1),
            Icon.SUCCESS_MEDIUM_ASPECTRATIO,
        ),
        ((499, 499), ((1000, 1000), (500, 500)), (1, 1), Icon.SUCCESS_SMALL),
        ((1920, 1080), ((1920, 0), (960, 0)), (16, 9), Icon.SUCCESS),
        ((1919, 1080), ((1920, 0), (960, 0)), (16, 9), Icon.SUCCESS_MEDIUM_ASPECTRATIO),
        ((960, 500), ((1920, 0), (960, 0)), (16, 9), Icon.SUCCESS_MEDIUM_ASPECTRATIO),
        ((959, 1080), ((1920, 0), (960, 0)), (16, 9), Icon.SUCCESS_SMALL_ASPECTRATIO),
    ],
)
def test_status_icon_indicates_image_quality(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    dimensions: tuple[int, int],
    thresholds: tuple[tuple[int, int], tuple[int, int]],
    expected_ratio: tuple[int, int],
    expected_icon: Icon,
) -> None:
    monkeypatch.setattr(
        settings,
        "get_cover_quality_indicators",
        lambda: settings.CoverQualityIndicators.ENABLE_1000,
    )
    image_file = ResourceFileImage(
        "image.jpg",
        0,
        "https://example.com/image.jpg",
        width=dimensions[0],
        height=dimensions[1],
    )
    image_file._is_in_sync = True

    icon = status_icon(
        Resource(JobStatus.SUCCESS, image_file),
        tmp_path,
        expected_ratio,
        thresholds,
        quality_indicators_enabled=True,
    )

    assert icon is expected_icon


def test_status_icon_hides_aspect_ratio_indicator_when_quality_indicators_disabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image_file = ResourceFileImage(
        "image.jpg", 0, "https://example.com/image.jpg", width=800, height=600
    )
    image_file._is_in_sync = True

    icon = status_icon(
        Resource(JobStatus.SUCCESS, image_file),
        tmp_path,
        (1, 1),
        ((1000, 1000), (500, 500)),
    )

    assert icon is Icon.SUCCESS


@pytest.mark.parametrize(
    ("column", "cover_setting", "background_setting"),
    [
        (
            Column.COVER,
            settings.CoverQualityIndicators.DISABLE,
            settings.BackgroundQualityIndicators.ENABLE_1920,
        ),
        (
            Column.BACKGROUND,
            settings.CoverQualityIndicators.ENABLE_1000,
            settings.BackgroundQualityIndicators.DISABLE,
        ),
    ],
)
def test_image_column_uses_its_own_quality_indicator_setting(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    song: UsdbSong,
    column: Column,
    cover_setting: settings.CoverQualityIndicators,
    background_setting: settings.BackgroundQualityIndicators,
) -> None:
    monkeypatch.setattr(settings, "get_cover_quality_indicators", lambda: cover_setting)
    monkeypatch.setattr(
        settings, "get_background_quality_indicators", lambda: background_setting
    )
    image_file = ResourceFileImage(
        "image.jpg", 0, "https://example.com/image.jpg", width=800, height=600
    )
    image_file._is_in_sync = True
    resource = Resource(JobStatus.SUCCESS, image_file)
    assert song.sync_meta is not None
    song.sync_meta.path = tmp_path / "sync.json"
    song.sync_meta.cover = resource
    song.sync_meta.background = resource
    enabled_values: list[bool] = []

    def capture_quality_setting(*args: object, **kwargs: bool) -> Icon:
        enabled_values.append(kwargs["quality_indicators_enabled"])
        return Icon.SUCCESS

    monkeypatch.setattr(song_table_column, "status_icon", capture_quality_setting)
    monkeypatch.setattr(Icon, "icon", lambda _self, _theme=None: None)

    column.cell_decoration_data(song, settings.Theme.SYSTEM)

    assert enabled_values == [False]
