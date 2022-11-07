"""Contains a runnable song loader."""

import filecmp
import logging
import os
import re

from PySide6.QtCore import QRunnable

from usdb_dl import SongId, note_utils, resource_dl, usdb_scraper
from usdb_dl.meta_tags import MetaTags
from usdb_dl.options import Options
from usdb_dl.resource_dl import ImageKind, download_and_process_image
from usdb_dl.usdb_scraper import SongDetails

_logger: logging.Logger = logging.getLogger(__file__)


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

    def __init__(self, details: SongDetails, options: Options) -> None:
        self.details = details
        self.options = options
        self.songtext = usdb_scraper.get_notes(details.song_id)
        self.header, self.notes = note_utils.parse_notes(self.songtext)
        # remove anything in "[]" from the title, e.g. "[duet]"
        self.header["#TITLE"] = re.sub(r"\[.*?\]", "", self.header["#TITLE"]).strip()
        # extract video tag
        self.meta_tags = MetaTags(self.header.pop("#VIDEO", ""))
        dirname = note_utils.generate_dirname(self.header, bool(self.meta_tags.video))
        self.dir_path = os.path.join(
            self.options.song_dir, dirname, str(self.details.song_id)
        )
        self.filename = note_utils.generate_filename(self.header)
        self.file_path = os.path.join(self.dir_path, self.filename)


class SongLoader(QRunnable):
    """Runnable to create a complete song folder."""

    def __init__(self, song_id: SongId, options: Options) -> None:
        super().__init__()
        self.song_id = song_id
        self.options = options

    def run(self) -> None:
        _logger.info(f"#{self.song_id}: Downloading song...")
        _logger.info(f"#{self.song_id}: (1/6) downloading usdb file...")

        if (details := usdb_scraper.get_usdb_details(self.song_id)) is None:
            # song was deleted from usdb in the meantime, TODO: uncheck/remove from model
            return

        ctx = Context(details, self.options)
        _maybe_write_player_tags(ctx)
        _logger.info(
            f"#{self.song_id}: (1/6) {ctx.header['#ARTIST']} - {ctx.header['#TITLE']}"
        )

        if _find_or_initialize_folder(ctx):
            return
        ###
        _logger.info(f"#{self.song_id}: (2/6) downloading audio file...")
        _maybe_download_audio(ctx)
        _logger.info(f"#{self.song_id}: (3/6) downloading video file...")
        _maybe_download_video(ctx)
        _logger.info(f"#{self.song_id}: (4/6) downloading cover file...")
        _maybe_download_cover(ctx)
        _logger.info(f"#{self.song_id}: (5/6) downloading background file...")
        _maybe_download_background(ctx)
        _logger.info(f"#{self.song_id}: (6/6) writing song text file...")
        _maybe_write_txt(ctx)
        _logger.info(f"#{self.song_id}: (6/6) Download completed!")


def _find_or_initialize_folder(ctx: Context) -> bool:
    """True if the folder already exists and is up to date."""

    if not os.path.exists(ctx.dir_path):
        os.makedirs(ctx.dir_path)
    temp_path = os.path.join(ctx.dir_path, "temp.usdb")
    usdb_path = os.path.join(ctx.dir_path, f"{ctx.details.song_id}.usdb")

    # write .usdb file for synchronization
    with open(temp_path, "w", encoding="utf_8") as file:
        file.write(ctx.songtext)

    if os.path.exists(usdb_path):
        if filecmp.cmp(temp_path, usdb_path):
            _logger.info(
                f"#{ctx.details.song_id}: (1/6) usdb and local file are identical, "
                "no need to re-download. Skipping song."
            )
            os.remove(temp_path)
            return True

        _logger.info(
            f"#{ctx.details.song_id}: (1/6) usdb file has been updated, re-downloading..."
        )
        # TODO: check if resources in #VIDEO tag have changed and if so, re-download
        # new resources only
        os.remove(usdb_path)

    os.rename(temp_path, usdb_path)
    return False


def _maybe_write_player_tags(ctx: Context) -> None:
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
            prev_start = int(start)


def _maybe_download_audio(ctx: Context) -> None:
    if not (options := ctx.options.audio_options):
        return

    # else:
    #    video_params = details.get("video_params")
    #    if video_params:
    #        audio_resource = video_params.get("v")
    #        if audio_resource:
    #            _logger.warning(
    #                f"#{self.song_id}: (2/6) Using Youtube ID {audio_resource} extracted from comments."
    #            )
    if resource := ctx.meta_tags.audio or ctx.meta_tags.video:
        if ext := resource_dl.download_video(
            resource, options, ctx.options.browser, ctx.file_path
        ):
            ctx.header["#MP3"] = f"{ctx.filename}.{ext}"
            _logger.info(f"#{ctx.details.song_id}: (2/6) Success.")
            # self.model.setItem(self.model.findItems(self.kwargs['id'], flags=Qt.MatchExactly, column=0)[0].row(), 9, QStandardItem(QIcon(":/icons/tick.png"), ""))
        else:
            _logger.error(f"#{ctx.details.song_id}: (2/6) Failed.")
    else:
        _logger.warning("\t- no audio resource in #VIDEO tag")


def _maybe_download_video(ctx: Context) -> None:
    if not (options := ctx.options.video_options):
        return

        # elif not resource_params.get("a"):
        #    video_params = details.get("video_params")
        #    if video_params:
        #        video_resource = video_params.get("v")
        #        if video_resource:
        #            _logger.warning(
        #                f"#{self.song_id}: (3/6) Using Youtube ID {audio_resource} extracted from comments."
        #            )
    if resource := ctx.meta_tags.video:
        if ext := resource_dl.download_video(
            resource, options, ctx.options.browser, ctx.file_path
        ):
            ctx.header["#VIDEO"] = f"{ctx.filename}.{ext}"
            _logger.info(f"#{ctx.details.song_id}: (3/6) Success.")
            # self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 10, QStandardItem(QIcon(":/icons/tick.png"), ""))
        else:
            _logger.error(f"#{ctx.details.song_id}: (3/6) Failed.")
    else:
        _logger.warning(
            f"#{ctx.details.song_id}: (3/6) no video resource in #VIDEO tag"
        )


def _maybe_download_cover(ctx: Context) -> None:
    if not ctx.options.cover:
        return

    if download_and_process_image(
        ctx.header, ctx.meta_tags.cover, ctx.details, ctx.dir_path, ImageKind.COVER
    ):
        ctx.header["#COVER"] = f"{ctx.filename} [CO].jpg"
        _logger.info(f"#{ctx.details.song_id}: (4/6) Success.")
        # ctx.model.setItem(ctx.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 11, QStandardItem(QIcon(":/icons/tick.png"), ""))
    else:
        _logger.error(f"#{ctx.details.song_id}: (4/6) Failed.")


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
    ):
        ctx.header["#BACKGROUND"] = f"{ctx.filename} [BG].jpg"
        _logger.info(f"#{ctx.details.song_id}: (5/6) Success.")
        # ctx.model.setItem(ctx.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 12, QStandardItem(QIcon(":/icons/tick.png"), ""))
    else:
        _logger.error(f"#{ctx.details.song_id}: (5/6) Failed.")


def _maybe_write_txt(ctx: Context) -> None:
    if not (options := ctx.options.txt_options):
        return
    ctx.filename = note_utils.dump_notes(ctx.header, ctx.notes, ctx.dir_path, options)
    if ctx.filename:
        _logger.info(f"#{ctx.details.song_id}: (6/6) Success.")
        # ctx.model.setItem(ctx.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 8, QStandardItem(QIcon(":/icons/tick.png"), ""))
    else:
        _logger.error(f"#{ctx.details.song_id}: (6/6) Failed.")
