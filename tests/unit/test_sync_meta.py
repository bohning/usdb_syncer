"""Tests for SyncMeta."""

import json
from pathlib import Path

from PIL import Image

from usdb_syncer.db import JobStatus
from usdb_syncer.sync_meta import (
    ImageResource,
    Resource,
    ResourceFileImage,
    SyncMeta,
    SyncMetaEncoder,
)
from usdb_syncer.usdb_song import UsdbSong


def test_v1_meta_file_roundtrip(resource_dir: Path) -> None:
    path = resource_dir.joinpath("meta_files", "-tDPmkDoxSc.usdb")
    meta = SyncMeta.try_from_file(path)
    assert meta
    meta_json = json.dumps(meta, cls=SyncMetaEncoder)
    with path.open(encoding="utf-8") as file:
        assert file.read() == meta_json


def test_pre_pin_v1_meta_file_roundtrip(resource_dir: Path) -> None:
    path = resource_dir.joinpath("meta_files", "r-Q6wyggsTg.usdb")
    meta = SyncMeta.try_from_file(path)
    assert meta
    meta_json = (
        json.dumps(meta, cls=SyncMetaEncoder)
        .replace(', "pinned": false', "")
        .replace(', "custom_data": {}', "")
        .replace(', "usdb_mtime": 0', "")
        .replace(', "status": "success"', "")
        .replace(', "vocals": null', "")
        .replace(', "instrumental": null', "")
    )
    with path.open(encoding="utf-8") as file:
        assert file.read() == meta_json


def test_image_dimensions_roundtrip_in_meta_file(
    song: UsdbSong, tmp_path: Path
) -> None:
    meta = song.sync_meta
    assert meta
    meta.path = tmp_path / meta.sync_meta_id.to_filename()
    meta.cover = Resource(
        JobStatus.SUCCESS,
        ResourceFileImage(
            "cover.jpg", 0, "https://example.com/cover.jpg", width=640, height=480
        ),
    )
    meta.synchronize_to_file()

    loaded = SyncMeta.try_from_file(meta.path)

    assert loaded and isinstance(loaded.cover, ImageResource)
    assert loaded.cover and isinstance(loaded.cover.file, ResourceFileImage)
    assert loaded.cover.file.width == 640
    assert loaded.cover.file.height == 480


def test_image_file_new_reads_dimensions(tmp_path: Path) -> None:
    path = tmp_path / "image.png"
    Image.new("RGB", (320, 240)).save(path)

    image = ResourceFileImage.new(path, "https://example.com/image.png")

    assert image.width == 320
    assert image.height == 240
