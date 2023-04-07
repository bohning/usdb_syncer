"""Meta data about the synchronization state of a USDB song."""

from __future__ import annotations

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
    resource: str | None = None

    @classmethod
    def new(cls, path: Path, resource: str | None = None) -> FileMeta:
        return cls(path.name, os.path.getmtime(path), resource)

    @classmethod
    def from_nested_dict(cls, dct: Any) -> FileMeta | None:
        if dct:
            return cls(**dct)
        return None


@attrs.define
class SyncMeta:
    """Meta data about the synchronization state of a USDB song."""

    song_id: SongId
    meta_tags: MetaTags
    txt: FileMeta | None = None
    audio: FileMeta | None = None
    video: FileMeta | None = None
    cover: FileMeta | None = None
    background: FileMeta | None = None
    version: int = SYNC_META_VERSION

    @classmethod
    def new(cls, song_id: SongId, meta_tags: MetaTags) -> SyncMeta:
        return cls(song_id, meta_tags)

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
            meta_tags=MetaTags.parse(dct["meta_tags"], _logger),
            txt=FileMeta.from_nested_dict(dct["txt"]),
            audio=FileMeta.from_nested_dict(dct["audio"]),
            video=FileMeta.from_nested_dict(dct["video"]),
            cover=FileMeta.from_nested_dict(dct["cover"]),
            background=FileMeta.from_nested_dict(dct["background"]),
        )

    def to_file(self, directory: Path) -> None:
        path = directory.joinpath(f"{self.song_id}.usdb")
        with path.open("w", encoding="utf8") as file:
            json.dump(self, file, cls=SyncMetaEncoder)

    def set_txt_meta(self, path: Path) -> None:
        self.txt = FileMeta.new(path)

    def set_audio_meta(self, path: Path, resource: str) -> None:
        self.audio = FileMeta.new(path, resource)

    def set_video_meta(self, path: Path, resource: str) -> None:
        self.video = FileMeta.new(path, resource)

    def set_cover_meta(self, path: Path, resource: str) -> None:
        self.cover = FileMeta.new(path, resource)

    def set_background_meta(self, path: Path, resource: str) -> None:
        self.background = FileMeta.new(path, resource)

    def local_audio_resource(self, folder: Path) -> str | None:
        return _local_resource(self.audio, folder)

    def local_video_resource(self, folder: Path) -> str | None:
        return _local_resource(self.video, folder)

    def local_cover_resource(self, folder: Path) -> str | None:
        return _local_resource(self.cover, folder)

    def local_background_resource(self, folder: Path) -> str | None:
        return _local_resource(self.background, folder)


def _local_resource(meta: FileMeta | None, folder: Path) -> str | None:
    """Returns the name of the resource, if it exists in the given folder
    and is in sync.
    """
    if meta:
        if (path := folder.joinpath(meta.fname)).exists():
            if os.path.getmtime(path) == meta.mtime:
                return meta.resource
    return None


class SyncMetaEncoder(json.JSONEncoder):
    """Custom JSON encoder"""

    def default(self, o: Any) -> Any:
        if isinstance(o, (SyncMeta, FileMeta)):
            return attrs.asdict(o, recurse=False)
        if isinstance(o, MetaTags):
            return str(o)
        return super().default(o)
