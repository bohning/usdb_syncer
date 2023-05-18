"""Headers of a parsed UltraStar txt file."""

from __future__ import annotations

import math
from typing import Any, Callable

import attrs

from usdb_syncer.constants import MINIMUM_BPM
from usdb_syncer.logger import Log
from usdb_syncer.song_txt.error import NotesParseError
from usdb_syncer.song_txt.language_translations import LANGUAGE_TRANSLATIONS
from usdb_syncer.song_txt.tracks import replace_false_apostrophes_and_quotation_marks


@attrs.define
class BeatsPerMinute:
    """New type for beats per minute float."""

    value: float = NotImplemented

    def __str__(self) -> str:
        return f"{round(self.value, 2):g}"

    @classmethod
    def parse(cls, value: str) -> BeatsPerMinute:
        return cls(float(value.replace(",", ".")))

    def beats_to_secs(self, beats: int) -> float:
        return beats / (self.value * 4) * 60

    def beats_to_ms(self, beats: int) -> float:
        return self.beats_to_secs(beats) * 1000

    def is_too_low(self) -> bool:
        return self.value < MINIMUM_BPM

    def make_large_enough(self) -> int:
        """Double BPM (if necessary, multiple times) until it is above MINIMUM_BPM
        and returns the required multiplication factor."""
        # how often to double bpm until it is larger or equal to the threshold
        exp = math.ceil(math.log2(MINIMUM_BPM / self.value))
        factor = 2**exp
        self.value = self.value * factor
        return factor


@attrs.define
class Headers:
    """Ultrastar headers."""

    unknown: dict[str, str]
    title: str
    artist: str
    bpm: BeatsPerMinute
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
        if "title" not in kwargs or "artist" not in kwargs or "bpm" not in kwargs:
            raise NotesParseError("cannot parse song without artist, title or bpm")
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

    def fix_apostrophes(self, logger: Log) -> None:
        apostrophes_and_quotation_marks_fixed = False
        for key in ("artist", "title", "language", "genre", "p1", "p2", "album"):
            if value := getattr(self, key):
                corrected_value = replace_false_apostrophes_and_quotation_marks(value)
                if value != corrected_value:
                    setattr(self, key, corrected_value)
                    apostrophes_and_quotation_marks_fixed = True
        if apostrophes_and_quotation_marks_fixed:
            logger.debug("FIX: Apostrophes in song header corrected.")

    def apply_to_medley_tags(self, func: Callable[[int], int]) -> None:
        if self.medleystartbeat:
            self.medleystartbeat = func(self.medleystartbeat)
        if self.medleyendbeat:
            self.medleyendbeat = func(self.medleyendbeat)

    def fix_language(self, logger: Log) -> None:
        if old_language := self.language:
            languages = [
                language.strip()
                for language in self.language.replace(";", ",")
                .replace("/", ",")
                .replace("|", ",")
                .split(",")
            ]
            languages = [
                LANGUAGE_TRANSLATIONS.get(language.lower(), language)
                for language in languages
            ]
            self.language = ", ".join(languages)
            if old_language != self.language:
                logger.debug(f"FIX: Language corrected to {self.language}.")

    def main_language(self) -> str:
        if self.language:
            return self.language.split(",", maxsplit=1)[0].removesuffix(" (romanized)")
        return ""


def _set_header_value(kwargs: dict[str, Any], header: str, value: str) -> None:
    header = "creator" if header == "AUTHOR" else header.lower()
    if header in (
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
    elif header == "title":
        kwargs[header] = value.removesuffix(" [DUET]")
    # these are given in (fractional) seconds, thus may have a decimal comma or point
    elif header in ("videogap", "start", "previewstart"):
        kwargs[header] = float(value.replace(",", "."))
    # these are given in milliseconds, but may have a decimal point or comma in usdb
    elif header in ("gap", "end"):
        kwargs[header] = round(float(value.replace(",", ".")))
    # these are given in beats and should thus be integers
    elif header in ("medleystartbeat", "medleyendbeat"):
        kwargs[header] = int(value)
    elif header == "bpm":
        kwargs[header] = BeatsPerMinute.parse(value)
    else:
        kwargs["unknown"][header] = value
