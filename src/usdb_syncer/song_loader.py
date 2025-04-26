"""Contains a runnable song loader."""

from __future__ import annotations

import copy
import shutil
import tempfile
import time
from collections.abc import Iterable, Iterator
from itertools import islice
from pathlib import Path
from typing import ClassVar, assert_never

import attrs
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
    usdb_scraper,
    utils,
)
from usdb_syncer.custom_data import CustomData
from usdb_syncer.discord import notify_discord
from usdb_syncer.logger import Logger, logger, song_logger
from usdb_syncer.postprocessing import write_audio_tags, write_video_tags
from usdb_syncer.resource_dl import ResourceDLError
from usdb_syncer.settings import FormatVersion
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.sync_meta import ResourceFile, SyncMeta
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

    def to_resource_file(
        self, locations: _Locations, temp: bool
    ) -> ResourceFile | None:
        if path_resource := self.path_and_resource(locations, temp=temp):
            return ResourceFile.new(*path_resource)
        return None


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

    def __attrs_post_init__(self) -> None:
        # reuse old resource files unless we acquire new ones later on
        # txt is always rewritten
        if self.song.sync_meta and (current := self.locations.current_path()):
            for old, out in (
                (self.song.sync_meta.audio, self.out.audio),
                (self.song.sync_meta.video, self.out.video),
                (self.song.sync_meta.cover, self.out.cover),
                (self.song.sync_meta.background, self.out.background),
            ):
                if old and old.is_in_sync(current.parent):
                    out.resource = old.resource
                    out.old_fname = old.fname

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
                song.song_id, paths.target_path().parent, txt.meta_tags
            )
        return cls(song, details, options, txt, paths, log)

    def all_audio_resources(self) -> Iterator[str]:
        if self.txt.meta_tags.audio:
            yield self.txt.meta_tags.audio
        if not self.txt.meta_tags.video:
            self.logger.debug("No valid audio/video meta tag. Looking in comments.")
        yield from self.all_video_resources()

    def all_video_resources(self) -> Iterator[str]:
        if self.txt.meta_tags.video:
            yield self.txt.meta_tags.video
        yield from self.details.all_comment_videos()

    def background_url(self) -> str | None:
        url = None
        if self.txt.meta_tags.background:
            url = self.txt.meta_tags.background.source_url(self.logger)
            self.logger.debug(f"downloading background from #VIDEO params: {url}")
        return url


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
                self.song.status = DownloadStatus.NONE
            except errors.UsdbLoginError:
                self.logger.error("Aborted; download requires login.")  # noqa: TRY400
                self.song.status = DownloadStatus.FAILED
            except errors.UsdbNotFoundError:
                self.logger.error("Song has been deleted from USDB.")  # noqa: TRY400
                with db.transaction():
                    self.song.delete()
                if meta := self.song.sync_meta:
                    path = meta.path.parent
                    self.logger.info(f"Trashing local song {path}")
                    send2trash.send2trash(path)
                events.SongDeleted(self.song_id).post()
                events.DownloadFinished(self.song_id).post()
                return
            except Exception:
                self.logger.exception(
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
            ctx = _Context.new(self.song, self.options, Path(tempdir), self.logger)
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


def _maybe_download_audio(ctx: _Context) -> None:
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
            resource_dl.ResourceDLError.RESOURCE_UNSUPPORTED,
            resource_dl.ResourceDLError.RESOURCE_UNAVAILABLE,
            resource_dl.ResourceDLError.RESOURCE_PARSE_ERROR,
        }:
            if ctx.options.notify_discord and (
                url := video_url_from_resource(resource)
            ):
                notify_discord(
                    ctx.song.song_id, url, "Audio", dl_result.error.value, logger
                )
    keep = " Keeping last resource." if ctx.out.audio.resource else ""
    song_len = ctx.txt.minimum_song_length()
    ctx.logger.error(f"Failed to download audio (song duration > {song_len})!{keep}")


def _maybe_download_video(ctx: _Context) -> None:
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
            resource_dl.ResourceDLError.RESOURCE_UNSUPPORTED,
            resource_dl.ResourceDLError.RESOURCE_UNAVAILABLE,
            resource_dl.ResourceDLError.RESOURCE_PARSE_ERROR,
        }:
            if ctx.options.notify_discord and (
                url := video_url_from_resource(resource)
            ):
                notify_discord(
                    ctx.song.song_id, url, "Video", dl_result.error.value, logger
                )
    keep = " Keeping last resource." if ctx.out.video.resource else ""
    ctx.logger.error(f"Failed to download video!{keep}")


def _maybe_download_cover(ctx: _Context) -> None:
    if not ctx.options.cover:
        return
    if ctx.txt.meta_tags.cover is None and ctx.details.cover_url is None:
        ctx.logger.warning("No cover resource found.")
        return
    if cover := ctx.txt.meta_tags.cover:
        url = cover.source_url(ctx.logger)
        if _download_cover_url(ctx, url):
            return
        if ctx.options.notify_discord:
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


def _download_cover_url(ctx: _Context, url: str, process: bool = True) -> bool:
    """True if download was successful (or is unnecessary)."""
    assert ctx.options.cover
    if ctx.out.cover.resource == url:
        if sync_meta := ctx.song.sync_meta:
            if sync_meta.meta_tags.cover == ctx.txt.meta_tags.cover:
                ctx.logger.info(
                    "Cover resource and postprocessing parameters are unchanged, "
                    "skipping."
                )
                return True
            ctx.logger.info(
                "Cover postprocessing parameters have changed, redownloading."
            )
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


def _maybe_download_background(ctx: _Context) -> None:
    if not (options := ctx.options.background_options):
        return
    if not options.download_background(bool(ctx.out.video.resource)):
        return
    if not (url := ctx.background_url()):
        ctx.logger.warning("No background resource found.")
        return
    if ctx.out.background.resource == url:
        if sync_meta := ctx.song.sync_meta:
            if sync_meta.meta_tags.background == ctx.txt.meta_tags.background:
                ctx.logger.info(
                    "Background resource and postprocessing parameters are unchanged, "
                    "skipping."
                )
                return
            ctx.logger.info(
                "Background postprocessing parameters have changed, redownloading."
            )
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
        if ctx.options.notify_discord:
            notify_discord(
                ctx.song.song_id,
                url,
                "Background",
                ResourceDLError.RESOURCE_UNAVAILABLE.value,
                ctx.logger,
            )
        keep = " Keeping last resource." if ctx.out.cover.resource else ""
        ctx.logger.error(f"Failed to download background!{keep}")


def _maybe_write_txt(ctx: _Context) -> None:
    if not (options := ctx.options.txt_options):
        return
    _write_headers(ctx)
    path = ctx.locations.temp_path(ext="txt")
    ctx.out.txt.new_fname = path.name
    ctx.txt.write_to_file(path, options.encoding.value, options.newline.value)
    ctx.out.txt.resource = ctx.song.song_id.usdb_gettxt_url()
    ctx.logger.info("Success! Created song txt.")


def _write_headers(ctx: _Context) -> None:
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
    if version == FormatVersion.V1_2_0 and (resource := ctx.txt.meta_tags.video):
        ctx.txt.headers.videourl = video_url_from_resource(resource)


def _set_cover_headers(ctx: _Context, version: FormatVersion, path: Path) -> None:
    ctx.txt.headers.cover = path.name
    if (
        version == FormatVersion.V1_2_0
        and ctx.txt.meta_tags.cover
        and (url := ctx.txt.meta_tags.cover.source_url(ctx.logger))
    ):
        ctx.txt.headers.coverurl = url


def _set_background_headers(ctx: _Context, version: FormatVersion, path: Path) -> None:
    ctx.txt.headers.background = path.name
    if (
        version == FormatVersion.V1_2_0
        and ctx.txt.meta_tags.background
        and (url := ctx.txt.meta_tags.background.source_url(ctx.logger))
    ):
        ctx.txt.headers.backgroundurl = url


def _maybe_write_audio_tags(ctx: _Context) -> None:
    if not (options := ctx.options.audio_options):
        return
    if not (
        audio_path_resource := ctx.out.audio.path_and_resource(ctx.locations, temp=True)
    ):
        return
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


def _maybe_write_video_tags(ctx: _Context) -> None:
    if not (options := ctx.options.video_options):
        return
    if not (
        video_path_resource := ctx.out.video.path_and_resource(ctx.locations, temp=True)
    ):
        return
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


def _cleanup_existing_resources(ctx: _Context) -> None:
    """Delete resources that are either out of sync or will be replaced with a new one,
    and ensure kept ones are correctly named.
    """
    if not ctx.song.sync_meta:
        return
    for (old, _), out in zip(
        ctx.song.sync_meta.all_resource_files(), ctx.out, strict=False
    ):
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


def _persist_tempfiles(ctx: _Context) -> None:
    for temp_file in ctx.out:
        if temp_file.new_fname and (
            temp_path := temp_file.path(ctx.locations, temp=True)
        ):
            target = ctx.locations.target_path(temp_path.name)
            if target.exists():
                send2trash.send2trash(target)
                ctx.logger.debug(f"Trashed existing file: '{target}'.")
            shutil.move(temp_path, target)


def _write_sync_meta(ctx: _Context) -> None:
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
