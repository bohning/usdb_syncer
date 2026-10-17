"""Database tests."""

from __future__ import annotations

import copy
from pathlib import Path

import attrs
import pytest

from usdb_syncer import SongId, SyncMetaId, db
from usdb_syncer.db import JobStatus
from usdb_syncer.meta_tags import MetaTags
from usdb_syncer.sync_meta import Resource, ResourceFileImage, SyncMeta
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


def test_persisting_image_dimensions(song: UsdbSong) -> None:
    assert song.sync_meta
    song.sync_meta.cover = Resource(
        JobStatus.SUCCESS,
        ResourceFileImage(
            "cover.jpg", 0, "https://example.com/cover.jpg", width=640, height=480
        ),
    )
    with db.managed_connection(":memory:"):
        song.upsert()
        db.reset_active_sync_metas(Path("C:"))
        loaded = SyncMeta.from_db_row(db.get_in_folder(song.sync_meta.path.parent)[0])
        row = db.get_usdb_song(song.song_id)
        assert row
        db_song = UsdbSong.from_db_row(song.song_id, row)
        image_rows = (
            db._DbState.connection()
            .execute("SELECT kind, width, height FROM image_dimensions")
            .fetchall()
        )
        assert song.sync_meta.cover
        cover_file = song.sync_meta.cover.file
        assert isinstance(cover_file, ResourceFileImage)
        cover_file.width = None
        cover_file.height = None
        song.upsert()
        cleared_image_rows = (
            db._DbState.connection()
            .execute("SELECT kind, width, height FROM image_dimensions")
            .fetchall()
        )

    assert loaded.cover and isinstance(loaded.cover.file, ResourceFileImage)
    assert loaded.cover.file.width == 640
    assert loaded.cover.file.height == 480
    assert db_song.sync_meta and db_song.sync_meta.cover
    assert isinstance(db_song.sync_meta.cover.file, ResourceFileImage)
    assert db_song.sync_meta.cover.file.width == 640
    assert db_song.sync_meta.cover.file.height == 480
    assert image_rows == [("cover", 640, 480)]
    assert cleared_image_rows == []


def test_cover_order_sorts_by_status_then_image_size(song: UsdbSong) -> None:
    songs = []
    for song_id, status, width, height in (
        (SongId(1), JobStatus.SUCCESS, 200, 100),
        (SongId(2), JobStatus.FAILURE, 1000, 1000),
        (SongId(3), JobStatus.SUCCESS, 640, 480),
    ):
        item = copy.copy(song)
        item.song_id = song_id
        item.sync_meta = SyncMeta(
            SyncMetaId.new(),
            song_id,
            0,
            Path(f"C:/{song_id}"),
            0,
            MetaTags(),
            cover=Resource(
                status,
                ResourceFileImage(
                    f"{song_id}.jpg",
                    0,
                    f"https://example.com/{song_id}.jpg",
                    width=width,
                    height=height,
                ),
            ),
        )
        songs.append(item)

    with db.managed_connection(":memory:"):
        for item in songs:
            item.upsert()
        db.reset_active_sync_metas(Path("C:"))
        sorted_ids = list(
            db.search_usdb_songs(db.SearchBuilder(order=db.SongOrder.COVER))
        )

    assert sorted_ids == [SongId(2), SongId(1), SongId(3)]


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
