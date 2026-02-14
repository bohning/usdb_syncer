"""Settings tests."""

from __future__ import annotations

import copy

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
