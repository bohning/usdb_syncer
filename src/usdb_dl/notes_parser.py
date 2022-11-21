"""Parser for UltraStar txt files."""
import re
from enum import Enum

from usdb_dl.logger import SongLogger
from usdb_dl.meta_tags.deserializer import MetaTags


class NotesParseError(Exception):
    """Raised when failing to parse notes."""


class NoteKind(Enum):
    """Type of note."""

    REGULAR = ":"
    GOLDEN = "*"
    FREESTYLE = "F"
    RAP = "R"
    GOLDEN_RAP = "G"


class Note:
    """Representation of a note, parsed from a string."""

    kind: NoteKind
    start: int
    duration: int
    pitch: int
    text: str

    def __init__(self, value: str) -> None:
        regex = re.compile(r"(:|\*|F|R|G):? +(-?\d+) +(\d+) +(-?\d+) (.+)")
        if not (match := regex.fullmatch(value)):
            raise NotesParseError(f"invalid note: '{value}'")
        self.text = match.group(5) or ""
        try:
            self.kind = NoteKind(match.group(1))
            self.start = int(match.group(2))
            self.duration = int(match.group(3))
            self.pitch = int(match.group(4))
        except ValueError as err:
            raise NotesParseError(f"invalid note: '{value}'") from err

    def __str__(self) -> str:
        return (
            f"{self.kind.value} {self.start} {self.duration} {self.pitch} {self.text}"
        )


class Line:
    """Representation of a line, parsed from a list of strings."""

    notes: list[Note]
    # break to the next line; None if last line (at least for this player)
    line_break: int | tuple[int, int] | None = None

    def __init__(self, lines: list[str], logger: SongLogger) -> None:
        """Consumes a stream of notes until a line or document terminator is yielded."""
        self.notes = []
        while lines:
            txt_line = lines.pop(0).lstrip()
            if txt_line.rstrip() in ("E", "P2"):
                break
            if txt_line.startswith("-"):
                try:
                    self.line_break, next_line = _parse_line_break(txt_line)
                except NotesParseError as err:
                    logger.warning(str(err))
                    continue
                else:
                    if next_line:
                        lines.insert(0, next_line)
                    break
            try:
                self.notes.append(Note(txt_line))
            except NotesParseError as err:
                logger.warning(str(err))
        else:
            logger.warning("unterminated line")

    def is_last(self) -> bool:
        """True if this Line is the last line for any player."""
        return self.line_break is None

    def __str__(self) -> str:
        out = "\n".join(map(str, self.notes))
        if line_break := self._line_break_str():
            out = f"{out}\n{line_break}"
        return out

    def _line_break_str(self) -> str | None:
        if self.line_break is None:
            return None
        if isinstance(self.line_break, int):
            return f"- {self.line_break}"
        return f"- {self.line_break[0]} {self.line_break[1]}"


def _parse_line_break(value: str) -> tuple[int | tuple[int, int], str | None]:
    """Parses a line representing a line break.

    Line breaks consist of a single value or two values for the previous line end and
    the next line start. Some also aren't terminated by a line break. If this is the
    case, the rest of the line is returned.
    """
    # line breaks may contain one or two beat values ()
    regex = re.compile(r"- *(-?\d+) *(-?\d+)? *(.+)?")
    if not (match := regex.fullmatch(value)):
        raise NotesParseError(f"invalid line break: '{value}'")
    line_break: int | tuple[int, int] = (
        (int(match.group(1)), int(match.group(2)))
        if match.group(2)
        else int(match.group(1))
    )
    return line_break, match.group(3)


class PlayerNotes:
    """All lines for players 1 and 2 if applicable."""

    player_1: list[Line]
    player_2: list[Line] | None = None

    def __init__(self, lines: list[str], logger: SongLogger) -> None:
        self.player_1 = _player_lines(lines, logger)
        self.player_2 = _player_lines(lines, logger) or None

    def __str__(self) -> str:
        body = "\n".join(map(str, self.player_1))
        if self.player_2:
            body = "\n".join(("P1", body, "P2", *map(str, self.player_2)))
        return f"{body}\nE"


def _player_lines(lines: list[str], logger: SongLogger) -> list[Line]:
    notes: list[Line] = []
    if lines and lines[0].startswith("P"):
        lines.pop(0)
    while lines:
        line = Line(lines, logger)
        if line.notes:
            notes.append(line)
        if line.is_last():
            # end of file or player block
            break
    if notes:
        # ensure there is no trailing line break, e.g. because the last note was invalid
        notes[-1].line_break = None
    return notes


class Headers:
    """Ultrastar headers."""

    title: str = ""
    artist: str = ""
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
    _unknown: dict[str, str]

    def __init__(self, lines: list[str], logger: SongLogger) -> None:
        """Consumes a stream of lines while they are headers."""
        self._unknown = {}
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
                self._set_header_value(header, value)
            except ValueError:
                logger.warning(f"invalid header value: '{line}'")
        if not self.title or not self.artist:
            raise NotesParseError("cannot parse song without artist and title")
        if not self.bpm:
            logger.warning("missing bpm")

    def _set_header_value(self, header: str, value: str) -> None:
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
            setattr(self, header, value)
        elif header in ("bpm", "gap", "videogap", "start", "end", "previewstart"):
            setattr(self, header, float(value.replace(",", ".")))
        elif header in ("medleystartbeat", "medleyendbeat"):
            setattr(self, header, int(value))
        else:
            self._unknown[header] = value

    def reset_file_location_headers(self) -> None:
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
        if self._unknown:
            out = "\n".join(
                (out, *(f"#{key.upper()}:{val}" for key, val in self._unknown.items()))
            )
        return out


class SongTxt:
    """A parsed .txt file of an UltraStar song."""

    headers: Headers
    notes: PlayerNotes
    meta_tags: MetaTags

    def __init__(self, value: str, logger: SongLogger) -> None:
        lines = [line for line in value.split("\n") if line]
        self.headers = Headers(lines, logger)
        self.meta_tags = MetaTags(self.headers.video or "", logger)
        self.notes = PlayerNotes(lines, logger)
        if lines:
            logger.warning(f"trailing text in song txt: '{lines}'")

    def __str__(self) -> str:
        return f"{self.headers}\n{self.notes}"
