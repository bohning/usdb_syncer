"""Database tests."""

from __future__ import annotations

import copy
from pathlib import Path

import attrs
import pytest

from usdb_syncer import SongId, SyncMetaId, db
from usdb_syncer.db import JobStatus
from usdb_syncer.meta_tags import MetaTags
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.usdb_song import UsdbSong

PERFORMANCE_TEST_ITEM_COUNT = 100000


def _disable_foreign_keys() -> None:
    db._DbState.connection().execute("PRAGMA foreign_keys = OFF")


def test_persisting_usdb_song(song: UsdbSong) -> None:
    with db.managed_connection(":memory:"):
        song.upsert()
        db.reset_active_sync_metas(Path("C:"))
        db_song = UsdbSong.get(song.song_id)

    assert db_song
    assert attrs.asdict(song) == attrs.asdict(db_song)


def test_foreign_key_enforcement(song: UsdbSong) -> None:
    with db.managed_connection(":memory:"):
        song.upsert()
        assert len(list(db.all_local_usdb_songs())) == 1
        song.delete()
        assert len(list(db.all_local_usdb_songs())) == 0


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
        _disable_foreign_keys()
        db.upsert_sync_metas(sync_meta_params)
        db.delete_sync_metas(tuple(sync_meta_ids))


@pytest.mark.slow
def test_upsert_delete_resources_many() -> None:
    """Test inserting and deleting many resource files at once."""
    sync_meta_ids = [SyncMetaId.new() for _ in range(PERFORMANCE_TEST_ITEM_COUNT)]
    resource_file_params = [
        db.ResourceParams(
            sync_meta_id=sync_meta_id,
            kind=db.ResourceKind.AUDIO,
            fname=str(sync_meta_id),
            mtime=0,
            resource="",
            status=JobStatus.SUCCESS,
        )
        for sync_meta_id in sync_meta_ids
    ]
    with db.managed_connection(":memory:"):
        _disable_foreign_keys()
        db.upsert_resources(resource_file_params)
        db.delete_resources(
            (sync_meta_id, db.ResourceKind.AUDIO) for sync_meta_id in sync_meta_ids
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
        _disable_foreign_keys()
        db.upsert_custom_meta_data(custom_metadata_params)
        db.delete_custom_meta_data(sync_meta_ids)


def test_custom_data_order(song: UsdbSong) -> None:
    key = "key"
    song_1 = copy.copy(song)
    song_1.song_id = SongId(1)
    song_1.sync_meta = SyncMeta(
        SyncMetaId.new(), song_1.song_id, 0, Path("C:/1"), 0, MetaTags()
    )
    song_1.sync_meta.custom_data.set(key, "a")
    song_2 = copy.copy(song)
    song_2.song_id = SongId(2)
    song_2.sync_meta = SyncMeta(
        SyncMetaId.new(), song_2.song_id, 0, Path("C:/2"), 0, MetaTags()
    )
    song_2.sync_meta.custom_data.set(key, "b")
    with db.managed_connection(":memory:"):
        song.upsert()
        song_1.upsert()
        song_2.upsert()
        db.reset_active_sync_metas(Path("C:"))
        search = db.SearchBuilder(order=db.CustomSongOrder(key))
        ids_asc = list(db.search_usdb_songs(search))
        search.descending = True
        ids_desc = list(db.search_usdb_songs(search))
    assert ids_asc == [song_1.song_id, song_2.song_id, song.song_id]
    assert ids_desc == [song.song_id, song_2.song_id, song_1.song_id]
