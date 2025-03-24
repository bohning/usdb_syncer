"""Contains a runnable song loader."""

from __future__ import annotations

import shutil
import tempfile
import time
import traceback
from itertools import islice
from pathlib import Path
from typing import Iterable, assert_never

import send2trash
import shiboken6
from PySide6 import QtCore

from usdb_syncer import (
    SongId,
    SyncMetaId,
    db,
    download_options,
    errors,
    events,
    hooks,
    resource_dl,
    settings,
    utils,
)
from usdb_syncer.context import Context
from usdb_syncer.custom_data import CustomData
from usdb_syncer.discord import notify_discord
from usdb_syncer.logger import logger, song_logger
from usdb_syncer.postprocessing import write_audio_tags, write_video_tags
from usdb_syncer.resource_dl import ResourceDLError
from usdb_syncer.settings import FormatVersion, get_discord_allowed
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.usdb_song import DownloadStatus, UsdbSong
from usdb_syncer.utils import video_url_from_resource


class DownloadManager:
    """Manager for concurrent song downloads."""

    _jobs: dict[SongId, _SongLoader] = {}
    _pause = False
    _pool: QtCore.QThreadPool | None = None

    @classmethod
    def download(cls, songs: Iterable[UsdbSong]) -> None:
        options = download_options.download_options()
        for song in songs:
            if song.song_id in cls._jobs:
                cls._jobs[song.song_id].logger.warning("Already downloading!")
                continue
            cls._jobs[song.song_id] = job = _SongLoader(song, options)
            job.pause = cls._pause
            cls._threadpool().start(job)

    @classmethod
    def abort(cls, songs: Iterable[SongId]) -> None:
        for song in songs:
            if (job := cls._jobs.get(song)) and shiboken6.isValid(job):
                if cls._threadpool().tryTake(job):
                    job.logger.info("Download aborted by user request.")
                    job.song.status = DownloadStatus.NONE
                    with db.transaction():
                        job.song.upsert()
                    events.SongChanged(job.song_id).post()
                    events.DownloadFinished(job.song_id).post()
                else:
                    job.abort = True

    @classmethod
    def set_pause(cls, pause: bool) -> None:
        cls._pause = pause
        for job in cls._jobs.values():
            job.pause = pause

    @classmethod
    def quit(cls) -> None:
        if cls._pool:
            logger.debug(f"Quitting {len(cls._jobs)} downloads.")
            for job in cls._jobs.values():
                job.abort = True
            cls._pool.waitForDone()

    @classmethod
    def _threadpool(cls) -> QtCore.QThreadPool:
        if cls._pool is None:
            cls._pool = QtCore.QThreadPool()
            if threads := settings.get_throttling_threads():
                cls._pool.setMaxThreadCount(threads)
            events.DownloadFinished.subscribe(cls._remove_job)
        return cls._pool

    @classmethod
    def _remove_job(cls, event: events.DownloadFinished) -> None:
        if event.song_id in cls._jobs:
            del cls._jobs[event.song_id]


class _SongLoader(QtCore.QRunnable):
    """Runnable to create a complete song folder."""

    abort = False
    pause = False

    def __init__(self, song: UsdbSong, options: download_options.Options) -> None:
        super().__init__()
        self.song = song
        self.song_id = song.song_id
        self.options = options
        self.logger = song_logger(self.song_id)

    def run(self) -> None:
        with db.managed_connection(utils.AppPaths.db):
            try:
                self.song = self._run_inner()
            except errors.AbortError:
                self.logger.info("Download aborted by user request.")
                self.song.status = DownloadStatus.NONE
            except errors.UsdbLoginError:
                self.logger.error("Aborted; download requires login.")
                self.song.status = DownloadStatus.FAILED
            except errors.UsdbNotFoundError:
                self.logger.error("Song has been deleted from USDB.")
                with db.transaction():
                    self.song.delete()
                if meta := self.song.sync_meta:
                    path = meta.path.parent
                    self.logger.info(f"Trashing local song {path}")
                    send2trash.send2trash(path)
                events.SongDeleted(self.song_id).post()
                events.DownloadFinished(self.song_id).post()
                return
            except Exception:  # pylint: disable=broad-except
                self.logger.debug(traceback.format_exc())
                self.logger.error(
                    "Failed to finish download due to an unexpected error. "
                    "See debug log for more information."
                )
                self.song.status = DownloadStatus.FAILED
            else:
                self.song.status = DownloadStatus.NONE
                self.logger.info("All done!")
            with db.transaction():
                self.song.upsert()
        events.SongChanged(self.song_id).post()
        events.DownloadFinished(self.song_id).post()

    def _run_inner(self) -> UsdbSong:
        self._check_flags()
        self.song.status = DownloadStatus.DOWNLOADING
        with db.transaction():
            self.song.upsert()
        events.SongChanged(self.song_id).post()
        with tempfile.TemporaryDirectory() as tempdir:
            ctx = Context.new(self.song, self.options, Path(tempdir), self.logger)
            for job in (
                _maybe_download_audio,
                _maybe_download_video,
                _maybe_download_cover,
                _maybe_download_background,
                _maybe_write_audio_tags,
                _maybe_write_video_tags,
            ):
                self._check_flags()
                job(ctx)

            # last chance to abort before irreversible changes
            self._check_flags()
            _cleanup_existing_resources(ctx)
            # only here so filenames in header are up-to-date
            _maybe_write_txt(ctx)
            ctx.locations.move_to_target_folder()
            _persist_tempfiles(ctx)
        _write_sync_meta(ctx)
        hooks.SongLoaderDidFinish.call(ctx.song)
        return ctx.song

    def _check_flags(self) -> None:
        if self.abort:
            raise errors.AbortError
        if self.pause:
            while self.pause:
                time.sleep(0.5)
                if self.abort:
                    raise errors.AbortError


def _maybe_download_audio(ctx: Context) -> None:
    if not (options := ctx.options.audio_options):
        return
    for resource in islice(ctx.all_audio_resources(), 10):
        if ctx.out.audio.resource == resource:
            ctx.logger.info("Audio resource is unchanged.")
            return
        dl_result = resource_dl.download_audio(
            resource,
            options,
            ctx.options.browser,
            ctx.locations.temp_path(),
            ctx.logger,
        )
        if ext := dl_result.extension:
            ctx.out.audio.resource = resource
            ctx.out.audio.new_fname = ctx.locations.filename(ext=ext)
            ctx.logger.info("Success! Downloaded audio.")
            return
        if dl_result.error in {
            resource_dl.ResourceDLError.RESOURCE_INVALID,
            resource_dl.ResourceDLError.RESOURCE_UNAVAILABLE,
        }:
            if get_discord_allowed() and (url := video_url_from_resource(resource)):
                notify_discord(
                    ctx.song.song_id, url, "Audio", dl_result.error.value, logger
                )
    keep = " Keeping last resource." if ctx.out.audio.resource else ""
    song_len = ctx.txt.minimum_song_length()
    ctx.logger.error(f"Failed to download audio (song duration > {song_len})!{keep}")


def _maybe_download_video(ctx: Context) -> None:
    if not (options := ctx.options.video_options) or ctx.txt.meta_tags.is_audio_only():
        return
    for resource in islice(ctx.all_video_resources(), 10):
        if ctx.out.video.resource == resource:
            ctx.logger.info("Video resource is unchanged.")
            return
        dl_result = resource_dl.download_video(
            resource,
            options,
            ctx.options.browser,
            ctx.locations.temp_path(),
            ctx.logger,
        )
        if ext := dl_result.extension:
            ctx.out.video.resource = resource
            ctx.out.video.new_fname = ctx.locations.filename(ext=ext)
            ctx.logger.info("Success! Downloaded video.")
            return
        if dl_result.error in {
            resource_dl.ResourceDLError.RESOURCE_INVALID,
            resource_dl.ResourceDLError.RESOURCE_UNAVAILABLE,
        }:
            if get_discord_allowed() and (url := video_url_from_resource(resource)):
                notify_discord(
                    ctx.song.song_id, url, "Video", dl_result.error.value, logger
                )
    keep = " Keeping last resource." if ctx.out.video.resource else ""
    ctx.logger.error(f"Failed to download video!{keep}")


def _maybe_download_cover(ctx: Context) -> None:
    if not ctx.options.cover:
        return
    if ctx.txt.meta_tags.cover == ctx.details.cover_url == None:
        ctx.logger.warning("No cover resource found.")
        return
    if cover := ctx.txt.meta_tags.cover:
        url = cover.source_url(ctx.logger)
        if _download_cover_url(ctx, url):
            return
        if get_discord_allowed():
            notify_discord(
                ctx.song.song_id,
                url,
                "Cover",
                ResourceDLError.RESOURCE_UNAVAILABLE.value,
                ctx.logger,
            )
    if ctx.details.cover_url:
        ctx.logger.warning("Falling back to small USDB cover.")
        if _download_cover_url(ctx, ctx.details.cover_url, process=False):
            return
    keep = " Keeping last resource." if ctx.out.cover.resource else ""
    ctx.logger.error(f"Failed to download cover!{keep}")


def _download_cover_url(ctx: Context, url: str, process: bool = True) -> bool:
    """True if download was successful (or is unnecessary)."""
    assert ctx.options.cover
    if ctx.out.cover.resource == url:
        ctx.logger.info("Cover resource is unchanged.")
        return True
    if path := resource_dl.download_and_process_image(
        url=url,
        target_stem=ctx.locations.temp_path(),
        meta_tags=ctx.txt.meta_tags.cover,
        details=ctx.details,
        kind=resource_dl.ImageKind.COVER,
        max_width=ctx.options.cover.max_size,
        process=process,
    ):
        ctx.out.cover.resource = url
        ctx.out.cover.new_fname = path.name
        ctx.logger.info("Success! Downloaded cover.")
        return True
    return False


def _maybe_download_background(ctx: Context) -> None:
    if not (options := ctx.options.background_options):
        return
    if not options.download_background(bool(ctx.out.video.resource)):
        return
    if not (url := ctx.background_url()):
        ctx.logger.warning("No background resource found.")
        return
    if ctx.out.background.resource == url:
        ctx.logger.info("Background resource is unchanged.")
        return
    if path := resource_dl.download_and_process_image(
        url=url,
        target_stem=ctx.locations.temp_path(),
        meta_tags=ctx.txt.meta_tags.background,
        details=ctx.details,
        kind=resource_dl.ImageKind.BACKGROUND,
        max_width=None,
    ):
        ctx.out.background.resource = url
        ctx.out.background.new_fname = path.name
        ctx.logger.info("Success! Downloaded background.")
    else:
        if get_discord_allowed():
            notify_discord(
                ctx.song.song_id,
                url,
                "Background",
                ResourceDLError.RESOURCE_UNAVAILABLE.value,
                ctx.logger,
            )
        keep = " Keeping last resource." if ctx.out.cover.resource else ""
        ctx.logger.error(f"Failed to download background!{keep}")


def _maybe_write_txt(ctx: Context) -> None:
    if not (options := ctx.options.txt_options):
        return
    _write_headers(ctx)
    path = ctx.locations.temp_path(ext="txt")
    ctx.out.txt.new_fname = path.name
    ctx.txt.write_to_file(path, options.encoding.value, options.newline.value)
    ctx.out.txt.resource = ctx.song.song_id.usdb_url()
    ctx.logger.info("Success! Created song txt.")


def _write_headers(ctx: Context) -> None:
    version = (
        ctx.options.txt_options.format_version
        if ctx.options and ctx.options.txt_options
        else FormatVersion.V1_0_0
    )

    if path := ctx.out.audio.path(ctx.locations, temp=True):
        _set_audio_headers(ctx, version, path)

    if path := ctx.out.video.path(ctx.locations, temp=True):
        _set_video_headers(ctx, version, path)

    if path := ctx.out.cover.path(ctx.locations, temp=True):
        _set_cover_headers(ctx, version, path)

    if path := ctx.out.background.path(ctx.locations, temp=True):
        _set_background_headers(ctx, version, path)


def _set_audio_headers(ctx: Context, version: FormatVersion, path: Path) -> None:
    match version:
        case FormatVersion.V1_0_0:
            ctx.txt.headers.mp3 = path.name
        case FormatVersion.V1_1_0:
            # write both #MP3 and #AUDIO to maximize compatibility
            ctx.txt.headers.mp3 = path.name
            ctx.txt.headers.audio = path.name
        case FormatVersion.V1_2_0:
            ctx.txt.headers.audio = path.name
            if resource := ctx.txt.meta_tags.audio or ctx.txt.meta_tags.video:
                ctx.txt.headers.audiourl = video_url_from_resource(resource)
        case _ as unreachable:
            assert_never(unreachable)


def _set_video_headers(ctx: Context, version: FormatVersion, path: Path) -> None:
    ctx.txt.headers.video = path.name
    if version == FormatVersion.V1_2_0 and (resource := ctx.txt.meta_tags.video):
        ctx.txt.headers.videourl = video_url_from_resource(resource)


def _set_cover_headers(ctx: Context, version: FormatVersion, path: Path) -> None:
    ctx.txt.headers.cover = path.name
    if (
        version == FormatVersion.V1_2_0
        and ctx.txt.meta_tags.cover
        and (url := ctx.txt.meta_tags.cover.source_url(ctx.logger))
    ):
        ctx.txt.headers.coverurl = url


def _set_background_headers(ctx: Context, version: FormatVersion, path: Path) -> None:
    ctx.txt.headers.background = path.name
    if (
        version == FormatVersion.V1_2_0
        and ctx.txt.meta_tags.background
        and (url := ctx.txt.meta_tags.background.source_url(ctx.logger))
    ):
        ctx.txt.headers.backgroundurl = url


def _maybe_write_audio_tags(ctx: Context) -> None:
    if not (options := ctx.options.audio_options):
        return
    if not (path_resource := ctx.out.audio.path_and_resource(ctx.locations, temp=True)):
        return
    write_audio_tags(ctx, options, path_resource)


def _maybe_write_video_tags(ctx: Context) -> None:
    if not (options := ctx.options.video_options):
        return
    if not (path_resource := ctx.out.video.path_and_resource(ctx.locations, temp=True)):
        return
    write_video_tags(ctx, options, path_resource)


def _cleanup_existing_resources(ctx: Context) -> None:
    """Delete resources that are either out of sync or will be replaced with a new one,
    and ensure kept ones are correctly named.
    """
    if not ctx.song.sync_meta:
        return
    for (old, _), out in zip(ctx.song.sync_meta.all_resource_files(), ctx.out):
        if not (old and (old_path := ctx.locations.current_path(file=old.fname))):
            continue
        if not out.old_fname:
            # out of sync
            if old_path.exists():
                send2trash.send2trash(old_path)
                ctx.logger.debug(f"Trashed untracked file: '{old_path}'.")
        elif out.new_fname:
            send2trash.send2trash(old_path)
            ctx.logger.debug(f"Trashed existing file: '{old_path}'.")
        else:
            target = ctx.locations.filename(ext=utils.resource_file_ending(old.fname))
            if out.old_fname != target:
                # no new file; keep existing one, but ensure correct name
                path = old_path.with_name(target)
                old_path.rename(path)
                out.old_fname = target

    return


def _persist_tempfiles(ctx: Context) -> None:
    for temp_file in ctx.out:
        if temp_file.new_fname and (
            temp_path := temp_file.path(ctx.locations, temp=True)
        ):
            target = ctx.locations.target_path(temp_path.name)
            if target.exists():
                send2trash.send2trash(target)
                ctx.logger.debug(f"Trashed existing file: '{target}'.")
            shutil.move(temp_path, target)


def _write_sync_meta(ctx: Context) -> None:
    old = ctx.song.sync_meta
    sync_meta_id = old.sync_meta_id if old else SyncMetaId.new()
    ctx.song.sync_meta = SyncMeta(
        sync_meta_id=sync_meta_id,
        song_id=ctx.song.song_id,
        path=ctx.locations.target_path(file=sync_meta_id.to_filename()),
        mtime=0,
        meta_tags=ctx.txt.meta_tags,
        pinned=old.pinned if old else False,
        custom_data=CustomData(old.custom_data.inner() if old else None),
    )
    ctx.song.sync_meta.txt = ctx.out.txt.to_resource_file(ctx.locations, temp=False)
    ctx.song.sync_meta.audio = ctx.out.audio.to_resource_file(ctx.locations, temp=False)
    ctx.song.sync_meta.video = ctx.out.video.to_resource_file(ctx.locations, temp=False)
    ctx.song.sync_meta.cover = ctx.out.cover.to_resource_file(ctx.locations, temp=False)
    ctx.song.sync_meta.background = ctx.out.background.to_resource_file(
        ctx.locations, temp=False
    )
    ctx.song.sync_meta.synchronize_to_file()
