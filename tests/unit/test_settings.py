"""Settings tests."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

import pytest

from usdb_syncer import db, settings

if TYPE_CHECKING:
    from collections.abc import Callable


def test_persisting_saved_search() -> None:
    search = settings.SavedSearch(
        name="name",
        search=db.SearchBuilder(
            order=db.SongOrder.ARTIST,
            text="foo bar",
            genres=["Rock", "Pop"],
            views=[(0, 100)],
            years=[1990, 2000, 2010],
        ),
    )
    search.insert(temp=True)
    saved = settings.get_saved_searches()
    assert len(saved) == 1
    assert search.name == "name"
    assert saved[0] == search

    search2 = copy.copy(search)
    search2.insert(temp=True)
    assert search2.name == "name (1)"
    assert len(settings.get_saved_searches()) == 2

    search2.update(new_name="name", temp=True)
    assert search2.name == "name (1)"
    assert len(settings.get_saved_searches()) == 2


@pytest.mark.parametrize(
    ("get_setting", "set_setting", "enabled", "disabled"),
    [
        (
            settings.get_cover_quality_indicators,
            settings.set_cover_quality_indicators,
            settings.CoverQualityIndicators.ENABLE_1000,
            settings.CoverQualityIndicators.DISABLE,
        ),
        (
            settings.get_background_quality_indicators,
            settings.set_background_quality_indicators,
            settings.BackgroundQualityIndicators.ENABLE_1920,
            settings.BackgroundQualityIndicators.DISABLE,
        ),
    ],
)
def test_quality_indicator_settings_are_cached_and_invalidated(
    monkeypatch: pytest.MonkeyPatch,
    get_setting: Callable[..., object],
    set_setting: Callable[..., None],
    enabled: object,
    disabled: object,
) -> None:
    selected = enabled
    reads = 0

    def get(_key: settings.SettingKey, _default: object) -> object:
        nonlocal reads
        reads += 1
        return selected

    monkeypatch.setattr(settings._Settings, "get", get)
    monkeypatch.setattr(settings._Settings, "set", lambda *_args, **_kwargs: None)
    settings.get_cover_quality_indicators.cache_clear()
    settings.get_background_quality_indicators.cache_clear()
    try:
        assert get_setting() == enabled
        assert get_setting() == enabled
        assert reads == 1

        set_setting(disabled)
        selected = disabled
        assert get_setting() == disabled
        assert reads == 2
    finally:
        settings.get_cover_quality_indicators.cache_clear()
        settings.get_background_quality_indicators.cache_clear()


@pytest.mark.parametrize(
    ("indicators", "expected_thresholds"),
    [
        (settings.CoverQualityIndicators.DISABLE, None),
        (settings.CoverQualityIndicators.ENABLE_1000, ((1000, 1000), (500, 500))),
        (settings.BackgroundQualityIndicators.DISABLE, None),
        (settings.BackgroundQualityIndicators.ENABLE_1920, ((1920, 1080), (960, 540))),
    ],
)
def test_image_quality_indicator_thresholds(
    indicators: settings.CoverQualityIndicators | settings.BackgroundQualityIndicators,
    expected_thresholds: tuple[tuple[int, int], tuple[int, int]] | None,
) -> None:
    assert indicators.thresholds == expected_thresholds
