"""Meta data about the synchronization state of a USDB song."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator

import attrs

from usdb_syncer import SongId
from usdb_syncer.constants import Usdb
from usdb_syncer.logger import get_logger
from usdb_syncer.meta_tags import MetaTags

SYNC_META_VERSION = 1
_logger = get_logger(__file__)


class SyncMetaTooNewError(Exception):
    """Raised when trying to decode meta info from an incompatible future release."""

    def __str__(self) -> str:
        return "cannot read sync meta written by a future release"


@attrs.define
class FileMeta:
    """Meta data about a local file."""

    fname: str
    mtime: float
    resource: str

    @classmethod
    def new(cls, path: Path, resource: str) -> FileMeta:
        return cls(path.name, os.path.getmtime(path), resource)

    @classmethod
    def from_nested_dict(cls, dct: Any) -> FileMeta | None:
        if dct:
            return cls(**dct)
        return None

    def is_in_sync(self, folder: Path) -> bool:
        """True if this file exists in the given folder and is in sync."""
        path = folder.joinpath(self.fname)
        return path.exists() and os.path.getmtime(path) == self.mtime


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
            raise SyncMetaTooNewError
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
        self.txt = FileMeta.new(path, Usdb.BASE_URL + f"?link=gettxt&id={self.song_id}")

    def set_audio_meta(self, path: Path, resource: str) -> None:
        self.audio = FileMeta.new(path, resource)

    def set_video_meta(self, path: Path, resource: str) -> None:
        self.video = FileMeta.new(path, resource)

    def set_cover_meta(self, path: Path, resource: str) -> None:
        self.cover = FileMeta.new(path, resource)

    def set_background_meta(self, path: Path, resource: str) -> None:
        self.background = FileMeta.new(path, resource)

    def synced_audio(self, folder: Path) -> FileMeta | None:
        if self.audio and self.audio.is_in_sync(folder):
            return self.audio
        return None

    def synced_video(self, folder: Path) -> FileMeta | None:
        if self.video and self.video.is_in_sync(folder):
            return self.video
        return None

    def synced_cover(self, folder: Path) -> FileMeta | None:
        if self.cover and self.cover.is_in_sync(folder):
            return self.cover
        return None

    def synced_background(self, folder: Path) -> FileMeta | None:
        if self.background and self.background.is_in_sync(folder):
            return self.background
        return None

    def file_metas(self) -> Iterator[FileMeta]:
        for meta in (self.txt, self.audio, self.video, self.cover, self.background):
            if meta:
                yield meta


class SyncMetaEncoder(json.JSONEncoder):
    """Custom JSON encoder"""

    def default(self, o: Any) -> Any:
        if isinstance(o, (SyncMeta, FileMeta)):
            return attrs.asdict(o, recurse=False)
        if isinstance(o, MetaTags):
            return str(o)
        return super().default(o)
