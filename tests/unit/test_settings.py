"""Settings tests."""

from __future__ import annotations

import copy
import json

from usdb_syncer import db, settings


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
