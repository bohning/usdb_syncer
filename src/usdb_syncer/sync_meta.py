"""Meta data about the synchronization state of a USDB song."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import attrs

from usdb_syncer import SongId, SyncMetaId, db, settings, utils
from usdb_syncer.custom_data import CustomData
from usdb_syncer.db import JobStatus
from usdb_syncer.logger import logger
from usdb_syncer.meta_tags import MetaTags

SYNC_META_VERSION = 1
SYNC_META_INDENT = 4
# mtimes may deviate up to 2 seconds on different file systems
# See https://en.wikipedia.org/wiki/File_Allocation_Table
MTIME_TOLERANCE_SECS = 2


class SyncMetaTooNewError(Exception):
    """Raised when trying to decode meta info from an incompatible future release."""

    def __str__(self) -> str:
        return "cannot read sync meta written by a future release"


@attrs.define
class ResourceFile:
    """Meta data about a local file."""

    fname: str
    mtime: int
    resource: str

    @classmethod
    def new(cls, path: Path, resource: str) -> ResourceFile:
        return cls(path.name, utils.get_mtime(path), resource)

    @classmethod
    def from_nested_dict(cls, dct: Any) -> ResourceFile | None:
        if (
            isinstance(dct, dict)
            and isinstance(fname := dct.get("fname"), str)
            and isinstance(mtime := dct.get("mtime"), (int, float))
            and isinstance(resource := dct.get("resource"), str)
        ):
            return cls(fname=fname, mtime=int(mtime), resource=resource)
        return None

    @classmethod
    def from_db_row(
        cls, row: tuple[str | None, int | None, str | None]
    ) -> ResourceFile | None:
        if row[0] is None or row[1] is None or row[2] is None:
            return None
        return cls(fname=row[0], mtime=row[1], resource=row[2])

    def is_in_sync(self, folder: Path) -> bool:
        """True if this file exists in the given folder and is in sync."""
        path = folder.joinpath(self.fname)
        return (
            path.exists()
            and abs(utils.get_mtime(path) - self.mtime) / 1_000_000
            < MTIME_TOLERANCE_SECS
        )


@attrs.define
class Resource:
    """Info about the status and the file of a resource."""

    status: JobStatus
    file: ResourceFile | None = None

    @classmethod
    def from_nested_dict(cls, dct: Any) -> Resource | None:
        if not isinstance(dct, dict):
            return None

        status_value = dct.get("status", JobStatus.SUCCESS)
        try:
            status = JobStatus(status_value)
        except (ValueError, TypeError):
            return None

        file = None
        if "fname" in dct and dct.get("fname") is not None:
            file = ResourceFile.from_nested_dict(dct)

        return cls(status, file)

    @classmethod
    def from_db_row(
        cls, row: tuple[str | None, int | None, str | None, JobStatus | None]
    ) -> Resource | None:
        if (status := row[3]) is None:
            return None

        file = ResourceFile.from_db_row(row[:3])

        return cls(status, file)

    def db_params(
        self, sync_meta_id: SyncMetaId, kind: db.ResourceKind
    ) -> db.ResourceParams:
        return db.ResourceParams(
            sync_meta_id=sync_meta_id,
            kind=kind,
            fname=self.file.fname if self.file else None,
            mtime=self.file.mtime if self.file else None,
            resource=self.file.resource if self.file else None,
            status=self.status,
        )


@attrs.define
class SyncMeta:
    """Meta data about the synchronization state of a USDB song."""

    sync_meta_id: SyncMetaId
    song_id: SongId
    usdb_mtime: int
    path: Path
    mtime: int
    meta_tags: MetaTags
    pinned: bool = False
    txt: Resource | None = None
    audio: Resource | None = None
    video: Resource | None = None
    cover: Resource | None = None
    background: Resource | None = None
    custom_data: CustomData = attrs.field(factory=CustomData)

    @classmethod
    def new(
        cls, song_id: SongId, usdb_mtime: int, folder: Path, meta_tags: MetaTags
    ) -> SyncMeta:
        sync_meta_id = SyncMetaId.new()
        return cls(
            sync_meta_id=sync_meta_id,
            song_id=song_id,
            usdb_mtime=usdb_mtime,
            path=folder.joinpath(sync_meta_id.to_filename()),
            mtime=0,
            meta_tags=meta_tags,
        )

    @classmethod
    def try_from_file(cls, path: Path) -> SyncMeta | None:
        new_id = False
        if (sync_meta_id := SyncMetaId.from_path(path)) is None:
            # might be a legacy file with old-style id
            sync_meta_id = SyncMetaId.new()
            new_id = True
        with path.open(encoding="utf8") as file:
            try:
                dct = json.load(file)
            except (json.decoder.JSONDecodeError, UnicodeDecodeError):
                return None
        if not isinstance(dct, dict):
            return None
        if int(dct["version"]) > SYNC_META_VERSION:
            raise SyncMetaTooNewError
        try:
            meta = cls(
                sync_meta_id=sync_meta_id,
                song_id=SongId(dct["song_id"]),
                usdb_mtime=int(dct.get("usdb_mtime", 0)),
                path=path,
                mtime=utils.get_mtime(path),
                meta_tags=MetaTags.parse(dct["meta_tags"], logger),
                pinned=bool(dct.get("pinned", False)),
                txt=Resource.from_nested_dict(dct["txt"]),
                audio=Resource.from_nested_dict(dct["audio"]),
                video=Resource.from_nested_dict(dct["video"]),
                cover=Resource.from_nested_dict(dct["cover"]),
                background=Resource.from_nested_dict(dct["background"]),
                custom_data=CustomData(dct.get("custom_data")),
            )
        except (TypeError, KeyError, ValueError):
            return None
        if new_id:
            meta.path = path.with_name(sync_meta_id.to_filename())
            path.rename(meta.path)
            logger.info(f"Assigned new ID to meta file: '{path}' > '{meta.path}'.")
        return meta

    @classmethod
    def from_db_row(cls, row: tuple) -> SyncMeta:
        assert len(row) == 27
        meta = cls(
            sync_meta_id=SyncMetaId(row[0]),
            song_id=SongId(row[1]),
            usdb_mtime=row[2],
            path=Path(row[3]),
            mtime=row[4],
            meta_tags=MetaTags.parse(row[5], logger),
            pinned=bool(row[6]),
        )
        meta.txt = Resource.from_db_row(row[7:11])
        meta.audio = Resource.from_db_row(row[11:15])
        meta.video = Resource.from_db_row(row[15:19])
        meta.cover = Resource.from_db_row(row[19:23])
        meta.background = Resource.from_db_row(row[23:])
        meta.custom_data = CustomData(db.get_custom_data(meta.sync_meta_id))
        return meta

    @classmethod
    def get_in_folder(cls, folder: Path) -> Iterator[SyncMeta]:
        return (SyncMeta.from_db_row(r) for r in db.get_in_folder(folder))

    @classmethod
    def reset_active(cls, folder: Path) -> None:
        db.reset_active_sync_metas(folder)

    def resource_is_local(self, kind: db.ResourceKind) -> bool:
        resource = self.resource(kind)
        if not resource or not resource.file or not resource.file.fname:
            return False

        file_path = self.path.parent / resource.file.fname
        return file_path.exists()

    def upsert(self) -> None:
        db.upsert_sync_meta(self.db_params())
        db.update_active_sync_metas(settings.get_song_dir(), self.song_id)
        resources = self.all_resources()
        db.upsert_resources(
            resource.db_params(self.sync_meta_id, kind)
            for resource, kind in resources
            if resource
        )
        db.delete_resources(
            (self.sync_meta_id, kind) for resource, kind in resources if not resource
        )
        db.delete_custom_meta_data((self.sync_meta_id,))
        db.upsert_custom_meta_data(
            db.CustomMetaDataParams(self.sync_meta_id, k, v)
            for k, v in self.custom_data.items()
        )

    @classmethod
    def upsert_many(cls, metas: list[SyncMeta]) -> None:
        db.upsert_sync_metas(meta.db_params() for meta in metas)
        db.reset_active_sync_metas(settings.get_song_dir())
        db.upsert_resources(
            file.db_params(meta.sync_meta_id, kind)
            for meta in metas
            for file, kind in meta.all_resources()
            if file
        )
        db.delete_resources(
            (meta.sync_meta_id, kind)
            for meta in metas
            for file, kind in meta.all_resources()
            if not file
        )
        db.delete_custom_meta_data(m.sync_meta_id for m in metas)
        db.upsert_custom_meta_data(
            db.CustomMetaDataParams(m.sync_meta_id, k, v)
            for m in metas
            for k, v in m.custom_data.items()
        )

    def delete(self) -> None:
        db.delete_sync_meta(self.sync_meta_id)

    @classmethod
    def delete_many(cls, ids: tuple[SyncMetaId, ...]) -> None:
        db.delete_sync_metas(ids)

    @classmethod
    def delete_many_in_folder(cls, folder: Path, ids: tuple[SyncMetaId, ...]) -> None:
        db.delete_sync_metas_in_folder(folder, ids)

    def resource(self, kind: db.ResourceKind) -> Resource | None:
        return next((r for r, k in self.all_resources() if k == kind), None)

    def all_resources(self) -> tuple[tuple[Resource | None, db.ResourceKind], ...]:
        return (
            (self.txt, db.ResourceKind.TXT),
            (self.audio, db.ResourceKind.AUDIO),
            (self.video, db.ResourceKind.VIDEO),
            (self.cover, db.ResourceKind.COVER),
            (self.background, db.ResourceKind.BACKGROUND),
        )

    def db_params(self) -> db.SyncMetaParams:
        return db.SyncMetaParams(
            sync_meta_id=self.sync_meta_id,
            song_id=self.song_id,
            usdb_mtime=self.usdb_mtime,
            path=self.path.as_posix(),
            mtime=self.mtime,
            meta_tags=str(self.meta_tags),
            pinned=self.pinned,
        )

    def synchronize_to_file(self) -> None:
        """Rewrite the file on disk and update the mtime."""
        with self.path.open("w", encoding="utf8") as file:
            json.dump(self, file, cls=SyncMetaEncoder, indent=SYNC_META_INDENT)
        self.mtime = utils.get_mtime(self.path)

    def txt_path(self) -> Path | None:
        if not self.txt or not self.txt.file or self.txt.file.fname is None:
            return None
        return self.path.parent / self.txt.file.fname

    def audio_path(self) -> Path | None:
        if not self.audio or not self.audio.file or self.audio.file.fname is None:
            return None
        return self.path.parent / self.audio.file.fname

    def video_path(self) -> Path | None:
        if not self.video or not self.video.file or self.video.file.fname is None:
            return None
        return self.path.parent / self.video.file.fname

    def cover_path(self) -> Path | None:
        if not self.cover or not self.cover.file or self.cover.file.fname is None:
            return None
        return self.path.parent / self.cover.file.fname


class SyncMetaEncoder(json.JSONEncoder):
    """Custom JSON encoder"""

    def default(self, o: Any) -> Any:
        if isinstance(o, ResourceFile):
            return attrs.asdict(o)
        if isinstance(o, Resource):
            if o.file is None:
                return {"status": o.status}
            else:
                dct = attrs.asdict(o.file)
                dct["status"] = o.status
                return dct
        if isinstance(o, MetaTags):
            return str(o)
        if isinstance(o, SyncMeta):
            fields = attrs.fields(SyncMeta)
            filt = attrs.filters.exclude(fields.sync_meta_id, fields.path, fields.mtime)
            dct = attrs.asdict(o, recurse=False, filter=filt)
            dct["version"] = SYNC_META_VERSION
            return dct
        if isinstance(o, CustomData):
            return o.inner()
        return super().default(o)
