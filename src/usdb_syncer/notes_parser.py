"""Parser for UltraStar txt files."""
from __future__ import annotations

import re
from enum import Enum
from typing import Any

import attrs

from usdb_syncer.logger import Log
from usdb_syncer.meta_tags.deserializer import MetaTags


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
        regex = re.compile(r"(:|\*|F|R|G):? +(-?\d+) +(\d+) +(-?\d+) (.+)")
        if not (match := regex.fullmatch(value)):
            raise NotesParseError(f"invalid note: '{value}'")
        text = match.group(5)
        try:
            kind = NoteKind(match.group(1))
            start = int(match.group(2))
            duration = int(match.group(3))
            pitch = int(match.group(4))
        except ValueError as err:
            raise NotesParseError(f"invalid note: '{value}'") from err
        return Note(kind, start, duration, pitch, text)

    def __str__(self) -> str:
        return (
            f"{self.kind.value} {self.start} {self.duration} {self.pitch} {self.text}"
        )


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


@attrs.define
class PlayerNotes:
    """All lines for players 1 and 2 if applicable."""

    player_1: list[Line]
    player_2: list[Line] | None

    @classmethod
    def parse(cls, lines: list[str], logger: Log) -> PlayerNotes:
        player_1 = _player_lines(lines, logger)
        if not player_1:
            raise NotesParseError("no notes in file")
        player_2 = _player_lines(lines, logger) or None
        return cls(player_1, player_2)

    def __str__(self) -> str:
        body = "\n".join(map(str, self.player_1))
        if self.player_2:
            body = "\n".join(("P1", body, "P2", *map(str, self.player_2)))
        return f"{body}\nE"

    def maybe_split_duet_notes(self) -> None:
        """Try to detect a second player's notes and fix notes accordingly."""
        if self.player_2:
            return
        if not (first_line_break := self.player_1[0].line_break):
            # only one line
            return
        last_start = first_line_break.start
        for idx, line in enumerate(self.player_1):
            if not line.line_break:
                break
            if line.line_break.start < last_start:
                part_1, part_2 = _split_duet_line(line, line.line_break.start)
                self.player_2 = self.player_1[idx + 1 :]
                if part_2.notes:
                    self.player_2.insert(0, part_2)
                self.player_1 = self.player_1[:idx]
                if part_1.notes:
                    self.player_1.append(part_1)
                return
            last_start = line.line_break.start

    def get_last_beat(self) -> int:
        if self.player_2:
            return max(
                self.player_1[-1:][0].notes[-1:][0].start
                + self.player_1[-1:][0].notes[-1:][0].duration,
                self.player_2[-1:][0].notes[-1:][0].start
                + self.player_2[-1:][0].notes[-1:][0].duration,
            )
        else:
            return (
                self.player_1[-1:][0].notes[-1:][0].start
                + self.player_1[-1:][0].notes[-1:][0].duration
            )


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
    gap: float = 0.0
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
    end: float | None = None
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
                "artist",
                "title",
                "language",
                "edition",
                "year",
                "genre",
                "album",
                "creator",
                "bpm",
                "gap",
                "videogap",
                "start",
                "end",
                "previewstart",
                "medleystartbeat",
                "medleyendbeat",
                "mp3",
                "video",
                "cover",
                "background",
                "p1",
                "p2",
                "relative",
                "resolution",
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
    elif header in ("bpm", "gap", "videogap", "start", "end", "previewstart"):
        kwargs[header] = float(value.replace(",", "."))
    elif header in ("medleystartbeat", "medleyendbeat"):
        kwargs[header] = int(value)
    else:
        kwargs["unknown"][header] = value


@attrs.define()
class SongTxt:
    """A parsed .txt file of an UltraStar song."""

    headers: Headers
    notes: PlayerNotes
    meta_tags: MetaTags

    def __str__(self) -> str:
        return f"{self.headers}\n{self.notes}"

    @classmethod
    def parse(cls, value: str, logger: Log) -> SongTxt:
        lines = [line for line in value.splitlines() if line]
        headers = Headers.parse(lines, logger)
        meta_tags = MetaTags(headers.video or "", logger)
        notes = PlayerNotes.parse(lines, logger)
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
        if self.notes.player_2:
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
        """Fix USDB issues and prepare for local usage."""
        self.headers.reset_file_location_headers()
        self.notes.maybe_split_duet_notes()
        self.restore_missing_headers()

    def get_minimum_song_length(self) -> str:
        """Return the minimum song length based on last beat, BPM and GAP"""
        minutes, seconds = divmod(
            self.notes.get_last_beat() / self.headers.bpm * 15
            + self.headers.gap / 1000,
            60,
        )

        return f"{minutes:02.0f}:{seconds:02.0f}"
