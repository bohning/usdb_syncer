"""Meta data about the synchronization state of a USDB song."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import attrs

from usdb_syncer import SongId
from usdb_syncer.logger import get_logger
from usdb_syncer.meta_tags import MetaTags

SYNC_META_VERSION = 1
_logger = get_logger(__file__)


@attrs.define
class FileMeta:
    """Meta data about a local file."""

    fname: str
    mtime: float

    @classmethod
    def from_path(cls, path: Path) -> FileMeta:
        return cls(path.name, os.path.getmtime(path))

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
    meta_tags: MetaTags
    txt: FileMeta | None = None
    audio: FileMeta | None = None
    video: FileMeta | None = None
    cover: FileMeta | None = None
    background: FileMeta | None = None
    version: int = SYNC_META_VERSION

    @classmethod
    def new(cls, song_id: SongId, txt: str, meta_tags: MetaTags) -> SyncMeta:
        return cls(song_id, hash_txt(txt), meta_tags)

    @classmethod
    def try_from_file(cls, path: Path) -> SyncMeta | None:
        with path.open(encoding="utf8") as file:
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
            src_txt_hash=dct["src_txt_hash"],
            meta_tags=MetaTags.parse(dct["meta_tags"], _logger),
            txt=FileMeta.from_nested_dict(dct["txt"]),
        )

    def to_file(self, directory: Path) -> None:
        path = directory.joinpath(f"{self.song_id}.usdb")
        with path.open("w", encoding="utf8") as file:
            json.dump(self, file, cls=SyncMetaEncoder)

    def update_src_txt_hash(self, new_txt: str) -> bool:
        """True if hash was changed."""
        new_hash = hash_txt(new_txt)
        changed = self.src_txt_hash != new_hash
        self.src_txt_hash = new_hash
        return changed

    def set_txt_meta(self, path: Path) -> None:
        self.txt = FileMeta.from_path(path)

    def set_audio_meta(self, path: Path) -> None:
        self.audio = FileMeta.from_path(path)

    def set_video_meta(self, path: Path) -> None:
        self.video = FileMeta.from_path(path)

    def set_cover_meta(self, path: Path) -> None:
        self.cover = FileMeta.from_path(path)

    def set_background_meta(self, path: Path) -> None:
        self.background = FileMeta.from_path(path)


def hash_txt(txt: str) -> str:
    hasher = hashlib.sha1()
    hasher.update(txt.encode("raw_unicode_escape"))
    return hasher.digest().hex()


class SyncMetaEncoder(json.JSONEncoder):
    """Custom JSON encoder"""

    def default(self, o: Any) -> Any:
        if isinstance(o, (SyncMeta, FileMeta)):
            return attrs.asdict(o, recurse=False)
        if isinstance(o, MetaTags):
            return str(o)
        return super().default(o)
