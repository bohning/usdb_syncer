"""Database tests."""

from pathlib import Path

import attrs

from usdb_syncer import db
from usdb_syncer.usdb_song import UsdbSong


def test_persisting_usdb_song(song: UsdbSong) -> None:
    with db.managed_connection(":memory:"):
        song.upsert()
        db.reset_active_sync_metas(Path("C:"))
        db_song = UsdbSong.get(song.song_id)

    assert db_song
    assert attrs.asdict(song) == attrs.asdict(db_song)


def test_persisting_saved_search() -> None:
    search = db.SavedSearch(
        "name",
        db.SearchBuilder(
            order=db.SongOrder.ARTIST,
            text="foo bar",
            genres=["Rock", "Pop"],
            views=[(0, 100)],
            years=[1990, 2000, 2010],
        ),
    )
    with db.managed_connection(":memory:"):
        search.insert()
        saved = list(db.SavedSearch.load_saved_searches())
        assert len(saved) == 1
        assert search.name == "name"
        assert saved[0] == search

        search.insert()
        assert search.name == "name (1)"
        assert len(list(db.SavedSearch.load_saved_searches())) == 2

        search.update(new_name="name")
        assert search.name == "name (1)"
        assert len(list(db.SavedSearch.load_saved_searches())) == 2
