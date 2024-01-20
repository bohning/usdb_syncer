"""Database tests."""

from pathlib import Path

import attrs

from usdb_syncer import SongId, SyncMetaId, db
from usdb_syncer.meta_tags import MetaTags
from usdb_syncer.sync_meta import ResourceFile, SyncMeta
from usdb_syncer.usdb_song import UsdbSong


def test_persisting_usdb_song() -> None:
    song = UsdbSong(
        song_id=SongId(123),
        artist="Foo",
        title="Bar",
        language="Esperanto",
        edition="",
        golden_notes=True,
        rating=0,
        views=1,
    )
    sync_meta_id = SyncMetaId.new()
    song.sync_meta = SyncMeta(
        sync_meta_id=sync_meta_id,
        song_id=song.song_id,
        path=Path(f"C:/{sync_meta_id.encode()}.usdb"),
        mtime=0,
        meta_tags=MetaTags(),
    )
    song.sync_meta.audio = ResourceFile("song.mp3", 1, "example.org/song.mp3")

    db.connect(":memory:")
    song.upsert()
    db.reset_active_sync_metas(Path("C:"))
    db_song = UsdbSong.get(song.song_id)

    assert db_song
    assert attrs.asdict(song) == attrs.asdict(db_song)
