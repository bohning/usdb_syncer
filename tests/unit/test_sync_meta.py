"""Tests for SyncMeta."""

import json
from pathlib import Path

from usdb_syncer.sync_meta import SyncMeta, SyncMetaEncoder


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
    meta_json = json.dumps(meta, cls=SyncMetaEncoder).replace(', "pinned": false', "")
    with path.open(encoding="utf-8") as file:
        assert file.read() == meta_json
