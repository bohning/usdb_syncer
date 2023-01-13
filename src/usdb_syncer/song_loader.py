"""Contains a runnable song loader."""

from __future__ import annotations

import os
from typing import Callable, Iterator

import attrs
from PySide6.QtCore import QRunnable, QThreadPool

from usdb_syncer import SongId, resource_dl, usdb_scraper
from usdb_syncer.download_options import Options, download_options
from usdb_syncer.encoding import CodePage
from usdb_syncer.logger import Log, get_logger
from usdb_syncer.resource_dl import ImageKind, download_and_process_image
from usdb_syncer.song_data import LocalFiles, SongData
from usdb_syncer.song_txt import Headers, SongTxt
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.usdb_scraper import SongDetails
from usdb_syncer.utils import (
    is_name_maybe_with_suffix,
    next_unique_directory,
    sanitize_filename,
)


@attrs.define
class DownloadInfo:
    """Data required to start a song download."""

    song_id: SongId
    meta_path: str | None
    encoding: CodePage

    @classmethod
    def from_song_data(cls, data: SongData) -> DownloadInfo:
        return cls(
            data.data.song_id,
            data.local_files.usdb_path,
            CodePage.from_language(data.data.language),
        )


@attrs.define(kw_only=True)
class Locations:
    """Paths for downloading a song."""

    meta_path: str
    dir_path: str
    filename_stem: str
    file_path_stem: str

    @classmethod
    def new(
        cls, song_id: SongId, song_dir: str, meta_path: str | None, headers: Headers
    ) -> Locations:
        filename_stem = sanitize_filename(headers.artist_title_str())
        if meta_path:
            dir_path = os.path.dirname(meta_path)
        else:
            dir_path = next_unique_directory(os.path.join(song_dir, filename_stem))
            meta_path = os.path.join(dir_path, f"{song_id}.usdb")
        return cls(
            meta_path=meta_path,
            dir_path=dir_path,
            filename_stem=filename_stem,
            file_path_stem=os.path.join(dir_path, filename_stem),
        )

    def update_dir_path(self, dir_path: str) -> None:
        self.dir_path = dir_path
        self.meta_path = os.path.join(dir_path, os.path.basename(self.meta_path))
        self.file_path_stem = os.path.join(dir_path, self.filename_stem)


@attrs.define
class Context:
    """Context for downloading media and creating a song folder."""

    details: SongDetails
    options: Options
    txt: SongTxt
    locations: Locations
    sync_meta: SyncMeta
    new_src_txt: bool
    logger: Log

    @classmethod
    def new(
        cls, details: SongDetails, options: Options, info: DownloadInfo, logger: Log
    ) -> Context:
        txt_str = usdb_scraper.get_notes(details.song_id, info.encoding, logger)
        txt = SongTxt.parse(txt_str, logger)
        txt.sanitize()
        paths = Locations.new(
            details.song_id, options.song_dir, info.meta_path, txt.headers
        )
        sync_meta, new_src_txt = _load_sync_meta(
            paths.meta_path, details.song_id, txt_str
        )
        return cls(details, options, txt, paths, sync_meta, new_src_txt, logger)

    def all_audio_resources(self) -> Iterator[str]:
        if self.txt.meta_tags.audio:
            yield self.txt.meta_tags.audio
        yield from self.all_video_resources()

    def all_video_resources(self) -> Iterator[str]:
        if self.txt.meta_tags.video:
            yield self.txt.meta_tags.video
        yield from self.details.all_comment_videos()


def _load_sync_meta(path: str, song_id: SongId, new_txt: str) -> tuple[SyncMeta, bool]:
    """True if new_txt is different to the last one (if any)."""
    if os.path.exists(path) and (meta := SyncMeta.try_from_file(path)):
        updated = meta.update_src_txt_hash(new_txt)
        return meta, updated
    return SyncMeta.new(song_id, new_txt), True


class SongLoader(QRunnable):
    """Runnable to create a complete song folder."""

    def __init__(
        self,
        info: DownloadInfo,
        options: Options,
        on_start: Callable[[SongId], None],
        on_finish: Callable[[SongId, LocalFiles], None],
    ) -> None:
        super().__init__()
        self.song_id = info.song_id
        self.data = info
        self.options = options
        self.on_start = on_start
        self.on_finish = on_finish
        self.logger = get_logger(__file__, info.song_id)

    def run(self) -> None:
        self.on_start(self.song_id)
        details = usdb_scraper.get_usdb_details(self.song_id)
        if details is None:
            # song was deleted from usdb in the meantime, TODO: uncheck/remove from model
            self.logger.error("Could not find song on USDB!")
            return
        self.logger.info(f"Found '{details.artist} - {details.title}' on  USDB")
        ctx = Context.new(details, self.options, self.data, self.logger)
        if not ctx.new_src_txt:
            ctx.logger.info("Aborted; song is already synchronized")
            return
        os.makedirs(ctx.locations.dir_path, exist_ok=True)
        _ensure_correct_folder_name(ctx.locations)
        _maybe_download_audio(ctx)
        _maybe_download_video(ctx)
        _maybe_download_cover(ctx)
        _maybe_download_background(ctx)
        _maybe_write_txt(ctx)
        _write_sync_meta(ctx)
        self.logger.info("All done!")
        self.on_finish(
            self.song_id,
            LocalFiles.from_sync_meta(ctx.locations.meta_path, ctx.sync_meta),
        )


def download_songs(
    infos: list[DownloadInfo],
    on_start: Callable[[SongId], None],
    on_finish: Callable[[SongId, LocalFiles], None],
) -> None:
    options = download_options()
    threadpool = QThreadPool.globalInstance()
    for info in infos:
        worker = SongLoader(info, options, on_start, on_finish)
        threadpool.start(worker)


def _maybe_download_audio(ctx: Context) -> None:
    if not (options := ctx.options.audio_options):
        return
    for (idx, resource) in enumerate(ctx.all_audio_resources()):
        if idx > 9:
            break
        if ext := resource_dl.download_video(
            resource,
            options,
            ctx.options.browser,
            ctx.locations.file_path_stem,
            ctx.logger,
        ):
            path = f"{ctx.locations.file_path_stem}.{ext}"
            ctx.sync_meta.set_audio_meta(path)
            ctx.txt.headers.mp3 = os.path.basename(path)
            ctx.logger.info("Success! Downloaded audio.")
            return

    ctx.logger.error(
        f"Failed to download audio (song duration > {ctx.txt.minimum_song_length()})!"
    )


def _maybe_download_video(ctx: Context) -> None:
    if not (options := ctx.options.video_options) or ctx.txt.meta_tags.is_audio_only():
        return
    for (idx, resource) in enumerate(ctx.all_video_resources()):
        if idx > 9:
            break
        if ext := resource_dl.download_video(
            resource,
            options,
            ctx.options.browser,
            ctx.locations.file_path_stem,
            ctx.logger,
        ):
            path = f"{ctx.locations.file_path_stem}.{ext}"
            ctx.sync_meta.set_video_meta(path)
            ctx.txt.headers.video = os.path.basename(path)
            ctx.logger.info("Success! Downloaded video.")
            return
    ctx.logger.error("Failed to download video!")


def _maybe_download_cover(ctx: Context) -> None:
    if not ctx.options.cover:
        return

    if filename := download_and_process_image(
        ctx.locations.filename_stem,
        ctx.txt.meta_tags.cover,
        ctx.details,
        ctx.locations.dir_path,
        ImageKind.COVER,
        max_width=ctx.options.cover.max_size,
    ):
        ctx.txt.headers.cover = filename
        ctx.sync_meta.set_cover_meta(os.path.join(ctx.locations.dir_path, filename))
        ctx.logger.info("Success! Downloaded cover.")
    else:
        ctx.logger.error("Failed to download cover!")


def _maybe_download_background(ctx: Context) -> None:
    if not (options := ctx.options.background_options):
        return
    if not options.download_background(bool(ctx.txt.headers.video)):
        return
    if filename := download_and_process_image(
        ctx.locations.filename_stem,
        ctx.txt.meta_tags.background,
        ctx.details,
        ctx.locations.dir_path,
        ImageKind.BACKGROUND,
        max_width=None,
    ):
        ctx.txt.headers.background = filename
        ctx.sync_meta.set_background_meta(
            os.path.join(ctx.locations.dir_path, filename)
        )
        ctx.logger.info("Success! Downloaded background.")
    else:
        ctx.logger.error("Failed to download background!")


def _maybe_write_txt(ctx: Context) -> None:
    if not (options := ctx.options.txt_options):
        return
    path = f"{ctx.locations.file_path_stem}.txt"
    ctx.txt.write_to_file(path, options.encoding.value, options.newline.value)
    ctx.sync_meta.set_txt_meta(path)
    ctx.logger.info("Success! Created song txt.")


def _write_sync_meta(ctx: Context) -> None:
    ctx.sync_meta.to_file(ctx.locations.dir_path)


def _ensure_correct_folder_name(locations: Locations) -> None:
    folder_dir, folder_name = os.path.split(locations.dir_path)
    if is_name_maybe_with_suffix(folder_name, locations.filename_stem):
        return
    new = next_unique_directory(os.path.join(folder_dir, locations.filename_stem))
    os.rename(locations.dir_path, new)
    locations.update_dir_path(new)
