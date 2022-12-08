"""Contains a runnable song loader."""

import os
from typing import Iterator

from PySide6.QtCore import QRunnable, QThreadPool

from usdb_syncer import SongId, resource_dl, usdb_scraper
from usdb_syncer.download_options import Options, download_options
from usdb_syncer.logger import Log, get_logger
from usdb_syncer.notes_parser import SongTxt
from usdb_syncer.resource_dl import ImageKind, download_and_process_image
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.usdb_scraper import SongDetails
from usdb_syncer.utils import sanitize_filename


class Context:
    """Context for downloading media and creating a song folder."""

    details: SongDetails
    options: Options
    songtext: str
    txt: SongTxt
    dir_path: str
    # without extension
    filename_stem: str
    # without extension
    file_path_stem: str
    logger: Log

    def __init__(self, details: SongDetails, options: Options, logger: Log) -> None:
        self.details = details
        self.options = options

        self.songtext = usdb_scraper.get_notes(details.song_id, logger)
        self.txt = SongTxt.parse(self.songtext, logger)
        self.txt.headers.reset_file_location_headers()
        self.txt.notes.maybe_split_duet_notes()
        self.txt.restore_missing_headers()

        self.filename_stem = sanitize_filename(self.txt.headers.artist_title_str())
        self.dir_path = os.path.join(
            self.options.song_dir, self.filename_stem, str(self.details.song_id)
        )
        self.file_path_stem = os.path.join(self.dir_path, self.filename_stem)
        self.logger = logger

    def all_audio_resources(self) -> Iterator[str]:
        if self.txt.meta_tags.audio:
            yield self.txt.meta_tags.audio
        yield from self.all_video_resources()

    def all_video_resources(self) -> Iterator[str]:
        if self.txt.meta_tags.video:
            yield self.txt.meta_tags.video
        yield from self.details.all_comment_videos()


class SongLoader(QRunnable):
    """Runnable to create a complete song folder."""

    def __init__(self, song_id: SongId, options: Options) -> None:
        super().__init__()
        self.song_id = song_id
        self.options = options
        self.logger = get_logger(__file__, song_id)

    def run(self) -> None:
        details = usdb_scraper.get_usdb_details(self.song_id)
        if details is None:
            # song was deleted from usdb in the meantime, TODO: uncheck/remove from model
            self.logger.error("Could not find song on USDB!")
            return
        self.logger.info(f"Found '{details.artist} - {details.title}' on  USDB")
        ctx = Context(details, self.options, self.logger)
        if _find_or_initialize_folder(ctx):
            return
        _maybe_download_audio(ctx)
        _maybe_download_video(ctx)
        _maybe_download_cover(ctx)
        _maybe_download_background(ctx)
        _maybe_write_txt(ctx)
        self.logger.info("All done!")


def download_songs(ids: list[SongId]) -> None:
    options = download_options()
    threadpool = QThreadPool.globalInstance()
    for song_id in ids:
        worker = SongLoader(song_id=song_id, options=options)
        threadpool.start(worker)


def _find_or_initialize_folder(ctx: Context) -> bool:
    """True if the folder already exists and is up to date."""
    usdb_path = os.path.join(ctx.dir_path, f"{ctx.details.song_id}.usdb")
    if os.path.exists(usdb_path) and (meta := SyncMeta.try_from_file(usdb_path)):
        if not meta.update_txt_hash(ctx.songtext):
            ctx.logger.info("Aborted; song is already synchronized")
            return True
        ctx.logger.info("USDB file has been updated, re-downloading...")
    else:
        os.makedirs(ctx.dir_path, exist_ok=True)
        meta = SyncMeta.new(ctx.details.song_id, ctx.songtext)
    meta.to_file(ctx.dir_path)
    return False


def _maybe_download_audio(ctx: Context) -> None:
    if not (options := ctx.options.audio_options):
        return
    for (idx, resource) in enumerate(ctx.all_audio_resources()):
        if idx > 9:
            break
        if ext := resource_dl.download_video(
            resource, options, ctx.options.browser, ctx.file_path_stem, ctx.logger
        ):
            ctx.txt.headers.mp3 = f"{ctx.filename_stem}.{ext}"
            ctx.logger.info("Success! Downloaded audio.")
            return
    ctx.logger.error("Failed to download audio!")


def _maybe_download_video(ctx: Context) -> None:
    if not (options := ctx.options.video_options) or ctx.txt.meta_tags.is_audio_only():
        return
    for (idx, resource) in enumerate(ctx.all_video_resources()):
        if idx > 9:
            break
        if ext := resource_dl.download_video(
            resource, options, ctx.options.browser, ctx.file_path_stem, ctx.logger
        ):
            ctx.txt.headers.video = f"{ctx.filename_stem}.{ext}"
            ctx.logger.info("Success! Downloaded video.")
            return
    ctx.logger.error("Failed to download video!")


def _maybe_download_cover(ctx: Context) -> None:
    if not ctx.options.cover:
        return

    if filename := download_and_process_image(
        ctx.filename_stem,
        ctx.txt.meta_tags.cover,
        ctx.details,
        ctx.dir_path,
        ImageKind.COVER,
        max_width=ctx.options.cover.max_size,
    ):
        ctx.txt.headers.cover = filename
        ctx.logger.info("Success! Downloaded cover.")
    else:
        ctx.logger.error("Failed to download cover!")


def _maybe_download_background(ctx: Context) -> None:
    if not (options := ctx.options.background_options):
        return
    if not options.download_background(bool(ctx.txt.headers.video)):
        return
    if filename := download_and_process_image(
        ctx.filename_stem,
        ctx.txt.meta_tags.background,
        ctx.details,
        ctx.dir_path,
        ImageKind.BACKGROUND,
        max_width=None,
    ):
        ctx.txt.headers.background = filename
        ctx.logger.info("Success! Downloaded background.")
    else:
        ctx.logger.error("Failed to download background!")


def _maybe_write_txt(ctx: Context) -> None:
    if not (options := ctx.options.txt_options):
        return
    ctx.txt.write_to_file(
        f"{ctx.file_path_stem}.txt", options.encoding.value, options.newline.value
    )
    ctx.logger.info("Success! Created song txt.")
