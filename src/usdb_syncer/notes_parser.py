"""Parser for UltraStar txt files."""
from __future__ import annotations

import math
import re
from enum import Enum
from typing import Any, Iterator

import attrs

from usdb_syncer.logger import Log
from usdb_syncer.meta_tags.deserializer import MetaTags

MINIMUM_BPM = 200.0


class NotesParseError(Exception):
    """Raised when failing to parse notes."""


class NoteKind(Enum):
    """Type of note."""

    REGULAR = ":"
    GOLDEN = "*"
    FREESTYLE = "F"
    RAP = "R"
    GOLDEN_RAP = "G"


@attrs.define
class Note:
    """Representation of a note, parsed from a string."""

    kind: NoteKind
    start: int
    duration: int
    pitch: int
    text: str

    @classmethod
    def parse(cls, value: str) -> Note:
        regex = re.compile(r"(:|\*|F|R|G):? +(-?\d+) +(\d+) +(-?\d+)(?: (.*))?")
        if not (match := regex.fullmatch(value)):
            raise NotesParseError(f"invalid note: '{value}'")
        text = match.group(5) or ""
        try:
            kind = NoteKind(match.group(1))
            start = int(match.group(2))
            duration = int(match.group(3))
            pitch = int(match.group(4))
        except ValueError as err:
            raise NotesParseError(f"invalid note: '{value}'") from err
        if kind != NoteKind.FREESTYLE:
            if not text.strip():
                text = "~" + text
        if text.strip() == "-":
            text = text.replace("-", "~")
        return Note(kind, start, duration, pitch, text)

    def __str__(self) -> str:
        return (
            f"{self.kind.value} {self.start} {self.duration} {self.pitch} {self.text}"
        )

    def end(self) -> int:
        return self.start + self.duration

    def shorten(self, beats:int=1) -> None:
        if self.duration > beats:
            self.duration = self.duration - beats


@attrs.define
class LineBreak:
    """Line breaks consist of a single value or two values for the previous line end and
    the next line start.
    """

    start: int
    end: int | None

    @classmethod
    def parse(cls, value: str) -> tuple[LineBreak, str | None]:
        """Some line breaks aren't terminated by a line break. If this is the case, the
        rest of the line is returned.
        """
        regex = re.compile(r"- *(-?\d+) *(-?\d+)? *(.+)?")
        if not (match := regex.fullmatch(value)):
            raise NotesParseError(f"invalid line break: '{value}'")
        end = int(match.group(2)) if match.group(2) else None
        return cls(int(match.group(1)), end), match.group(3)

    def __str__(self) -> str:
        if self.end is not None:
            return f"- {self.start} {self.end}"
        return f"- {self.start}"

    def shift(self, offset: int) -> None:
        self.start = self.start + offset
        if self.end is not None:
            self.end = self.end + offset

    def multiply(self, factor: int) -> None:
        self.start = self.start * factor
        if self.end is not None:
            self.end = self.end * factor


@attrs.define
class Line:
    """Representation of a line, parsed from a list of strings."""

    notes: list[Note]
    # break to the next line; None if last line (at least for this player)
    line_break: LineBreak | None

    @classmethod
    def parse(cls, lines: list[str], logger: Log) -> Line:
        """Consumes a stream of notes until a line or document terminator is yielded."""
        notes = []
        line_break = None
        while lines:
            txt_line = lines.pop(0).lstrip()
            if txt_line.rstrip() in ("E", "P2"):
                break
            if txt_line.startswith("-"):
                try:
                    line_break, next_line = LineBreak.parse(txt_line)
                except NotesParseError as err:
                    logger.warning(str(err))
                    continue
                else:
                    if next_line:
                        lines.insert(0, next_line)
                    break
            try:
                notes.append(Note.parse(txt_line))
            except NotesParseError as err:
                logger.warning(str(err))
        else:
            logger.warning("unterminated line")
        return cls(notes, line_break)

    def is_last(self) -> bool:
        """True if this Line is the last line for any player."""
        return self.line_break is None

    def __str__(self) -> str:
        out = "\n".join(map(str, self.notes))
        if self.line_break:
            out = f"{out}\n{self.line_break}"
        return out

    def split(self) -> tuple[Line, Line] | None:
        pass

    def start(self) -> int:
        return self.notes[0].start

    def end(self) -> int:
        return self.notes[-1].end()

    def shift(self, offset: int) -> None:
        for note in self.notes:
            note.start += offset
        if self.line_break:
            self.line_break.shift(offset)

    def multiply(self, factor: int) -> None:
        for note in self.notes:
            note.start *= factor
            note.duration *= factor
        if self.line_break:
            self.line_break.multiply(factor)


@attrs.define
class Tracks:
    """All lines for players 1 and 2 if applicable."""

    track_1: list[Line]
    track_2: list[Line] | None

    @classmethod
    def parse(cls, lines: list[str], logger: Log) -> Tracks:
        track_1 = _player_lines(lines, logger)
        if not track_1:
            raise NotesParseError("no notes in file")
        track_2 = _player_lines(lines, logger) or None
        return cls(track_1, track_2)

    def __str__(self) -> str:
        body = "\n".join(map(str, self.track_1))
        if self.track_2:
            body = "\n".join(("P1", body, "P2", *map(str, self.track_2)))
        return f"{body}\nE"

    def maybe_split_duet_notes(self) -> None:
        """Try to detect a second player's notes and fix notes accordingly."""
        if self.track_2:
            return
        if not (first_line_break := self.track_1[0].line_break):
            # only one line
            return
        last_start = first_line_break.start
        for idx, line in enumerate(self.track_1):
            if not line.line_break:
                break
            if line.line_break.start < last_start:
                part_1, part_2 = _split_duet_line(line, line.line_break.start)
                self.track_2 = self.track_1[idx + 1 :]
                if part_2.notes:
                    self.track_2.insert(0, part_2)
                self.track_1 = self.track_1[:idx]
                if part_1.notes:
                    self.track_1.append(part_1)
                return
            last_start = line.line_break.start

    def start(self) -> int:
        if self.track_2:
            return min(self.track_1[0].start(), self.track_2[0].start())
        return self.track_1[0].start()

    def end(self) -> int:
        if self.track_2:
            return max(self.track_1[-1].end(), self.track_2[-1].end())
        return self.track_1[-1].end()

    def all_tracks(self) -> Iterator[list[Line]]:
        yield self.track_1
        if self.track_2:
            yield self.track_2

    def all_lines(self) -> Iterator[Line]:
        yield from self.track_1
        if self.track_2:
            yield from self.track_2

    def all_notes(self) -> Iterator[Note]:
        for line in self.all_lines():
            for note in line.notes:
                yield note

    def fix_pitch_values(self) -> None:
        min_pitch = min(note.pitch for note in self.all_notes())
        octave_shift = min_pitch // 12

        # only adjust pitches if they are at least two octaves off
        if abs(octave_shift) >= 2:
            for note in self.all_notes():
                note.pitch = note.pitch - octave_shift * 12


def _player_lines(lines: list[str], logger: Log) -> list[Line]:
    notes: list[Line] = []
    if lines and lines[0].startswith("P"):
        lines.pop(0)
    while lines:
        line = Line.parse(lines, logger)
        if line.notes:
            notes.append(line)
        if line.is_last():
            # end of file or player block
            break
    if notes:
        # ensure there is no trailing line break, e.g. because the last note was invalid
        notes[-1].line_break = None
    return notes


def _split_duet_line(line: Line, cutoff: int) -> tuple[Line, Line]:
    """Split a line into two, where the first part only contains notes _after_ some
    cutoff and the second part contains the rest. Either line may be empty.
    """
    idx = 0
    for idx, note in enumerate(line.notes):
        if note.start < cutoff:
            break
    return Line(line.notes[:idx], None), Line(line.notes[idx:], line.line_break)


@attrs.define
class Headers:
    """Ultrastar headers."""

    unknown: dict[str, str]
    title: str
    artist: str
    bpm: float = 0.0
    gap: int = 0
    language: str | None = None
    edition: str | None = None
    genre: str | None = None
    album: str | None = None
    year: str | None = None
    creator: str | None = None
    mp3: str | None = None
    cover: str | None = None
    background: str | None = None
    video: str | None = None
    videogap: float | None = None
    start: float | None = None
    end: int | None = None
    previewstart: float | None = None
    relative: str | None = None
    p1: str | None = None
    p2: str | None = None
    medleystartbeat: int | None = None
    medleyendbeat: int | None = None
    # not rewritten, as it depends on the chosen encoding
    encoding: str | None = None
    comment: str | None = None
    resolution: str | None = None

    @classmethod
    def parse(cls, lines: list[str], logger: Log) -> Headers:
        """Consumes a stream of lines while they are headers."""
        kwargs: dict[str, Any] = {"unknown": {}}
        while lines:
            if not lines[0].startswith("#"):
                break
            line = lines.pop(0).removeprefix("#")
            if not ":" in line:
                logger.warning(f"header without value: '{line}'")
                continue
            header, value = line.split(":", maxsplit=1)
            if not value:
                # ignore headers with empty values
                continue
            try:
                _set_header_value(kwargs, header, value)
            except ValueError:
                logger.warning(f"invalid header value: '{line}'")
        if "title" not in kwargs or "artist" not in kwargs:
            raise NotesParseError("cannot parse song without artist and title")
        if "bpm" not in kwargs:
            logger.warning("missing bpm")
        return cls(**kwargs)

    def reset_file_location_headers(self) -> None:
        """Clear all tags with local file locations."""
        self.mp3 = self.video = self.cover = self.background = None

    def __str__(self) -> str:
        out = "\n".join(
            f"#{key.upper()}:{val}"
            for key in (
                "title",
                "artist",
                "language",
                "edition",
                "genre",
                "year",
                "creator",
                "mp3",
                "cover",
                "background",
                "video",
                "videogap",
                "resolution",
                "start",
                "end",
                "relative",
                "previewstart",
                "medleystartbeat",
                "medleyendbeat",
                "bpm",
                "gap",
                "p1",
                "p2",
                "album",
                "comment",
            )
            if (val := getattr(self, key)) is not None
        )
        if self.unknown:
            out = "\n".join(
                (out, *(f"#{key.upper()}:{val}" for key, val in self.unknown.items()))
            )
        return out

    def artist_title_str(self) -> str:
        return f"{self.artist} - {self.title}"


def _set_header_value(kwargs: dict[str, Any], header: str, value: str) -> None:
    header = "creator" if header == "AUTHOR" else header.lower()
    if header in (
        "title",
        "artist",
        "language",
        "edition",
        "genre",
        "album",
        "year",
        "creator",
        "mp3",
        "cover",
        "background",
        "relative",
        "video",
        "p1",
        "p2",
        "encoding",
        "comment",
        "resolution",
    ):
        kwargs[header] = value
    # these are given in (fractional) seconds, thus may have a decimal comma or point
    elif header in ("bpm", "videogap", "start", "previewstart"):
        kwargs[header] = float(value.replace(",", "."))
    # these are given in milliseconds, but may have a decimal point or comma in usdb
    elif header in ("gap", "end"):
        kwargs[header] = round(float(value.replace(",", ".")))
    # these are given in beats and should thus be integers
    elif header in ("medleystartbeat", "medleyendbeat"):
        kwargs[header] = int(value)
    else:
        kwargs["unknown"][header] = value


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
        self.restore_missing_headers()
        self.fix()

    def fix(self) -> None:
        self.notes.maybe_split_duet_notes()
        self.fix_first_timestamp()
        self.fix_low_bpm()
        self.fix_line_breaks()
        self.fix_touching_notes()
        self.notes.fix_pitch_values()

    def minimum_song_length(self) -> str:
        """Return the minimum song length based on last beat, BPM and GAP"""
        beats_secs = beats_to_secs(self.notes.end(), self.headers.bpm)
        minimum_secs = beats_secs + self.headers.gap / 1000
        minutes, seconds = divmod(minimum_secs, 60)

        return f"{minutes:02.0f}:{seconds:02.0f}"

    def fix_first_timestamp(self) -> None:
        """Shifts all notes such that the first note starts at beat zero and adjusts
        GAP accordingly
        """
        if (offset := self.notes.start()) == 0:
            # round GAP to nearest 10 ms
            self.headers.gap = round(self.headers.gap / 10) * 10
            return
        for line in self.notes.all_lines():
            line.shift(-offset)
        self.headers.gap = int(
            round(self.headers.gap + beats_to_ms(offset, self.headers.bpm), -1)
        )

    def fix_low_bpm(self) -> None:
        """(repeatedly) doubles BPM value and all note timings
        until the BPM is above MINIMUM_BPM"""

        if self.headers.bpm >= MINIMUM_BPM:
            return

        # how often to multiply bpm until it is larger or equal to the threshold
        exp = math.ceil(math.log2(MINIMUM_BPM / self.headers.bpm))
        factor = 2**exp

        self.headers.bpm *= factor

        # modify medley tags
        if self.headers.medleystartbeat:
            self.headers.medleystartbeat *= factor

        if self.headers.medleyendbeat:
            self.headers.medleyendbeat *= factor

        # modify all note timings
        for line in self.notes.all_lines():
            line.multiply(factor)

    def fix_line_breaks(self) -> None:
        for track in self.notes.all_tracks():
            fix_line_breaks(track)

    def fix_touching_notes(self) -> None:
        for track in self.notes.all_tracks():
            for num_line, line in enumerate(track):
                for num_note, note in enumerate(line.notes[:-1]):
                    if note.end() == line.notes[num_note + 1].start:
                        note.shorten()
                if not line.is_last():
                    if line.end() == self.notes.track_1[num_line + 1].start:
                        line.notes[-1].shorten()


def beats_to_secs(beats: int, bpm: float) -> float:
    return beats / (bpm * 4) * 60


def beats_to_ms(beats: int, bpm: float) -> float:
    return beats_to_secs(beats, bpm) * 1000


def fix_line_breaks(lines: list[Line]) -> None:
    last_line = None
    for line in lines:
        if last_line and last_line.line_break:
            # remove end (not needed/used)
            last_line.line_break.end = None

            # similar to USDX implementation (https://github.com/UltraStar-Deluxe/USDX/blob/0974aadaa747a5ce7f1f094908e669209641b5d4/src/screens/UScreenEditSub.pas#L2976) # pylint: disable=line-too-long
            gap = line.start() - last_line.end()
            if gap < 2:
                last_line.line_break.start = line.start()
            elif gap == 2:
                last_line.line_break.start = last_line.end() + 1
            else:
                last_line.line_break.start = last_line.end() + 2

        # update last_line
        last_line = line
