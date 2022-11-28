"""Contains a runnable song loader."""

import filecmp
import os
import re
from typing import Iterator

from PySide6.QtCore import QRunnable, QThreadPool

from usdb_syncer import SongId, note_utils, resource_dl, usdb_scraper
from usdb_syncer.download_options import Options, download_options
from usdb_syncer.logger import Logger, get_logger
from usdb_syncer.meta_tags.deserializer import MetaTags
from usdb_syncer.resource_dl import ImageKind, download_and_process_image
from usdb_syncer.usdb_scraper import SongDetails


class Context:
    """Context for downloading media and creating a song folder."""

    details: SongDetails
    options: Options
    songtext: str
    header: dict[str, str]
    notes: list[str]
    meta_tags: MetaTags
    dir_path: str
    # without extension
    filename: str
    # without extension
    file_path: str
    logger: Logger

    def __init__(self, details: SongDetails, options: Options, logger: Logger) -> None:
        self.details = details
        self.options = options

        self.songtext = usdb_scraper.get_notes(details.song_id, logger)
        self.header, self.notes = note_utils.parse_notes(self.songtext)
        # remove anything in "[]" from the title, e.g. "[duet]"
        self.header["#TITLE"] = re.sub(r"\[.*?\]", "", self.header["#TITLE"]).strip()

        # extract video tag
        self.meta_tags = MetaTags(self.header.pop("#VIDEO", ""), logger)

        self.filename = note_utils.generate_filename(self.header)
        self.dir_path = os.path.join(
            self.options.song_dir, self.filename, str(self.details.song_id)
        )
        self.file_path = os.path.join(self.dir_path, self.filename)
        self.logger = logger

    def all_audio_resources(self) -> Iterator[str]:
        if self.meta_tags.audio:
            yield self.meta_tags.audio
        yield from self.all_video_resources()

    def all_video_resources(self) -> Iterator[str]:
        if self.meta_tags.video:
            yield self.meta_tags.video
        yield from self.details.all_comment_videos()


class SongLoader(QRunnable):
    """Runnable to create a complete song folder."""

    def __init__(self, song_id: SongId, options: Options) -> None:
        super().__init__()
        self.song_id = song_id
        self.options = options
        self.logger = get_logger(__file__, song_id)

    def run(self) -> None:
        details = usdb_scraper.get_usdb_details(self.song_id, self.logger)
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

    if not os.path.exists(ctx.dir_path):
        os.makedirs(ctx.dir_path)
    temp_path = os.path.join(ctx.dir_path, "temp.usdb")
    usdb_path = os.path.join(ctx.dir_path, f"{ctx.details.song_id}.usdb")

    # write .usdb file for synchronization
    # songtxt may have CRLF newlines, so prevent Python from replacing LF with CRLF on
    # Windows
    with open(temp_path, "w", encoding="utf_8", newline="") as file:
        file.write(ctx.songtext)

    if os.path.exists(usdb_path):
        if filecmp.cmp(temp_path, usdb_path):
            ctx.logger.info("Aborted; song is already synchronized")
            os.remove(temp_path)
            return True

        ctx.logger.info("USDB file has been updated, re-downloading...")
        os.remove(usdb_path)

    os.rename(temp_path, usdb_path)
    return False


def _maybe_download_audio(ctx: Context) -> None:
    if not (options := ctx.options.audio_options):
        return
    for (idx, resource) in enumerate(ctx.all_audio_resources()):
        if idx > 9:
            break
        if ext := resource_dl.download_video(
            resource, options, ctx.options.browser, ctx.file_path, ctx.logger
        ):
            ctx.header["#MP3"] = f"{ctx.filename}.{ext}"
            ctx.logger.info("Success! Downloaded audio.")
            return
    ctx.logger.error("Failed to download audio!")


def _maybe_download_video(ctx: Context) -> None:
    if not (options := ctx.options.video_options) or ctx.meta_tags.is_audio_only():
        return
    for (idx, resource) in enumerate(ctx.all_video_resources()):
        if idx > 9:
            break
        if ext := resource_dl.download_video(
            resource, options, ctx.options.browser, ctx.file_path, ctx.logger
        ):
            ctx.header["#VIDEO"] = f"{ctx.filename}.{ext}"
            ctx.logger.info("Success! Downloaded video.")
            return
    ctx.logger.error("Failed to download video!")


def _maybe_download_cover(ctx: Context) -> None:
    if not ctx.options.cover:
        return

    if download_and_process_image(
        ctx.header,
        ctx.meta_tags.cover,
        ctx.details,
        ctx.dir_path,
        ImageKind.COVER,
        max_width=ctx.options.cover.max_size,
    ):
        ctx.header["#COVER"] = f"{ctx.filename} [CO].jpg"
        ctx.logger.info("Success! Downloaded cover.")
    else:
        ctx.logger.error("Failed to download cover!")


def _maybe_download_background(ctx: Context) -> None:
    if not (options := ctx.options.background_options):
        return
    if not options.download_background("#VIDEO" in ctx.header):
        return
    if download_and_process_image(
        ctx.header,
        ctx.meta_tags.background,
        ctx.details,
        ctx.dir_path,
        ImageKind.BACKGROUND,
        max_width=None,
    ):
        ctx.header["#BACKGROUND"] = f"{ctx.filename} [BG].jpg"
        ctx.logger.info("Success! Downloaded background.")
    else:
        ctx.logger.error("Failed to download background!")


def _maybe_write_txt(ctx: Context) -> None:
    if not (options := ctx.options.txt_options):
        return
    _set_missing_headers(ctx)
    note_utils.dump_notes(ctx.header, ctx.notes, ctx.dir_path, options, ctx.logger)
    ctx.logger.info("Success! Created song txt.")


def _set_missing_headers(ctx: Context) -> None:
    _maybe_set_player_tags_and_markers(ctx)
    if ctx.meta_tags.preview is not None:
        ctx.header["#PREVIEWSTART"] = str(ctx.meta_tags.preview)
    if medley := ctx.meta_tags.medley:
        ctx.header["#MEDLEYSTARTBEAT"] = str(medley.start)
        ctx.header["#MEDLEYENDBEAT"] = str(medley.end)


def _maybe_set_player_tags_and_markers(ctx: Context) -> None:
    if not note_utils.is_duet(ctx.header, ctx.meta_tags):
        return

    ctx.header["#P1"] = ctx.meta_tags.player1 or "P1"
    ctx.header["#P2"] = ctx.meta_tags.player2 or "P2"

    ctx.notes.insert(0, "P1\n")
    prev_start = 0
    for idx, line in enumerate(ctx.notes):
        if line.startswith((":", "*", "F", "R", "G")):
            _type, start, _duration, _pitch, *_syllable = line.split(" ", maxsplit=4)
            if int(start) < prev_start:
                ctx.notes.insert(idx, "P2\n")
                ctx.logger.debug("Success! Restored duet markers.")
                return
            prev_start = int(start)
    ctx.logger.error("Failed to restore duet markers!")
