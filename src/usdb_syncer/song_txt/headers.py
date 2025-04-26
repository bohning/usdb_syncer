"""Headers of a parsed UltraStar txt file."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import attrs

from usdb_syncer import errors
from usdb_syncer.logger import Logger
from usdb_syncer.meta_tags import MetaTags
from usdb_syncer.settings import FormatVersion
from usdb_syncer.song_txt.auxiliaries import BeatsPerMinute, replace_false_apostrophes
from usdb_syncer.song_txt.language_translations import LANGUAGE_TRANSLATIONS


@attrs.define
class Headers:
    """Ultrastar headers."""

    unknown: dict[str, str]
    title: str
    artist: str
    bpm: BeatsPerMinute
    gap: int = 0
    version: str | None = None
    language: str | None = None
    edition: str | None = None
    genre: str | None = None
    album: str | None = None
    year: str | None = None
    creator: str | None = None
    mp3: str | None = None
    audio: str | None = None
    audiourl: str | None = None
    vocals: str | None = None
    instrumental: str | None = None
    cover: str | None = None
    coverurl: str | None = None
    background: str | None = None
    backgroundurl: str | None = None
    video: str | None = None
    videourl: str | None = None
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
    tags: str | None = None

    @classmethod
    def parse(cls, lines: list[str], logger: Logger) -> Headers:
        """Consumes a stream of lines while they are headers."""
        kwargs: dict[str, Any] = {"unknown": {}}
        while lines:
            if not lines[0].startswith("#"):
                break
            line = lines.pop(0).removeprefix("#")
            if ":" not in line:
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
            raise errors.HeadersRequiredMissingError()
        return cls(**kwargs)

    def set_version(self, version: FormatVersion) -> None:
        self.version = version.value

    def reset_file_location_headers(self) -> None:
        """Clear all tags with local file locations."""
        self.mp3 = self.audio = self.vocals = self.instrumental = self.video = (
            self.cover
        ) = self.background = None

    def __str__(self) -> str:
        out = "\n".join(
            f"#{key.upper()}:{val}"
            for key in (
                "version",
                "title",
                "artist",
                "language",
                "edition",
                "genre",
                "year",
                "creator",
                "mp3",
                "audio",
                "audiourl",
                "vocals",
                "instrumental",
                "cover",
                "coverurl",
                "background",
                "backgroundurl",
                "video",
                "videourl",
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
                "tags",
            )
            if (val := getattr(self, key)) is not None
        )
        if self.unknown:
            out = "\n".join((
                out,
                *(f"#{key.upper()}:{val}" for key, val in self.unknown.items()),
            ))
        return out

    def artist_title_str(self) -> str:
        return f"{self.artist} - {self.title}"

    def fix_apostrophes(self, logger: Logger) -> None:
        apostrophes_and_quotation_marks_fixed = False
        for key in ("artist", "title", "language", "genre", "p1", "p2", "album"):
            if value := getattr(self, key):
                corrected_value = replace_false_apostrophes(value)
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

    def fix_language(self, logger: Logger) -> None:
        if not self.language:
            logger.debug("No #LANGUAGE tag found. Consider adding it.")
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

    def fix_videogap(self, meta_tags: MetaTags, logger: Logger) -> None:
        if self.videogap is not None:
            if (
                meta_tags.audio is None
                or meta_tags.video is None
                or meta_tags.audio == meta_tags.video
            ):
                logger.warning(
                    "This song contains a non-zero #VIDEOGAP, which only makes sense "
                    "if different resources for audio and video are specified, which "
                    "is not the case here. This should be fixed in USDB. Removing "
                    "#VIDEOGAP in local text file."
                )
                self.videogap = None


def _set_header_value(kwargs: dict[str, Any], header: str, value: str) -> None:
    header = "creator" if header == "AUTHOR" else header.lower()
    if header in (
        "artist",
        "version",
        "language",
        "edition",
        "genre",
        "album",
        "year",
        "creator",
        "mp3",
        "audio",
        "audiourl",
        "vocals",
        "instrumental",
        "cover",
        "coverurl",
        "background",
        "backgroundurl",
        "video",
        "videourl",
        "relative",
        "p1",
        "p2",
        "encoding",
        "comment",
        "resolution",
        "tags",
    ):
        kwargs[header] = value
    elif header == "title":
        kwargs[header] = value.removesuffix(" [DUET]")
    # these are given in (fractional) seconds, thus may have a decimal comma or point
    elif header in ("videogap", "start", "previewstart"):
        if (val := float(value.replace(",", "."))) != 0.0:
            kwargs[header] = val
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
