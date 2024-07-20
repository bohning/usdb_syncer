"""This module contains pytest fixtures."""

from pathlib import Path

import pytest

from usdb_syncer import SongId, SyncMetaId
from usdb_syncer.meta_tags import MetaTags
from usdb_syncer.sync_meta import ResourceFile, SyncMeta
from usdb_syncer.usdb_song import UsdbSong


@pytest.fixture(scope="session", name="resource_dir")
def resource_dir_fixture() -> Path:
    """Returns the path to the test resource directory.

    Returns:
        Path: The resource directory path.
    """
    return Path(__file__).parent.joinpath("resources")


@pytest.fixture(name="song")
def usdb_song() -> UsdbSong:
    song_id = SongId(123)
    sync_meta_id = SyncMetaId.new()
    return UsdbSong(
        sample_url="",
        song_id=song_id,
        artist="Foo",
        title="Bar",
        genre="Pop",
        year=1999,
        language="Esperanto",
        creator="unknown",
        edition="",
        golden_notes=True,
        rating=0,
        views=1,
        sync_meta=SyncMeta(
            sync_meta_id=sync_meta_id,
            song_id=song_id,
            path=Path(f"C:/{sync_meta_id.to_filename()}"),
            mtime=0,
            meta_tags=MetaTags(),
            audio=ResourceFile("song.mp3", 1, "example.org/song.mp3"),
        ),
    )
