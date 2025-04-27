"""Parsed UltraStar txt file."""

from __future__ import annotations

from pathlib import Path
from typing import assert_never

import attrs

from usdb_syncer import download_options, errors
from usdb_syncer.logger import Logger
from usdb_syncer.meta_tags import MetaTags
from usdb_syncer.settings import FixLinebreaks, FixSpaces
from usdb_syncer.song_txt.headers import Headers
from usdb_syncer.song_txt.tracks import Tracks


@attrs.define()
class SongTxt:
    """A parsed .txt file of an UltraStar song."""

    headers: Headers
    notes: Tracks
    meta_tags: MetaTags
    logger: Logger

    def __str__(self) -> str:
        return f"{self.headers}\n{self.notes}"

    def unsynchronized_lyrics(self) -> str:
        track_1 = "\n".join(line.text().rstrip() for line in self.notes.track_1)
        if self.notes.track_2:
            track_2 = "\n".join(line.text().rstrip() for line in self.notes.track_2)
            return f"[{self.headers.p1}]:\n{track_1}\n\n[{self.headers.p2}]:\n{track_2}"
        return track_1

    def synchronized_lyrics(self) -> list[tuple[str, int]]:
        # format: list of tuples (lrc, millisecond)
        return [
            (
                line.text(),
                round(self.headers.bpm.beats_to_ms(line.start()) + self.headers.gap),
            )
            for line in self.notes.all_lines()
        ]

    @classmethod
    def parse(cls, value: str, logger: Logger) -> SongTxt:
        lines = [line for line in value.splitlines() if line]
        headers = Headers.parse(lines, logger)
        meta_tags = MetaTags.parse(headers.video or "", logger)
        notes = Tracks.parse(lines, logger)
        if lines:
            logger.warning(f"trailing text in song txt: '{lines}'")
        return cls(headers=headers, meta_tags=meta_tags, notes=notes, logger=logger)

    @classmethod
    def try_parse(cls, value: str, logger: Logger) -> SongTxt | None:
        try:
            return cls.parse(value, logger)
        except errors.TxtParseError:
            return None

    def maybe_split_duet_notes(self) -> None:
        if self.headers.relative and self.headers.relative.lower() == "yes":
            return
        self.notes.maybe_split_duet_notes()

    def restore_missing_headers(self) -> None:
        if self.notes.track_2:
            self.headers.p1 = self.meta_tags.player1 or "P1"
            self.headers.p2 = self.meta_tags.player2 or "P2"
        if self.meta_tags.preview is not None and self.meta_tags.preview != 0.0:
            self.headers.previewstart = self.meta_tags.preview
        if medley := self.meta_tags.medley:
            self.headers.medleystartbeat = medley.start
            self.headers.medleyendbeat = medley.end
        if self.meta_tags.tags:
            self.headers.tags = self.meta_tags.tags

    def write_to_file(self, path: Path, encoding: str, newline: str) -> None:
        with path.open(
            "w", encoding=encoding, newline=newline, errors="backslashreplace"
        ) as file:
            file.write(str(self))

    def sanitize(self, txt_options: download_options.TxtOptions | None) -> None:
        """Sanitize USDB issues and prepare for local usage."""
        self.headers.reset_file_location_headers()
        if txt_options:
            self.headers.set_version(txt_options.format_version)
            self.fix(txt_options)

    def fix(self, txt_options: download_options.TxtOptions) -> None:
        # non-optional fixes
        self.fix_relative_songs()
        self.notes.maybe_split_duet_notes()
        self.restore_missing_headers()
        self.fix_first_timestamp()
        self.fix_low_bpm()
        self.notes.fix_overlapping_and_touching_notes(self.logger)
        self.notes.fix_pitch_values(self.logger)
        self.notes.fix_apostrophes(self.logger)
        self.headers.fix_apostrophes(self.logger)
        self.notes.fix_all_caps(self.logger)
        self.headers.fix_language(self.logger)
        self.headers.fix_videogap(self.meta_tags, self.logger)
        # optional fixes
        if txt_options:
            match txt_options.fix_linebreaks:
                case FixLinebreaks.DISABLE:
                    pass
                case FixLinebreaks.USDX_STYLE:
                    self.notes.fix_linebreaks_usdx_style(self.logger)
                case FixLinebreaks.YASS_STYLE:
                    self.notes.fix_linebreaks_yass_style(self.headers.bpm, self.logger)
                case _ as unreachable:
                    assert_never(unreachable)
            if txt_options.fix_first_words_capitalization:
                self.notes.fix_first_words_capitalization(self.logger)
            if txt_options.fix_spaces != FixSpaces.DISABLE:
                self.notes.fix_spaces(txt_options.fix_spaces, self.logger)
            if txt_options.fix_quotation_marks:
                self.notes.fix_quotation_marks(
                    self.headers.main_language(), self.logger
                )

    def minimum_song_length(self) -> str:
        """Return the minimum song length based on last beat, BPM and GAP"""
        beats_secs = self.headers.bpm.beats_to_secs(self.notes.end())
        minimum_secs = round(beats_secs + self.headers.gap / 1000)
        minutes, seconds = divmod(minimum_secs, 60)

        return f"{minutes:02d}:{seconds:02d}"

    def fix_relative_songs(self) -> None:
        if not self.headers.relative:
            return

        offset = 0
        for line in self.notes.all_lines():
            for note in line.notes:
                note.start = note.start + offset

            if (line_break := line.line_break) is None:
                # must be last line, because relative timings don't support duets
                break

            line_break.previous_line_out_time = (
                line_break.previous_line_out_time + offset
            )
            if line_break.next_line_in_time is not None:
                line_break.next_line_in_time = line_break.next_line_in_time + offset
            offset = line_break.next_line_in_time or line_break.previous_line_out_time

        # remove #RELATIVE tag
        self.headers.relative = None
        self.logger.debug("FIX: Changed relative to absolute timings.")

    def fix_first_timestamp(self) -> None:
        """Shifts all notes such that the first note starts at beat zero and adjusts
        GAP accordingly
        """
        if (offset := self.notes.start()) == 0:
            # round GAP to nearest 10 ms
            self.headers.gap = int(round(self.headers.gap, -1))
            return

        for line in self.notes.all_lines():
            line.shift(-offset)

        self.headers.apply_to_medley_tags(lambda beats: beats - offset)
        offset_ms = self.headers.bpm.beats_to_ms(offset)
        self.headers.gap = int(round(self.headers.gap + offset_ms, -1))
        self.logger.debug(
            "FIX: Set first timestamp to zero and adjusted #GAP accordingly."
        )

    def fix_low_bpm(self) -> None:
        """(repeatedly) doubles BPM value and all note timings
        until the BPM is above MINIMUM_BPM"""

        if not self.headers.bpm.is_too_low():
            return

        factor = self.headers.bpm.make_large_enough()

        self.headers.apply_to_medley_tags(lambda beats: beats * factor)
        for line in self.notes.all_lines():
            line.multiply(factor)
        self.logger.debug(
            f"FIX: Increased BPM to {self.headers.bpm} (factor: {factor})"
        )
