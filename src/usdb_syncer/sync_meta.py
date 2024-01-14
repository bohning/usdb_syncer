"""Meta data about the synchronization state of a USDB song."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator

import attrs

from usdb_syncer import SongId, SyncMetaId, db
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
class ResourceFile:
    """Meta data about a local file."""

    fname: str
    mtime: float
    resource: str

    @classmethod
    def new(cls, path: Path, resource: str) -> ResourceFile:
        return cls(path.name, os.path.getmtime(path), resource)

    @classmethod
    def from_nested_dict(cls, dct: Any) -> ResourceFile | None:
        if dct:
            return cls(**dct)
        return None

    @classmethod
    def from_db_row(cls, row: tuple[str, float, str]) -> ResourceFile:
        return cls(fname=row[0], mtime=row[1], resource=row[2])

    def is_in_sync(self, folder: Path) -> bool:
        """True if this file exists in the given folder and is in sync."""
        path = folder.joinpath(self.fname)
        return path.exists() and os.path.getmtime(path) == self.mtime

    def bump_mtime(self, folder: Path) -> None:
        self.mtime = os.path.getmtime(folder.joinpath(self.fname))

    def db_params(
        self, sync_meta_id: SyncMetaId, kind: db.ResourceFileKind
    ) -> db.ResourceFileParams:
        return db.ResourceFileParams(
            sync_meta_id=sync_meta_id,
            kind=kind,
            fname=self.fname,
            mtime=self.mtime,
            resource=self.resource,
        )


@attrs.define
class SyncMeta:
    """Meta data about the synchronization state of a USDB song."""

    sync_meta_id: SyncMetaId
    song_id: SongId
    path: Path
    mtime: float
    meta_tags: MetaTags
    pinned: bool = False
    txt: ResourceFile | None = None
    audio: ResourceFile | None = None
    video: ResourceFile | None = None
    cover: ResourceFile | None = None
    background: ResourceFile | None = None

    @classmethod
    def new(cls, song_id: SongId, folder: Path, meta_tags: MetaTags) -> SyncMeta:
        sync_meta_id = SyncMetaId.new()
        return cls(
            sync_meta_id=sync_meta_id,
            song_id=song_id,
            path=folder.joinpath(f"{sync_meta_id.encode()}.usdb"),
            mtime=0,
            meta_tags=meta_tags,
        )

    @classmethod
    def try_from_file(cls, path: Path) -> SyncMeta | None:
        if (sync_meta_id := SyncMetaId.decode(path.stem)) is None:
            return None
        with path.open(encoding="utf8") as file:
            dct = json.load(file)
        if not isinstance(dct, dict):
            return None
        if int(dct["version"]) > SYNC_META_VERSION:
            raise SyncMetaTooNewError
        try:
            return cls(
                sync_meta_id=sync_meta_id,
                song_id=SongId(dct["song_id"]),
                path=path,
                mtime=os.path.getmtime(path),
                meta_tags=MetaTags.parse(dct["meta_tags"], _logger),
                pinned=dct.get("pinned", False),
                txt=ResourceFile.from_nested_dict(dct["txt"]),
                audio=ResourceFile.from_nested_dict(dct["audio"]),
                video=ResourceFile.from_nested_dict(dct["video"]),
                cover=ResourceFile.from_nested_dict(dct["cover"]),
                background=ResourceFile.from_nested_dict(dct["background"]),
            )
        except (json.decoder.JSONDecodeError, TypeError, KeyError, ValueError):
            return None

    @classmethod
    def from_db_row(cls, song_id: SongId, row: tuple) -> SyncMeta | None:
        assert len(row) == 20
        if row[0] is None:
            return None
        meta = cls(
            sync_meta_id=SyncMetaId(row[0]),
            song_id=song_id,
            path=row[1],
            mtime=row[2],
            meta_tags=MetaTags.parse(row[3], _logger),
            pinned=row[4],
        )
        meta.txt = ResourceFile.from_db_row(row[5:8])
        meta.audio = ResourceFile.from_db_row(row[8:11])
        meta.video = ResourceFile.from_db_row(row[11:14])
        meta.cover = ResourceFile.from_db_row(row[14:17])
        meta.background = ResourceFile.from_db_row(row[17:])
        return meta

    def upsert(self, commit: bool = True) -> None:
        db.upsert_sync_meta(self.db_params())
        files = self.all_resource_files()
        db.upsert_resource_files(
            file.db_params(self.sync_meta_id, kind) for file, kind in files if file
        )
        db.delete_resource_files(
            (self.sync_meta_id, kind) for file, kind in files if not file
        )
        if commit:
            db.commit()

    @classmethod
    def upsert_many(cls, metas: list[SyncMeta], commit: bool = True) -> None:
        db.upsert_sync_metas(meta.db_params() for meta in metas)
        db.upsert_resource_files(
            file.db_params(meta.sync_meta_id, kind)
            for meta in metas
            for file, kind in meta.all_resource_files()
            if file
        )
        db.delete_resource_files(
            (meta.sync_meta_id, kind)
            for meta in metas
            for file, kind in meta.all_resource_files()
            if not file
        )
        if commit:
            db.commit()

    def delete(self, commit: bool = True) -> None:
        db.delete_sync_meta(self.sync_meta_id)
        if commit:
            db.commit()

    def all_resource_files(
        self,
    ) -> tuple[tuple[ResourceFile | None, db.ResourceFileKind], ...]:
        return (
            (self.txt, db.ResourceFileKind.TXT),
            (self.audio, db.ResourceFileKind.AUDIO),
            (self.video, db.ResourceFileKind.VIDEO),
            (self.cover, db.ResourceFileKind.COVER),
            (self.background, db.ResourceFileKind.BACKGROUND),
        )

    def db_params(self) -> db.SyncMetaParams:
        return db.SyncMetaParams(
            sync_meta_id=self.sync_meta_id,
            song_id=self.song_id,
            path=self.path.as_posix(),
            mtime=self.mtime,
            meta_tags=str(self.meta_tags),
            pinned=self.pinned,
        )

    def synchronize_to_file(self) -> None:
        """Rewrite the file on disk and update the mtime."""
        with self.path.open("w", encoding="utf8") as file:
            json.dump(self, file, cls=SyncMetaEncoder)
        self.mtime = os.path.getmtime(self.path)

    def set_txt_meta(self, path: Path) -> None:
        self.txt = ResourceFile.new(
            path, f"{Usdb.BASE_URL}?link=gettxt&id={self.song_id}"
        )

    def set_audio_meta(self, path: Path, resource: str) -> None:
        self.audio = ResourceFile.new(path, resource)

    def set_video_meta(self, path: Path, resource: str) -> None:
        self.video = ResourceFile.new(path, resource)

    def set_cover_meta(self, path: Path, resource: str) -> None:
        self.cover = ResourceFile.new(path, resource)

    def set_background_meta(self, path: Path, resource: str) -> None:
        self.background = ResourceFile.new(path, resource)

    def synced_audio(self, folder: Path) -> ResourceFile | None:
        if self.audio and self.audio.is_in_sync(folder):
            return self.audio
        return None

    def synced_video(self, folder: Path) -> ResourceFile | None:
        if self.video and self.video.is_in_sync(folder):
            return self.video
        return None

    def synced_cover(self, folder: Path) -> ResourceFile | None:
        if self.cover and self.cover.is_in_sync(folder):
            return self.cover
        return None

    def synced_background(self, folder: Path) -> ResourceFile | None:
        if self.background and self.background.is_in_sync(folder):
            return self.background
        return None

    def resource_files(self) -> Iterator[ResourceFile]:
        for meta in (self.txt, self.audio, self.video, self.cover, self.background):
            if meta:
                yield meta


class SyncMetaEncoder(json.JSONEncoder):
    """Custom JSON encoder"""

    def default(self, o: Any) -> Any:
        if isinstance(o, ResourceFile):
            return attrs.asdict(o)
        if isinstance(o, MetaTags):
            return str(o)
        if isinstance(o, SyncMeta):
            fields = attrs.fields(SyncMeta)
            filt = attrs.filters.exclude(fields.sync_meta_id, fields.path, fields.mtime)
            dct = attrs.asdict(o, recurse=False, filter=filt)
            dct["version"] = SYNC_META_VERSION
            return dct
        return super().default(o)
