"""Contains a runnable song loader."""

from __future__ import annotations

import copy
import filecmp
import shutil
import tempfile
import time
from collections.abc import Iterable, Iterator
from enum import Enum
from functools import partial
from itertools import islice
from pathlib import Path
from typing import ClassVar, assert_never

import attrs
import shiboken6
from PySide6 import QtCore

from usdb_syncer import (
    SongId,
    SyncMetaId,
    constants,
    db,
    download_options,
    errors,
    events,
    hooks,
    resource_dl,
    settings,
    usdb_scraper,
    utils,
)
from usdb_syncer.custom_data import CustomData
from usdb_syncer.db import JobStatus, ResourceKind
from usdb_syncer.discord import notify_discord
from usdb_syncer.download_options import AudioOptions, VideoOptions
from usdb_syncer.logger import Logger, logger, song_logger
from usdb_syncer.meta_tags import ImageMetaTags
from usdb_syncer.postprocessing import write_audio_tags, write_video_tags
from usdb_syncer.resource_dl import ImageKind, ResourceDLError
from usdb_syncer.settings import FormatVersion
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.sync_meta import Resource, ResourceFile, SyncMeta
from usdb_syncer.usdb_scraper import SongDetails
from usdb_syncer.usdb_song import DownloadStatus, UsdbSong
from usdb_syncer.utils import video_url_from_resource


class DownloadManager:
    """Manager for concurrent song downloads."""

    _jobs: ClassVar[dict[SongId, _SongLoader]] = {}
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
                    with db.transaction():
                        job.song.set_status(job.song.get_resetted_status())
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


@attrs.define(kw_only=True)
class _Locations:
    """Paths for downloading a song."""

    _current: Path | None
    # includes filename stem
    _target: Path
    _tempdir: Path

    @classmethod
    def new(
        cls, song: UsdbSong, options: download_options.Options, tempdir: Path
    ) -> _Locations:
        target = options.path_template.evaluate(song, options.song_dir)
        if (
            _current := song.sync_meta.path.parent if song.sync_meta else None
        ) and utils.path_matches_maybe_with_suffix(_current, target.parent):
            target = _current / target.name
        else:
            target = utils.next_unique_directory(target.parent) / target.name
        return cls(current=_current, target=target, tempdir=tempdir)  # pyright: ignore

    def current_path(self, file: str = "", ext: str = "") -> Path | None:
        """Path to file in the current download directory if it exists.
        The final path component is the generic name or the provided file, optionally
        with the provided extension joined with a '.' unless one is already present.
        """
        return self._path(self._current, file, ext) if self._current else None

    def temp_path(self, file: str = "", ext: str = "") -> Path:
        """Path to file in the temporary download directory.
        The final path component is the generic name or the provided file, optionally
        with the provided extension joined with a '.' unless one is already present.
        """
        return self._path(self._tempdir, file, ext)

    def target_path(self, file: str = "", ext: str = "") -> Path:
        """Path to file in the final download directory.
        The final path component is the generic name or the provided file, optionally
        with the provided extension joined with a '.' unless one is already present.
        """
        return self._path(self._target.parent, file, ext)

    def _path(self, parent: Path, file: str = "", ext: str = "") -> Path:
        name = file or self._target.name
        if ext:
            name = f"{name}{'' if '.' in ext else '.'}{ext}"
        return parent.joinpath(name)

    def filename(self, ext: str = "") -> str:
        if ext:
            return f"{self._target.name}{'' if '.' in ext else '.'}{ext}"
        return self._target.name

    def move_to_target_folder(self) -> None:
        """Rename the path of the song folder if it does not match the template, and
        ensure the target directory exists.
        """
        if self._current and self._current != self._target:
            self._target.parent.parent.mkdir(parents=True, exist_ok=True)
            self._current.rename(self._target.parent)
            self._current = self._target.parent
        else:
            self._target.parent.mkdir(parents=True, exist_ok=True)


@attrs.define
class _TempResourceFile:
    """Interim resource file in the temporary folder, or in the old folder if the
    resource is potentially kept.
    """

    old_fname: str | None = None
    new_fname: str | None = None
    resource: str | None = None

    def path_and_resource(
        self, locations: _Locations, temp: bool
    ) -> tuple[Path, str] | None:
        if (path := self.path(locations, temp=temp)) and self.resource:
            return (path, self.resource)
        return None

    def path(self, locations: _Locations, temp: bool) -> Path | None:
        if self.new_fname:
            if temp:
                return locations.temp_path(self.new_fname)
            return locations.target_path(self.new_fname)
        if self.old_fname:
            return locations.current_path(self.old_fname)
        return None

    def to_resource(
        self, locations: _Locations, temp: bool, status: JobStatus
    ) -> Resource:
        if path_resource := self.path_and_resource(locations, temp=temp):
            file = ResourceFile.new(*path_resource)
            return Resource.new(status, file)
        return Resource.status_only(status)


@attrs.define
class _TempResourceFiles:
    """Collection of all temporary resource files."""

    txt: _TempResourceFile = attrs.field(factory=_TempResourceFile)
    audio: _TempResourceFile = attrs.field(factory=_TempResourceFile)
    video: _TempResourceFile = attrs.field(factory=_TempResourceFile)
    cover: _TempResourceFile = attrs.field(factory=_TempResourceFile)
    background: _TempResourceFile = attrs.field(factory=_TempResourceFile)

    def __iter__(self) -> Iterator[_TempResourceFile]:
        return iter((self.txt, self.audio, self.video, self.cover, self.background))


@attrs.define
class _Context:
    """_Context for downloading media and creating a song folder."""

    # deep copy of the passed in song
    song: UsdbSong
    details: SongDetails
    options: download_options.Options
    txt: SongTxt
    locations: _Locations
    logger: Logger
    out: _TempResourceFiles = attrs.field(factory=_TempResourceFiles)
    results: dict[Job, JobStatus] = attrs.field(factory=dict)

    def __attrs_post_init__(self) -> None:
        # reuse old resource files unless we acquire new ones later on
        if self.song.sync_meta and (current := self.locations.current_path()):
            for old, out in (
                (self.song.sync_meta.txt, self.out.txt),
                (self.song.sync_meta.audio, self.out.audio),
                (self.song.sync_meta.video, self.out.video),
                (self.song.sync_meta.cover, self.out.cover),
                (self.song.sync_meta.background, self.out.background),
            ):
                if (
                    old
                    and (old_file := old.file)
                    and old_file.is_in_sync(current.parent)
                ):
                    out.resource = old_file.resource
                    out.old_fname = old_file.fname

    @classmethod
    def new(
        cls,
        song: UsdbSong,
        options: download_options.Options,
        tempdir: Path,
        log: Logger,
    ) -> _Context:
        song = copy.deepcopy(song)
        details, txt = _get_usdb_data(song.song_id, options.txt_options, log)
        _update_song_with_usdb_data(song, details, txt)
        paths = _Locations.new(song, options, tempdir)
        if not song.sync_meta:
            song.sync_meta = SyncMeta.new(
                song.song_id, song.usdb_mtime, paths.target_path().parent, txt.meta_tags
            )
        return cls(song, details, options, txt, paths, log)

    def primary_audio_resource(self) -> str | None:
        """Return the primary audio resource (from meta tags)."""
        return self.txt.meta_tags.audio or self.txt.meta_tags.video

    def fallback_audio_resources(self) -> Iterator[str]:
        """Return fallback audio resources (from video meta tag and comments)"""
        if self.txt.meta_tags.is_audio_only() and self.txt.meta_tags.video:
            yield self.txt.meta_tags.video
        yield from self.fallback_video_resources()

    def primary_video_resource(self) -> str | None:
        """Return the primary video resource (from meta tags)."""
        return self.txt.meta_tags.video

    def fallback_video_resources(self) -> Iterator[str]:
        """Return fallback video resources (from comments)"""
        yield from self.details.all_comment_videos()

    def primary_cover(self) -> ImageMetaTags | None:
        """Return the primary cover resource (from meta tags)."""
        return self.txt.meta_tags.cover

    def fallback_cover_resource(self) -> str | None:
        """Return the fallback USDB cover resource"""
        return self.details.cover_url

    def primary_background(self) -> ImageMetaTags | None:
        return self.txt.meta_tags.background


def _get_usdb_data(
    song_id: SongId, txt_options: download_options.TxtOptions | None, log: Logger
) -> tuple[SongDetails, SongTxt]:
    details = usdb_scraper.get_usdb_details(song_id)
    log.info(f"Found '{details.artist} - {details.title}' on USDB.")
    txt_str = usdb_scraper.get_notes(details.song_id, log)
    txt = SongTxt.parse(txt_str, log)
    txt.sanitize(txt_options)
    txt.headers.creator = txt.headers.creator or details.uploader or None
    return details, txt


def _update_song_with_usdb_data(
    song: UsdbSong, details: SongDetails, txt: SongTxt
) -> None:
    song.artist = details.artist
    song.title = details.title
    song.language = txt.headers.language or ""
    song.edition = txt.headers.edition or ""
    song.golden_notes = details.golden_notes
    song.rating = details.rating
    song.views = details.views
    if txt.headers.year and len(txt.headers.year) == 4 and txt.headers.year.isdigit():
        song.year = int(txt.headers.year)
    else:
        song.year = None
    song.genre = txt.headers.genre or ""
    song.creator = txt.headers.creator or ""


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
                status = self.song.get_resetted_status()
            except errors.UsdbLoginError:
                self.logger.error("Aborted; download requires login.")  # noqa: TRY400
                status = DownloadStatus.FAILED
            except errors.UsdbNotFoundError:
                self.logger.error("Song has been deleted from USDB.")  # noqa: TRY400
                with db.transaction():
                    self.song.delete()
                if meta := self.song.sync_meta:
                    path = meta.path.parent
                    self.logger.info(f"Trashing local song {path}")
                    utils.trash_or_delete_path(path)
                events.SongDeleted(self.song_id).post()
                events.DownloadFinished(self.song_id).post()
                return
            except Exception:
                self.logger.exception(
                    "Failed to finish download due to an unexpected error. "
                    "See debug log for more information."
                )
                status = DownloadStatus.FAILED
            else:
                status = DownloadStatus.SYNCHRONIZED
                self.logger.info("All done!")
            with db.transaction():
                self.song.upsert()
                self.song.set_status(status)
        events.SongChanged(self.song_id).post()
        events.DownloadFinished(self.song_id).post()

    def _run_inner(self) -> UsdbSong:
        self._check_flags()
        with db.transaction():
            self.song.set_status(DownloadStatus.DOWNLOADING)
        events.SongChanged(self.song_id).post()
        with tempfile.TemporaryDirectory() as tempdir:
            ctx = _Context.new(self.song, self.options, Path(tempdir), self.logger)
            for job in Job:
                self._check_flags()
                self.logger.debug(f"Running job: {job.name}")
                # Skip jobs if dependencies are unchanged
                if (deps := job.depends_on()) and not any(
                    ctx.results.get(dep) is JobStatus.SUCCESS for dep in deps
                ):
                    ctx.logger.debug(
                        f"Skipping {job.name}: all relevant files unchanged."
                    )
                    ctx.results[job] = JobStatus.SKIPPED_UNCHANGED
                    continue

                ctx.results[job] = job(ctx)
                ctx.logger.debug(f"Job {job.name} result: {ctx.results[job].name}")

            # last chance to abort before irreversible changes
            self._check_flags()
            _cleanup_existing_resources(ctx)
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


def _maybe_download_audio(ctx: _Context) -> JobStatus:
    if not (options := ctx.options.audio_options):
        ctx.logger.info("Audio download is disabled, skipping download.")
        return JobStatus.SKIPPED_DISABLED

    if primary_resource := ctx.primary_audio_resource():
        if out_resource := ctx.out.audio.resource:
            if primary_resource == out_resource:
                # TODO: Filename might need to change because of changes in artist/title
                ctx.logger.info("Audio resource is unchanged, skipping download.")
                return JobStatus.SKIPPED_UNCHANGED
            else:
                ctx.logger.info("Audio resource has changed, redownloading.")

        status = _try_download_audio_or_video(
            ctx, primary_resource, options, ResourceKind.AUDIO
        )
        if status is JobStatus.SUCCESS:
            ctx.logger.info("Success! Downloaded audio. ")
            return JobStatus.SUCCESS

    for fallback_resource in islice(ctx.fallback_audio_resources(), 10):
        status = _try_download_audio_or_video(
            ctx, fallback_resource, options, ResourceKind.AUDIO
        )
        if status is JobStatus.SUCCESS:
            ctx.logger.warning(
                f"Downloaded fallback audio '{fallback_resource}'. "
                "This may require adaptations in GAP and/or BPM."
            )
            return JobStatus.FALLBACK

    failure_msg = "Failed to download audio."
    if ctx.out.audio.resource:
        ctx.logger.error(f"{failure_msg} Keeping existing resource.")
        return JobStatus.FAILURE_EXISTING

    song_len = ctx.txt.minimum_song_length()
    ctx.logger.error(f"{failure_msg} (song duration > {song_len})!")
    return JobStatus.FAILURE


def _maybe_download_video(ctx: _Context) -> JobStatus:
    if not (options := ctx.options.video_options):
        ctx.logger.info("Video download is disabled, skipping download.")
        return JobStatus.SKIPPED_DISABLED

    if ctx.txt.meta_tags.is_audio_only():
        ctx.logger.info("Song is audio only, skipping download.")
        return JobStatus.SKIPPED_UNAVAILABLE

    if primary := ctx.primary_video_resource():
        if out_resource := ctx.out.video.resource:
            if primary == out_resource:
                ctx.logger.info("Video resource is unchanged, skipping download.")
                return JobStatus.SKIPPED_UNCHANGED
            else:
                ctx.logger.info("Video resource has changed, redownloading.")

        status = _try_download_audio_or_video(ctx, primary, options, ResourceKind.VIDEO)
        if status is JobStatus.SUCCESS:
            ctx.logger.info("Success! Downloaded video. ")
            return JobStatus.SUCCESS

    for fallback in islice(ctx.fallback_audio_resources(), 10):
        status = _try_download_audio_or_video(
            ctx, fallback, options, ResourceKind.VIDEO
        )
        if status is JobStatus.SUCCESS:
            ctx.logger.warning(
                f"Downloaded fallback video '{fallback}'. "
                "This may require adaptations in GAP and/or BPM."
            )
            return JobStatus.FALLBACK

    failure_msg = "Failed to download video."
    if ctx.out.video.resource:
        ctx.logger.error(f"{failure_msg} Keeping existing resource.")
        return JobStatus.FAILURE_EXISTING

    ctx.logger.error(failure_msg)
    return JobStatus.FAILURE


def _try_download_audio_or_video(
    ctx: _Context,
    resource: str,
    options: AudioOptions | VideoOptions,
    kind: ResourceKind,
) -> JobStatus:
    match kind:
        case ResourceKind.AUDIO:
            assert isinstance(options, AudioOptions)
            dl_result = resource_dl.download_audio(
                resource,
                options,
                ctx.options.browser,
                ctx.locations.temp_path(),
                ctx.logger,
            )
        case ResourceKind.VIDEO:
            assert isinstance(options, VideoOptions)
            dl_result = resource_dl.download_video(
                resource,
                options,
                ctx.options.browser,
                ctx.locations.temp_path(),
                ctx.logger,
            )
        case _:
            return JobStatus.FAILURE

    if ext := dl_result.extension:
        match kind:
            case ResourceKind.AUDIO:
                ctx.out.audio.resource = resource
                ctx.out.audio.new_fname = ctx.locations.filename(ext=ext)
            case ResourceKind.VIDEO:
                ctx.out.video.resource = resource
                ctx.out.video.new_fname = ctx.locations.filename(ext=ext)
        return JobStatus.SUCCESS

    if dl_result.error in {
        resource_dl.ResourceDLError.RESOURCE_INVALID,
        resource_dl.ResourceDLError.RESOURCE_UNSUPPORTED,
        resource_dl.ResourceDLError.RESOURCE_UNAVAILABLE,
        resource_dl.ResourceDLError.RESOURCE_PARSE_ERROR,
    }:
        if ctx.options.notify_discord and (url := video_url_from_resource(resource)):
            notify_discord(
                ctx.song.song_id,
                url,
                kind.capitalize(),
                dl_result.error.value,
                ctx.logger,
            )

    return JobStatus.FAILURE


def _maybe_download_cover(ctx: _Context) -> JobStatus:
    if not ctx.options.cover:
        return JobStatus.SKIPPED_DISABLED

    if primary_cover := ctx.primary_cover():
        if (url := primary_cover.source_url(ctx.logger)) == ctx.out.cover.resource:
            ctx.logger.info("Cover resource is unchanged, skipping download.")
            return JobStatus.SKIPPED_UNCHANGED
        else:
            ctx.logger.info("Cover resource has changed, redownloading.")

        status = _try_download_cover_or_background(
            ctx, url, ImageKind.COVER, process=True
        )
        if status is JobStatus.SUCCESS:
            ctx.logger.info("Success! Downloaded cover. ")
            return JobStatus.SUCCESS
        if status is JobStatus.FAILURE and ctx.options.notify_discord:
            notify_discord(
                ctx.song.song_id,
                url,
                ResourceKind.COVER.capitalize(),
                ResourceDLError.RESOURCE_UNAVAILABLE.value,
                ctx.logger,
            )

    if fallback := ctx.fallback_cover_resource():
        status = _try_download_cover_or_background(
            ctx, fallback, ImageKind.COVER, process=False
        )
        if status is JobStatus.SUCCESS:
            ctx.logger.warning("Downloaded fallback cover from USDB.")
            return JobStatus.FALLBACK

    failure_msg = "Failed to download cover."
    if ctx.out.cover.resource:
        ctx.logger.error(f"{failure_msg} Keeping existing resource.")
        return JobStatus.FAILURE_EXISTING

    ctx.logger.error(failure_msg)
    return JobStatus.FAILURE


def _maybe_download_background(ctx: _Context) -> JobStatus:
    if not (options := ctx.options.background_options):
        return JobStatus.SKIPPED_DISABLED

    if not options.download_background(bool(ctx.out.video.resource)):
        return JobStatus.SKIPPED_DISABLED

    if not (primary := ctx.primary_background()) or not (
        url := primary.source_url(ctx.logger)
    ):
        ctx.logger.warning("No background resource found.")
        return JobStatus.SKIPPED_UNAVAILABLE

    if url == ctx.out.background.resource:
        ctx.logger.info("Background resource is unchanged, skipping download.")
        return JobStatus.SKIPPED_UNCHANGED
    else:
        ctx.logger.info("Background resource has changed, redownloading.")

    status = _try_download_cover_or_background(
        ctx, url, ImageKind.BACKGROUND, process=False
    )
    if status is JobStatus.SUCCESS:
        ctx.logger.info("Success! Downloaded background. ")
        return JobStatus.SUCCESS
    if status is JobStatus.FAILURE and ctx.options.notify_discord:
        notify_discord(
            ctx.song.song_id,
            url,
            ResourceKind.COVER.capitalize(),
            ResourceDLError.RESOURCE_UNAVAILABLE.value,
            ctx.logger,
        )

    failure_msg = "Failed to download background."
    if ctx.out.background.resource:
        ctx.logger.error(f"{failure_msg} Keeping existing resource.")
        return JobStatus.FAILURE_EXISTING

    ctx.logger.error(failure_msg)
    return JobStatus.FAILURE


def _try_download_cover_or_background(
    ctx: _Context, url: str, kind: ImageKind, process: bool
) -> JobStatus:
    assert ctx.options.cover

    if path := resource_dl.download_and_process_image(
        url=url,
        target_stem=ctx.locations.temp_path(),
        meta_tags=ctx.txt.meta_tags.cover
        if kind == ImageKind.COVER
        else ctx.txt.meta_tags.background,
        details=ctx.details,
        kind=kind,
        max_width=ctx.options.cover.max_size,
        process=process,
    ):
        match kind:
            case ImageKind.COVER:
                ctx.out.cover.resource = url
                ctx.out.cover.new_fname = path.name
            case ImageKind.BACKGROUND:
                ctx.out.background.resource = url
                ctx.out.background.new_fname = path.name
            case _ as unreachable:
                assert_never(unreachable)
        return JobStatus.SUCCESS

    return JobStatus.FAILURE


def _maybe_write_txt(ctx: _Context) -> JobStatus:
    if not (options := ctx.options.txt_options):
        return JobStatus.SKIPPED_DISABLED
    _write_headers(ctx)
    path = ctx.locations.temp_path(ext="txt")
    ctx.txt.write_to_file(path, options.encoding.value, options.newline.value)
    if (
        ctx.out.txt.old_fname
        and (old_path := ctx.locations.current_path(ctx.out.txt.old_fname))
        and filecmp.cmp(path, old_path, shallow=False)
    ):
        ctx.logger.info("Song txt is unchanged.")
        return JobStatus.SKIPPED_UNCHANGED
    else:
        ctx.out.txt.new_fname = path.name
        ctx.out.txt.resource = ctx.song.song_id.usdb_gettxt_url()
        ctx.logger.info("Success! Created song txt.")
        return JobStatus.SUCCESS


def _write_headers(ctx: _Context) -> None:
    version = (
        ctx.options.txt_options.format_version
        if ctx.options and ctx.options.txt_options
        else FormatVersion.V1_0_0
    )

    if version >= FormatVersion.V1_1_0:
        ctx.txt.headers.providedby = constants.Usdb.BASE_URL

    if path := ctx.out.audio.path(ctx.locations, temp=True):
        _set_audio_headers(ctx, version, path)

    if path := ctx.out.video.path(ctx.locations, temp=True):
        _set_video_headers(ctx, version, path)

    if path := ctx.out.cover.path(ctx.locations, temp=True):
        _set_cover_headers(ctx, version, path)

    if path := ctx.out.background.path(ctx.locations, temp=True):
        _set_background_headers(ctx, version, path)


def _set_audio_headers(ctx: _Context, version: FormatVersion, path: Path) -> None:
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


def _set_video_headers(ctx: _Context, version: FormatVersion, path: Path) -> None:
    ctx.txt.headers.video = path.name
    if version >= FormatVersion.V1_2_0 and (resource := ctx.txt.meta_tags.video):
        ctx.txt.headers.videourl = video_url_from_resource(resource)


def _set_cover_headers(ctx: _Context, version: FormatVersion, path: Path) -> None:
    ctx.txt.headers.cover = path.name
    if (
        version >= FormatVersion.V1_2_0
        and ctx.txt.meta_tags.cover
        and (url := ctx.txt.meta_tags.cover.source_url(ctx.logger))
    ):
        ctx.txt.headers.coverurl = url


def _set_background_headers(ctx: _Context, version: FormatVersion, path: Path) -> None:
    ctx.txt.headers.background = path.name
    if (
        version >= FormatVersion.V1_2_0
        and ctx.txt.meta_tags.background
        and (url := ctx.txt.meta_tags.background.source_url(ctx.logger))
    ):
        ctx.txt.headers.backgroundurl = url


def _maybe_write_audio_tags(ctx: _Context) -> JobStatus:
    if not (options := ctx.options.audio_options):
        return JobStatus.SKIPPED_DISABLED
    if not (
        audio_path_resource := ctx.out.audio.path_and_resource(ctx.locations, temp=True)
    ):
        ctx.logger.info("No audio file to tag, skipping writing audio tags.")
        return JobStatus.SKIPPED_UNAVAILABLE
    cover_path_resource = ctx.out.cover.path_and_resource(ctx.locations, temp=True)
    background_path_resource = ctx.out.background.path_and_resource(
        ctx.locations, temp=True
    )
    write_audio_tags(
        txt=ctx.txt,
        options=options,
        audio=audio_path_resource,
        cover=cover_path_resource,
        background=background_path_resource,
        logger=ctx.logger,
    )

    ctx.logger.info("Success! Wrote audio tags.")
    return JobStatus.SUCCESS


def _maybe_write_video_tags(ctx: _Context) -> JobStatus:
    if not (options := ctx.options.video_options):
        return JobStatus.SKIPPED_DISABLED
    if not (
        video_path_resource := ctx.out.video.path_and_resource(ctx.locations, temp=True)
    ):
        ctx.logger.info("No video file to tag, skipping writing video tags.")
        return JobStatus.SKIPPED_UNAVAILABLE
    cover_path_resource = ctx.out.cover.path_and_resource(ctx.locations, temp=True)
    background_path_resource = ctx.out.background.path_and_resource(
        ctx.locations, temp=True
    )
    write_video_tags(
        txt=ctx.txt,
        options=options,
        video=video_path_resource,
        cover=cover_path_resource,
        background=background_path_resource,
        logger=ctx.logger,
    )
    ctx.logger.info("Success! Wrote video tags.")
    return JobStatus.SUCCESS


def _cleanup_existing_resources(ctx: _Context) -> None:
    """Delete resources that are either out of sync or will be replaced with a new one,
    and ensure kept ones are correctly named.
    """
    if not ctx.song.sync_meta:
        return
    for (old, _), out in zip(ctx.song.sync_meta.all_resources(), ctx.out, strict=False):
        if not (
            old
            and (old_file := old.file)
            and old_file.fname
            and (old_path := ctx.locations.current_path(file=old_file.fname))
        ):
            continue
        if not out.old_fname:
            # out of sync
            if old_path.exists():
                utils.trash_or_delete_path(old_path)
                ctx.logger.debug(f"Trashed untracked file: '{old_path}'.")
        elif out.new_fname:
            utils.trash_or_delete_path(old_path)
            ctx.logger.debug(f"Trashed existing file: '{old_path}'.")
        else:
            target = ctx.locations.filename(
                ext=utils.resource_file_ending(old_file.fname)
            )
            if out.old_fname != target:
                # no new file; keep existing one, but ensure correct name
                path = old_path.with_name(target)
                old_path.rename(path)
                out.old_fname = target


def _persist_tempfiles(ctx: _Context) -> None:
    for temp_file in ctx.out:
        if temp_file.new_fname and (
            temp_path := temp_file.path(ctx.locations, temp=True)
        ):
            target = ctx.locations.target_path(temp_path.name)
            if target.exists():
                utils.trash_or_delete_path(target)
                ctx.logger.debug(f"Trashed existing file: '{target}'.")
            shutil.move(temp_path, target)


def _write_sync_meta(ctx: _Context) -> None:
    old = ctx.song.sync_meta
    sync_meta_id = old.sync_meta_id if old else SyncMetaId.new()
    ctx.song.sync_meta = SyncMeta(
        sync_meta_id=sync_meta_id,
        song_id=ctx.song.song_id,
        usdb_mtime=ctx.song.usdb_mtime,
        path=ctx.locations.target_path(file=sync_meta_id.to_filename()),
        mtime=0,
        meta_tags=ctx.txt.meta_tags,
        pinned=old.pinned if old else False,
        custom_data=CustomData(old.custom_data.inner() if old else None),
    )

    # if any resource is unchanged, keep previous status
    if old:
        for job, kind in JOB_TO_RESOURCE_KIND.items():
            if ctx.results[job] is JobStatus.SKIPPED_UNCHANGED:
                resource = old.resource(kind)
                if resource and resource.status:
                    ctx.results[job] = resource.status

    ctx.song.sync_meta.txt = ctx.out.txt.to_resource(
        ctx.locations, temp=False, status=ctx.results[Job.TXT_WRITTEN]
    )
    ctx.song.sync_meta.audio = ctx.out.audio.to_resource(
        ctx.locations, temp=False, status=ctx.results[Job.AUDIO_DOWNLOAD]
    )
    ctx.song.sync_meta.video = ctx.out.video.to_resource(
        ctx.locations, temp=False, status=ctx.results[Job.VIDEO_DOWNLOAD]
    )
    ctx.song.sync_meta.cover = ctx.out.cover.to_resource(
        ctx.locations, temp=False, status=ctx.results[Job.COVER_DOWNLOAD]
    )
    ctx.song.sync_meta.background = ctx.out.background.to_resource(
        ctx.locations, temp=False, status=ctx.results[Job.BACKGROUND_DOWNLOAD]
    )
    ctx.song.sync_meta.synchronize_to_file()


class Job(Enum):
    """All jobs in the song download pipeline, in logical order."""

    AUDIO_DOWNLOAD = partial(_maybe_download_audio)
    VIDEO_DOWNLOAD = partial(_maybe_download_video)
    COVER_DOWNLOAD = partial(_maybe_download_cover)
    BACKGROUND_DOWNLOAD = partial(_maybe_download_background)
    # write txt after all file downloads to include correct filenames
    TXT_WRITTEN = partial(_maybe_write_txt)
    WRITE_AUDIO_TAGS = partial(_maybe_write_audio_tags)
    WRITE_VIDEO_TAGS = partial(_maybe_write_video_tags)

    def __call__(self, ctx: _Context) -> JobStatus:
        return self.value(ctx)

    def depends_on(self) -> tuple["Job", ...]:
        match self:
            case Job.WRITE_AUDIO_TAGS | Job.WRITE_VIDEO_TAGS:
                return (
                    Job.AUDIO_DOWNLOAD,
                    Job.COVER_DOWNLOAD,
                    Job.BACKGROUND_DOWNLOAD,
                    Job.TXT_WRITTEN,
                )
            case _:
                return ()


JOB_TO_RESOURCE_KIND: dict[Job, ResourceKind] = {
    Job.TXT_WRITTEN: ResourceKind.TXT,
    Job.AUDIO_DOWNLOAD: ResourceKind.AUDIO,
    Job.VIDEO_DOWNLOAD: ResourceKind.VIDEO,
    Job.COVER_DOWNLOAD: ResourceKind.COVER,
    Job.BACKGROUND_DOWNLOAD: ResourceKind.BACKGROUND,
}
