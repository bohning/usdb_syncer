"""Meta data about the synchronization state of a USDB song."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import attrs

from usdb_syncer import SongId
from usdb_syncer.logger import get_logger

SYNC_META_VERSION = 1
_logger = get_logger(__file__)


@attrs.define
class FileMeta:
    """Meta data about a local file."""

    fname: str
    mtime: float

    @classmethod
    def from_path(cls, path: str) -> FileMeta:
        return cls(os.path.basename(path), os.path.getmtime(path))

    @classmethod
    def from_nested_dict(cls, dct: Any) -> FileMeta | None:
        if dct:
            return cls(**dct)
        return None


@attrs.define
class SyncMeta:
    """Meta data about the synchronization state of a USDB song."""

    song_id: SongId
    # Sha1 hash as a hex str
    src_txt_hash: str
    txt: FileMeta | None = None
    version: int = SYNC_META_VERSION

    @classmethod
    def new(cls, song_id: SongId, txt: str) -> SyncMeta:
        return cls(song_id, hash_txt(txt))

    @classmethod
    def try_from_file(cls, path: str) -> SyncMeta | None:
        with open(path, encoding="utf8") as file:
            try:
                return cls.from_dict(json.load(file))
            except (json.decoder.JSONDecodeError, TypeError, KeyError, ValueError):
                return None

    @classmethod
    def from_dict(cls, dct: Any) -> SyncMeta:
        if int(dct["version"]) > SYNC_META_VERSION:
            raise Exception("cannot read data written by a later version")
        return cls(
            SongId(dct["song_id"]),
            dct["src_txt_hash"],
            txt=FileMeta.from_nested_dict(dct["txt"]),
        )

    def to_file(self, directory: str) -> None:
        path = os.path.join(directory, f"{self.song_id}.usdb")
        with open(path, "w", encoding="utf8") as file:
            json.dump(self, file, cls=SyncMetaEncoder)

    def update_src_txt_hash(self, new_txt: str) -> bool:
        """True if hash was changed."""
        new_hash = hash_txt(new_txt)
        changed = self.src_txt_hash != new_hash
        self.src_txt_hash = new_hash
        return changed

    def set_txt_meta(self, path: str) -> None:
        self.txt = FileMeta.from_path(path)


def hash_txt(txt: str) -> str:
    hasher = hashlib.sha1()
    hasher.update(txt.encode("raw_unicode_escape"))
    return hasher.digest().hex()


class SyncMetaEncoder(json.JSONEncoder):
    """Custom JSON encoder"""

    def default(self, o: Any) -> Any:
        if isinstance(o, (SyncMeta, FileMeta)):
            return attrs.asdict(o, recurse=False)
        if isinstance(o, SongId):
            return o.value
        return super().default(o)
