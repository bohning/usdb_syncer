"""Parsed UltraStar txt file."""

from __future__ import annotations

import math

import attrs

from usdb_syncer.logger import Log
from usdb_syncer.meta_tags.deserializer import MetaTags
from usdb_syncer.song_txt.error import NotesParseError
from usdb_syncer.song_txt.headers import Headers
from usdb_syncer.song_txt.tracks import Tracks

MINIMUM_BPM = 200.0


@attrs.define()
class SongTxt:
    """A parsed .txt file of an UltraStar song."""

    headers: Headers
    notes: Tracks
    meta_tags: MetaTags

    def __str__(self) -> str:
        return f"{self.headers}\n{self.notes}"

    @classmethod
    def parse(cls, value: str, logger: Log) -> SongTxt:
        lines = [line for line in value.splitlines() if line]
        headers = Headers.parse(lines, logger)
        meta_tags = MetaTags(headers.video or "", logger)
        notes = Tracks.parse(lines, logger)
        if lines:
            logger.warning(f"trailing text in song txt: '{lines}'")
        return cls(headers=headers, meta_tags=meta_tags, notes=notes)

    @classmethod
    def try_parse(cls, value: str, logger: Log) -> SongTxt | None:
        try:
            return cls.parse(value, logger)
        except NotesParseError:
            return None

    def maybe_split_duet_notes(self) -> None:
        if self.headers.relative and self.headers.relative.lower() == "yes":
            return
        self.notes.maybe_split_duet_notes()

    def restore_missing_headers(self) -> None:
        if self.notes.track_2:
            self.headers.p1 = self.meta_tags.player1 or "P1"
            self.headers.p2 = self.meta_tags.player2 or "P2"
        if self.meta_tags.preview is not None:
            self.headers.previewstart = self.meta_tags.preview
        if medley := self.meta_tags.medley:
            self.headers.medleystartbeat = medley.start
            self.headers.medleyendbeat = medley.end

    def write_to_file(self, path: str, encoding: str, newline: str) -> None:
        with open(path, "w", encoding=encoding, newline=newline) as file:
            file.write(str(self))

    def sanitize(self) -> None:
        """Sanitize USDB issues and prepare for local usage."""
        self.headers.reset_file_location_headers()
        self.fix()

    def fix(self) -> None:
        self.fix_relative_songs()
        self.notes.maybe_split_duet_notes()
        self.restore_missing_headers()
        self.fix_first_timestamp()
        self.fix_low_bpm()
        self.notes.fix_line_breaks()
        self.notes.fix_touching_notes()
        self.notes.fix_pitch_values()
        self.notes.fix_apostrophes()
        self.headers.fix_apostrophes()
        self.notes.fix_spaces()
        self.notes.fix_all_caps()

    def minimum_song_length(self) -> str:
        """Return the minimum song length based on last beat, BPM and GAP"""
        beats_secs = beats_to_secs(self.notes.end(), self.headers.bpm)
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

            line_break.out_time = line_break.out_time + offset
            if line_break.in_time is not None:
                line_break.in_time = line_break.in_time + offset
            offset = line_break.in_time or line_break.out_time

        # remove #RELATIVE tag
        self.headers.relative = None

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
        offset_ms = beats_to_ms(offset, self.headers.bpm)
        self.headers.gap = int(round(self.headers.gap + offset_ms, -1))

    def fix_low_bpm(self) -> None:
        """(repeatedly) doubles BPM value and all note timings
        until the BPM is above MINIMUM_BPM"""

        if self.headers.bpm >= MINIMUM_BPM:
            return

        # how often to double bpm until it is larger or equal to the threshold
        exp = math.ceil(math.log2(MINIMUM_BPM / self.headers.bpm))
        factor = 2**exp

        self.headers.bpm *= factor
        self.headers.apply_to_medley_tags(lambda beats: beats * factor)
        for line in self.notes.all_lines():
            line.multiply(factor)


def beats_to_secs(beats: int, bpm: float) -> float:
    return beats / (bpm * 4) * 60


def beats_to_ms(beats: int, bpm: float) -> float:
    return beats_to_secs(beats, bpm) * 1000
