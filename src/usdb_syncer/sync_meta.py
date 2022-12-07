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
class SyncMeta:
    """Meta data about the synchronization state of a USDB song."""

    song_id: SongId
    # Sha1 hash as a hex str
    txt_hash: str
    version: int = SYNC_META_VERSION

    @classmethod
    def new(cls, song_id: SongId, txt: str) -> SyncMeta:
        return cls(song_id, hash_txt(txt))

    @classmethod
    def try_from_file(cls, path: str) -> SyncMeta | None:
        id_str = os.path.basename(path).removesuffix(".usdb")
        if not (song_id := SongId.parse(id_str)):
            return None
        with open(path, encoding="utf8") as file:
            try:
                dct = json.load(file)
                if int(dct["version"]) > SYNC_META_VERSION:
                    _logger.error("cannot read data written by a later version")
                    return None
                return cls(song_id, dct["txt_hash"])
            except (json.decoder.JSONDecodeError, TypeError, KeyError, ValueError):
                return None

    def to_file(self, directory: str) -> None:
        path = os.path.join(directory, f"{self.song_id}.usdb")
        with open(path, "w", encoding="utf8") as file:
            json.dump(self, file, cls=SyncMetaEncoder)

    def update_txt_hash(self, new_txt: str) -> bool:
        """True if hash was changed."""
        new_hash = hash_txt(new_txt)
        changed = self.txt_hash != new_hash
        self.txt_hash = new_hash
        return changed


def hash_txt(txt: str) -> str:
    hasher = hashlib.sha1()
    hasher.update(txt.encode("raw_unicode_escape"))
    return hasher.digest().hex()


class SyncMetaEncoder(json.JSONEncoder):
    """Custom JSON encoder"""

    def default(self, o: Any) -> Any:
        if isinstance(o, SyncMeta):
            dct = attrs.asdict(o, recurse=False)
            del dct["song_id"]
            return dct
        return super().default(o)
