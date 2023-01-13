"""Notes of an parsed UltraStar txt file."""

from __future__ import annotations

import re
from enum import Enum
from typing import Iterator

import attrs

from usdb_syncer.logger import Log
from usdb_syncer.song_txt.error import NotesParseError


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

    def shorten(self, beats: int = 1) -> None:
        if self.duration > beats:
            self.duration = self.duration - beats

    def left_trim_text(self) -> None:
        """Remove whitespace from the start of the note."""
        self.text = self.text.lstrip()

    def right_trim_text_and_add_space(self) -> None:
        """Ensure the note ends with a single space."""
        self.text = self.text.rstrip() + " "


@attrs.define
class LineBreak:
    """Line breaks consist of a single value or two values for the previous line end and
    the next line start.
    """

    previous_line_out_time: int
    next_line_in_time: int | None

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
        if self.next_line_in_time is not None:
            return f"- {self.previous_line_out_time} {self.next_line_in_time}"
        return f"- {self.previous_line_out_time}"

    def shift(self, offset: int) -> None:
        self.previous_line_out_time = self.previous_line_out_time + offset
        if self.next_line_in_time is not None:
            self.next_line_in_time = self.next_line_in_time + offset

    def multiply(self, factor: int) -> None:
        self.previous_line_out_time = self.previous_line_out_time * factor
        if self.next_line_in_time is not None:
            self.next_line_in_time = self.next_line_in_time * factor


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
        last_out_time = first_line_break.previous_line_out_time
        for idx, line in enumerate(self.track_1):
            if not line.line_break:
                break
            if line.line_break.previous_line_out_time < last_out_time:
                part_1, part_2 = _split_duet_line(
                    line, line.line_break.previous_line_out_time
                )
                self.track_2 = self.track_1[idx + 1 :]
                if part_2.notes:
                    self.track_2.insert(0, part_2)
                self.track_1 = self.track_1[:idx]
                if part_1.notes:
                    self.track_1.append(part_1)
                return
            last_out_time = line.line_break.previous_line_out_time

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

    def is_all_caps(self) -> bool:
        return not any(
            char.islower() for note in self.all_notes() for char in note.text
        )

    def fix_line_breaks(self) -> None:
        for track in self.all_tracks():
            fix_line_breaks(track)

    def fix_touching_notes(self) -> None:
        for track in self.all_tracks():
            for num_line, line in enumerate(track):
                for num_note, note in enumerate(line.notes[:-1]):
                    if note.end() == line.notes[num_note + 1].start:
                        note.shorten()
                if not line.is_last():
                    if line.end() == track[num_line + 1].start():
                        line.notes[-1].shorten()

    def fix_pitch_values(self) -> None:
        min_pitch = min(note.pitch for note in self.all_notes())
        octave_shift = min_pitch // 12

        # only adjust pitches if they are at least two octaves off
        if abs(octave_shift) >= 2:
            for note in self.all_notes():
                note.pitch = note.pitch - octave_shift * 12

    def fix_apostrophes(self) -> None:
        for note in self.all_notes():
            note.text = replace_false_apostrophes_and_quotation_marks(note.text)

    def fix_spaces(self) -> None:
        """Ensures
        1. no syllables start with whitespace,
        2. word-final syllables end with a single space,
        3. the last syllable in a line ends with a single space.
        """
        for line in self.all_lines():
            line.notes[0].left_trim_text()

            # if current syllable starts with a space shift it to the end of the
            # previous syllable
            for idx in range(1, len(line.notes)):
                if line.notes[idx].text.startswith(" "):
                    line.notes[idx - 1].right_trim_text_and_add_space()
                    line.notes[idx].left_trim_text()
                if line.notes[idx].text.endswith(" "):
                    line.notes[idx].right_trim_text_and_add_space()

            # last syllable should end with a space, otherwise syllable highlighting
            # used to be incomplete in USDX, and it allows simple text concatenation
            line.notes[-1].right_trim_text_and_add_space()

    def fix_all_caps(self) -> None:
        if self.is_all_caps():
            for note in self.all_notes():
                note.text = note.text.lower()
            self.fix_first_words_capitalization()

    def fix_first_words_capitalization(self) -> None:
        for line in self.all_lines():
            # capitalize first capitalizable character
            # e.g. '"what time is it?"' -> '"What time is it?"'
            for char in line.notes[0].text:
                if char != char.upper():
                    line.notes[0].text = line.notes[0].text.replace(
                        char, char.upper(), 1
                    )
                    break


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


def fix_line_breaks(lines: list[Line]) -> None:
    last_line = None
    for line in lines:
        if last_line and last_line.line_break:
            # remove end (not needed/used)
            last_line.line_break.next_line_in_time = None

            # similar to USDX implementation (https://github.com/UltraStar-Deluxe/USDX/blob/0974aadaa747a5ce7f1f094908e669209641b5d4/src/screens/UScreenEditSub.pas#L2976) # pylint: disable=line-too-long
            gap = line.start() - last_line.end()
            if gap < 2:
                last_line.line_break.previous_line_out_time = line.start()
            elif gap == 2:
                last_line.line_break.previous_line_out_time = last_line.end() + 1
            else:
                last_line.line_break.previous_line_out_time = last_line.end() + 2

        # update last_line
        last_line = line


def replace_false_apostrophes_and_quotation_marks(value: str) -> str:
    # two single quotation marks '' by "
    # grave accent ` by upright apostrophe '
    # acute accent ´ by upright apostrophe '
    return value.replace("''", '"').replace("`", "'").replace("´", "'")
