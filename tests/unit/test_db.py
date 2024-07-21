"""Database tests."""

from pathlib import Path

import attrs

from usdb_syncer import db
from usdb_syncer.usdb_song import UsdbSong


def test_persisting_usdb_song(song: UsdbSong) -> None:
    db.connect(":memory:")
    song.upsert()
    db.reset_active_sync_metas(Path("C:"))
    db_song = UsdbSong.get(song.song_id)

    assert db_song
    assert attrs.asdict(song) == attrs.asdict(db_song)


def test_persisting_saved_search() -> None:
    search = db.SearchBuilder(
        order=db.SongOrder.ARTIST,
        text="foo bar",
        genres=["Rock", "Pop"],
        views=[(0, 100)],
        years=[1990, 2000, 2010],
    )
    db.connect(":memory:")
    search.upsert("name")
    saved = db.load_saved_searches()
    assert len(saved) == 1
    assert saved[0][0] == "name"
    assert search == saved[0][1]
