"""Meta data about the synchronization state of a USDB song."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import attrs

from usdb_syncer import SongId, SyncMetaId, db, settings, utils
from usdb_syncer.custom_data import CustomData
from usdb_syncer.logger import logger
from usdb_syncer.meta_tags import MetaTags

SYNC_META_VERSION = 1
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
    mtime: int
    meta_tags: MetaTags
    pinned: bool = False
    txt: ResourceFile | None = None
    audio: ResourceFile | None = None
    video: ResourceFile | None = None
    cover: ResourceFile | None = None
    background: ResourceFile | None = None
    custom_data: CustomData = attrs.field(factory=CustomData)

    @classmethod
    def new(cls, song_id: SongId, folder: Path, meta_tags: MetaTags) -> SyncMeta:
        sync_meta_id = SyncMetaId.new()
        return cls(
            sync_meta_id=sync_meta_id,
            song_id=song_id,
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
                path=path,
                mtime=utils.get_mtime(path),
                meta_tags=MetaTags.parse(dct["meta_tags"], logger),
                pinned=bool(dct.get("pinned", False)),
                txt=ResourceFile.from_nested_dict(dct["txt"]),
                audio=ResourceFile.from_nested_dict(dct["audio"]),
                video=ResourceFile.from_nested_dict(dct["video"]),
                cover=ResourceFile.from_nested_dict(dct["cover"]),
                background=ResourceFile.from_nested_dict(dct["background"]),
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
        assert len(row) == 21
        meta = cls(
            sync_meta_id=SyncMetaId(row[0]),
            song_id=SongId(row[1]),
            path=Path(row[2]),
            mtime=row[3],
            meta_tags=MetaTags.parse(row[4], logger),
            pinned=bool(row[5]),
        )
        meta.txt = ResourceFile.from_db_row(row[6:9])
        meta.audio = ResourceFile.from_db_row(row[9:12])
        meta.video = ResourceFile.from_db_row(row[12:15])
        meta.cover = ResourceFile.from_db_row(row[15:18])
        meta.background = ResourceFile.from_db_row(row[18:])
        meta.custom_data = CustomData(db.get_custom_data(meta.sync_meta_id))
        return meta

    @classmethod
    def get_in_folder(cls, folder: Path) -> Iterator[SyncMeta]:
        return (SyncMeta.from_db_row(r) for r in db.get_in_folder(folder))

    @classmethod
    def reset_active(cls, folder: Path) -> None:
        db.reset_active_sync_metas(folder)

    def upsert(self) -> None:
        db.upsert_sync_meta(self.db_params())
        db.update_active_sync_metas(settings.get_song_dir(), self.song_id)
        files = self.all_resource_files()
        db.upsert_resource_files(
            file.db_params(self.sync_meta_id, kind) for file, kind in files if file
        )
        db.delete_resource_files(
            (self.sync_meta_id, kind) for file, kind in files if not file
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
        self.mtime = utils.get_mtime(self.path)

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
        if isinstance(o, CustomData):
            return o.inner()
        return super().default(o)
