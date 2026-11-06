"""Settings tests."""

from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings

from usdb_syncer import db, settings

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@pytest.fixture
def isolated_qsettings(tmp_path: Path) -> Generator[Path, None, None]:
    """Redirect all QSettings I/O to a per-test temp dir."""
    old_format = QSettings.defaultFormat()

    # On Windows the default is the registry; force INI so setPath() applies.
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    for fmt in (QSettings.Format.IniFormat, QSettings.Format.NativeFormat):
        for scope in (QSettings.Scope.UserScope, QSettings.Scope.SystemScope):
            QSettings.setPath(fmt, scope, str(tmp_path))

    yield tmp_path

    QSettings.setDefaultFormat(old_format)
    settings.reset()
    settings._TemporarySettings._temporary_settings.clear()


@pytest.mark.parametrize(("temp"), [True, False])
def test_persisting_saved_search(temp: bool, isolated_qsettings: Path) -> None:
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
    search.insert(temp=temp)
    saved = settings.get_saved_searches()
    assert len(saved) == 1
    assert search.name == "name"
    assert saved[0] == search

    search2 = copy.copy(search)
    search2.insert(temp=temp)
    assert search2.name == "name (1)"
    assert len(settings.get_saved_searches()) == 2

    search2.update(new_name="name", temp=temp)
    assert search2.name == "name (1)"
    assert len(settings.get_saved_searches()) == 2


def test_saved_search_json_round_trip() -> None:
    """Saved searches must be (de)serializable from builtin types only.

    Newer PySide6 versions refuse to deserialize pickled user types from QSettings.
    """
    for order in (db.SongOrder.ARTIST, db.CustomSongOrder("custom_key")):
        search = settings.SavedSearch(
            name="name",
            search=db.SearchBuilder(
                order=order,
                descending=True,
                text="foo bar",
                ratings=[3.5],
                statuses=[db.DownloadStatus.SYNCHRONIZED, db.DownloadStatus.FAILED],
                views=[(0, 100), (5, None)],
                years=[1990, 2000],
                genres=["Rock", "Pop"],
                golden_notes=True,
            ),
            subscribed=True,
        )
        search.search.custom_data["key"].append("value")

        restored = settings.SavedSearch.from_dict(
            json.loads(json.dumps(search.to_dict()))
        )

        assert restored == search
        assert restored.search.custom_data["missing"] == []
