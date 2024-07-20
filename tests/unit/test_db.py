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
