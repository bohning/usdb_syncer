"""Headers of a parsed UltraStar txt file."""

from __future__ import annotations

from typing import Any, Callable

import attrs

from usdb_syncer.logger import Log
from usdb_syncer.song_txt.error import NotesParseError
from usdb_syncer.song_txt.tracks import replace_false_apostrophes_and_quotation_marks


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

    def fix_apostrophes(self) -> None:
        for key in ("artist", "title", "language", "genre", "p1", "p2", "album"):
            if value := getattr(self, key):
                setattr(self, key, replace_false_apostrophes_and_quotation_marks(value))

    def apply_to_medley_tags(self, func: Callable[[int], int]) -> None:
        if self.medleystartbeat:
            self.medleystartbeat = func(self.medleystartbeat)
        if self.medleyendbeat:
            self.medleyendbeat = func(self.medleyendbeat)


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
