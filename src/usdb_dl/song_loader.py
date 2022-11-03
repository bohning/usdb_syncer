"""Contains a runnable song loader."""

import filecmp
import logging
import os
import re

from PySide6.QtCore import QRunnable

from usdb_dl import SongId, note_utils, resource_dl, usdb_scraper
from usdb_dl.options import Options

_logger: logging.Logger = logging.getLogger(__file__)


class SongLoader(QRunnable):
    """Runnable to create a complete song folder."""

    def __init__(self, song_id: SongId, options: Options) -> None:
        super().__init__()
        self.song_id = song_id
        self.options = options

    def run(self) -> None:
        _logger.info(f"#{self.song_id}: Downloading song...")
        _logger.info(f"#{self.song_id}: (1/6) downloading usdb file...")
        ###
        if (details := usdb_scraper.get_usdb_details(self.song_id)) is None:
            # song was deleted from usdb in the meantime, TODO: uncheck/remove from model
            return

        songtext = usdb_scraper.get_notes(self.song_id)

        header, notes = note_utils.parse_notes(songtext)

        # TODO: this is not updated until after download all songs
        # self.statusbar.showMessage(f"Downloading '{header['#ARTIST']} - {header['#TITLE']}' ({num+1}/{len(ids)})")

        header["#TITLE"] = re.sub(
            r"\[.*?\]", "", header["#TITLE"]
        ).strip()  # remove anything in "[]" from the title, e.g. "[duet]"
        resource_params = note_utils.get_params_from_video_tag(header)

        duet = note_utils.is_duet(header, resource_params)
        if duet:
            header["#P1"] = resource_params.get("p1", "P1")
            header["#P2"] = resource_params.get("p2", "P2")

            notes.insert(0, "P1\n")
            prev_start = 0
            for idx, line in enumerate(notes):
                if line.startswith((":", "*", "F", "R", "G")):
                    _type, start, _duration, _pitch, *_syllable = line.split(
                        " ", maxsplit=4
                    )
                    if int(start) < prev_start:
                        notes.insert(idx, "P2\n")
                    prev_start = int(start)

        _logger.info(f"#{self.song_id}: (1/6) {header['#ARTIST']} - {header['#TITLE']}")

        dirname = note_utils.generate_dirname(header, resource_params)
        pathname = os.path.join(self.options.song_dir, dirname, str(self.song_id))

        if not os.path.exists(pathname):
            os.makedirs(pathname)

        # write .usdb file for synchronization
        with open(os.path.join(pathname, "temp.usdb"), "w", encoding="utf_8") as file:
            file.write(songtext)
        if os.path.exists(os.path.join(pathname, f"{self.song_id}.usdb")):
            if filecmp.cmp(
                os.path.join(pathname, "temp.usdb"),
                os.path.join(pathname, f"{self.song_id}.usdb"),
            ):
                _logger.info(
                    f"#{self.song_id}: (1/6) usdb and local file are identical, no need to re-download. Skipping song."
                )
                os.remove(os.path.join(pathname, "temp.usdb"))
                return
            _logger.info(
                f"#{self.song_id}: (1/6) usdb file has been updated, re-downloading..."
            )
            # TODO: check if resources in #VIDEO tag have changed and if so, re-download
            # new resources only
            os.remove(os.path.join(pathname, f"{self.song_id}.usdb"))
            os.rename(
                os.path.join(pathname, "temp.usdb"),
                os.path.join(pathname, f"{self.song_id}.usdb"),
            )
        else:
            os.rename(
                os.path.join(pathname, "temp.usdb"),
                os.path.join(pathname, f"{self.song_id}.usdb"),
            )
        ###
        _logger.info(f"#{self.song_id}: (2/6) downloading audio file...")
        ###
        has_audio = False
        if audio_opts := self.options.audio_options:
            if audio_resource := resource_params.get("a"):
                pass
            elif audio_resource := resource_params.get("v"):
                pass
            # else:
            #    video_params = details.get("video_params")
            #    if video_params:
            #        audio_resource = video_params.get("v")
            #        if audio_resource:
            #            _logger.warning(
            #                f"#{self.song_id}: (2/6) Using Youtube ID {audio_resource} extracted from comments."
            #            )

            if audio_resource:
                has_audio, ext = resource_dl.download_and_process_audio(
                    header, audio_resource, audio_opts, self.options.browser, pathname
                )

                # delete #VIDEO tag used for resources
                if header.get("#VIDEO"):
                    header.pop("#VIDEO")

                if has_audio:
                    header["#MP3"] = f"{note_utils.generate_filename(header)}.{ext}"
                    _logger.info(f"#{self.song_id}: (2/6) Success.")
                    # self.model.setItem(self.model.findItems(self.kwargs['id'], flags=Qt.MatchExactly, column=0)[0].row(), 9, QStandardItem(QIcon(":/icons/tick.png"), ""))
                else:
                    _logger.error(f"#{self.song_id}: (2/6) Failed.")
        ###
        _logger.info(f"#{self.song_id}: (3/6) downloading video file...")
        ###
        has_video = False
        if video_opts := self.options.video_options:
            if video_resource := resource_params.get("v"):
                pass
            # elif not resource_params.get("a"):
            #    video_params = details.get("video_params")
            #    if video_params:
            #        video_resource = video_params.get("v")
            #        if video_resource:
            #            _logger.warning(
            #                f"#{self.song_id}: (3/6) Using Youtube ID {audio_resource} extracted from comments."
            #            )

            if video_resource:
                has_video = resource_dl.download_and_process_video(
                    header,
                    video_resource,
                    video_opts,
                    resource_params,
                    self.options.browser,
                    pathname,
                )

                if has_video:
                    header[
                        "#VIDEO"
                    ] = f"{note_utils.generate_filename(header)}{video_opts.format}"
                    _logger.info(f"#{self.song_id}: (3/6) Success.")
                    # self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 10, QStandardItem(QIcon(":/icons/tick.png"), ""))
                else:
                    _logger.error(f"#{self.song_id}: (3/6) Failed.")
            else:
                _logger.warning(
                    f"#{self.song_id}: (3/6) no video resource in #VIDEO tag"
                )
        ###
        _logger.info(f"#{self.song_id}: (4/6) downloading cover file...")
        ###
        has_cover = False
        if self.options.cover:
            has_cover = resource_dl.download_and_process_cover(
                header, resource_params, details, pathname
            )
            if has_cover:
                header["#COVER"] = f"{note_utils.generate_filename(header)} [CO].jpg"
                _logger.info(f"#{self.song_id}: (4/6) Success.")
                # self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 11, QStandardItem(QIcon(":/icons/tick.png"), ""))
            else:
                _logger.error(f"#{self.song_id}: (4/6) Failed.")
        ###
        _logger.info(f"#{self.song_id}: (5/6) downloading background file...")
        ###
        if bg_opts := self.options.background_options:
            if bg_opts.download_background(has_video):
                has_background = resource_dl.download_and_process_background(
                    header, resource_params, pathname
                )

                if has_background:
                    header[
                        "#BACKGROUND"
                    ] = f"{note_utils.generate_filename(header)} [BG].jpg"
                    _logger.info(f"#{self.song_id}: (5/6) Success.")
                    # self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 12, QStandardItem(QIcon(":/icons/tick.png"), ""))
                else:
                    _logger.error(f"#{self.song_id}: (5/6) Failed.")
        ###
        _logger.info(f"#{self.song_id}: (6/6) writing song text file...")
        ###
        if txt_opts := self.options.txt_options:
            filename = note_utils.dump_notes(
                header, notes, pathname, txt_opts, duet=duet
            )

            if filename:
                _logger.info(f"#{self.song_id}: (6/6) Success.")
                # self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 8, QStandardItem(QIcon(":/icons/tick.png"), ""))
            else:
                _logger.error(f"#{self.song_id}: (6/6) Failed.")
            ###
            _logger.info(f"#{self.song_id}: (6/6) Download completed!")
