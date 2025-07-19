"""Database tests."""

from pathlib import Path

import attrs
import pytest

from usdb_syncer import SongId, SyncMetaId, db
from usdb_syncer.usdb_song import UsdbSong

PERFORMANCE_TEST_ITEM_COUNT = 100000


def test_persisting_usdb_song(song: UsdbSong) -> None:
    with db.managed_connection(":memory:"):
        song.upsert()
        db.reset_active_sync_metas(Path("C:"))
        db_song = UsdbSong.get(song.song_id)

    assert db_song
    assert attrs.asdict(song) == attrs.asdict(db_song)


def test_persisting_saved_search() -> None:
    search = db.SavedSearch(
        name="name",
        search=db.SearchBuilder(
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


@pytest.mark.slow
def test_upsert_delete_sync_metas_many() -> None:
    """Test inserting and deleting many sync metas at once."""
    sync_meta_ids = [SyncMetaId.new() for _ in range(PERFORMANCE_TEST_ITEM_COUNT)]
    sync_meta_params = [
        db.SyncMetaParams(
            sync_meta_id=sync_meta_id,
            usdb_mtime=0,
            path=str(sync_meta_id),
            song_id=SongId(0),
            mtime=0,
            meta_tags="",
            pinned=False,
        )
        for sync_meta_id in sync_meta_ids
    ]
    with db.managed_connection(":memory:"):
        db.upsert_sync_metas(sync_meta_params)
        db.delete_sync_metas(tuple(sync_meta_ids))


@pytest.mark.slow
def test_upsert_delete_resource_files_many() -> None:
    """Test inserting and deleting many resource files at once."""
    sync_meta_ids = [SyncMetaId.new() for _ in range(PERFORMANCE_TEST_ITEM_COUNT)]
    resource_file_params = [
        db.ResourceFileParams(
            sync_meta_id=sync_meta_id,
            kind=db.ResourceFileKind.AUDIO,
            fname=str(sync_meta_id),
            mtime=0,
            resource="",
        )
        for sync_meta_id in sync_meta_ids
    ]
    with db.managed_connection(":memory:"):
        db.upsert_resource_files(resource_file_params)
        db.delete_resource_files(
            (sync_meta_id, db.ResourceFileKind.AUDIO) for sync_meta_id in sync_meta_ids
        )


@pytest.mark.slow
def test_upsert_delete_custom_metadata_many() -> None:
    """Test inserting and deleting many custom metadata at once."""
    sync_meta_ids = [SyncMetaId.new() for _ in range(PERFORMANCE_TEST_ITEM_COUNT)]
    custom_metadata_params = [
        db.CustomMetaDataParams(sync_meta_id=sync_meta_id, key="", value="")
        for sync_meta_id in sync_meta_ids
    ]
    with db.managed_connection(":memory:"):
        db.upsert_custom_meta_data(custom_metadata_params)
        db.delete_custom_meta_data(sync_meta_ids)
