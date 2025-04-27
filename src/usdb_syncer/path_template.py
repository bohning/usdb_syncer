"""See `PathTemplate`."""

from __future__ import annotations

import enum
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, assert_never

import attrs

from usdb_syncer import errors, utils
from usdb_syncer.custom_data import CustomData

if TYPE_CHECKING:
    from usdb_syncer.usdb_song import UsdbSong

FORBIDDEN_CHARACTERS = '?"<>|*.'
UNKNOWN_PLACEHOLDER_STRING = "None"


class PathTemplateError(errors.UsdbSyncerError, ValueError):
    """Raised when the path template is invalid."""


@attrs.define
class InvalidCharError(PathTemplateError):
    """Raised when the path template contains a forbidden character."""

    char: str

    def __str__(self) -> str:
        return f"Invalid character in path template: '{self.char}'"


@attrs.define
class InvalidPlaceholderError(PathTemplateError):
    """Raised when the path template contains an unknown placeholder name."""

    name: str

    def __str__(self) -> str:
        return f"Invalid placeholder in path template: '{self.name}'"


@attrs.define
class NotEnoughComponentsError(PathTemplateError):
    """Raised when the path template contains less than two components."""

    def __str__(self) -> str:
        return "Path template must contain at least two components separated by '/'!"


@attrs.define
class PathTemplate:
    """A path with optional placeholder names, which can be resolved by passing a
    UsdbSong object. The syntax for placeholders is `:name:`.
    See `PathTemplatePlaceholder` for valid names.
    """

    _components: list[PathTemplateComponent]
    default_str = ":artist: - :title: / :artist: - :title:"

    @classmethod
    def parse(cls, template: str) -> PathTemplate:
        parts = [
            p for part in template.replace("\\", "/").split("/") if (p := part.strip())
        ]
        if len(parts) < 2:
            raise NotEnoughComponentsError
        return cls([PathTemplateComponent.parse(part) for part in parts])

    def evaluate(self, song: UsdbSong, parent: Path = Path()) -> Path:
        """Returns a valid path relative to `parent` with placeholders replaced with
        the values from `song`. The final component is the filename stem.
        """
        return Path(
            parent,
            *(utils.sanitize_filename(c.evaluate(song)) for c in self._components),
        )

    @classmethod
    def default(cls) -> PathTemplate:
        return cls.parse(cls.default_str)

    def __str__(self) -> str:
        return " / ".join(map(str, self._components))


@attrs.define
class PathTemplateComponent:
    """A component of a template path, i.e. a file or directory name supporting the
    template syntax.
    """

    _tokens: list[PathTemplateComponentToken]

    @classmethod
    def parse(cls, component: str) -> PathTemplateComponent:
        component = component.strip()
        if component.count(":") % 2 == 1:
            raise InvalidCharError(":")
        tokens: list[PathTemplateComponentToken] = []
        literal = True
        for token in component.split(":"):
            if literal:
                if token:
                    tokens.append(PathTemplateLiteral(token))
            else:
                if token[:1] == "*":
                    tokens.append(PathTemplateCustomPlaceholder(token[1:]))
                else:
                    tokens.append(PathTemplatePlaceholder.from_name(token))
            literal = not literal
        return cls(tokens)

    def evaluate(self, song: UsdbSong) -> str:
        return "".join(t.evaluate(song) for t in self._tokens)

    def __str__(self) -> str:
        return "".join(map(str, self._tokens))


class PathTemplateComponentToken:
    """Common base class for path template component tokens."""

    def evaluate(self, _song: UsdbSong) -> str:
        return NotImplemented


class PathTemplateLiteral(PathTemplateComponentToken, str):
    """A literal string that is part of a path template."""

    def __init__(self, literal: str) -> None:
        for char in FORBIDDEN_CHARACTERS:
            if char in literal:
                raise InvalidCharError(char)

    def evaluate(self, _song: UsdbSong) -> str:
        return str(self)


class PathTemplatePlaceholder(PathTemplateComponentToken, enum.Enum):
    """The supported placeholders for path templates."""

    SONG_ID = "id"
    ARTIST = "artist"
    ARTIST_INITIAL = "artist initial"
    TITLE = "title"
    GENRE = "genre"
    YEAR = "year"
    LANGUAGE = "language"
    CREATOR = "creator"
    EDITION = "edition"
    RATING = "rating"

    @classmethod
    def from_name(cls, name: str) -> PathTemplatePlaceholder:
        try:
            return PathTemplatePlaceholder(name)
        except ValueError as error:
            raise InvalidPlaceholderError(name) from error

    def evaluate(self, song: UsdbSong) -> str:  # noqa: C901
        match self:
            case PathTemplatePlaceholder.SONG_ID:
                return str(song.song_id)
            case PathTemplatePlaceholder.ARTIST:
                if song.artist and len(song.artist) > 0:
                    return song.artist
                return UNKNOWN_PLACEHOLDER_STRING
            case PathTemplatePlaceholder.ARTIST_INITIAL:
                return (
                    utils.get_first_alphanum_upper(song.artist)
                    or UNKNOWN_PLACEHOLDER_STRING
                )
            case PathTemplatePlaceholder.TITLE:
                if song.title and len(song.title) > 0:
                    return song.title
                return UNKNOWN_PLACEHOLDER_STRING
            case PathTemplatePlaceholder.YEAR:
                if song.year and song.year > 0:
                    return str(song.year)
                return UNKNOWN_PLACEHOLDER_STRING
            case PathTemplatePlaceholder.GENRE:
                return next(iter(song.genres()), UNKNOWN_PLACEHOLDER_STRING)
            case PathTemplatePlaceholder.LANGUAGE:
                return next(iter(song.languages()), UNKNOWN_PLACEHOLDER_STRING)
            case PathTemplatePlaceholder.CREATOR:
                return next(iter(song.creators()), UNKNOWN_PLACEHOLDER_STRING)
            case PathTemplatePlaceholder.EDITION:
                if song.edition and len(song.edition) > 0:
                    return song.edition
                return UNKNOWN_PLACEHOLDER_STRING
            case PathTemplatePlaceholder.RATING:
                # This is annoying because we can't differentiate between a rating of 0
                # and no rating. Would take a refactor of UsdbSong to fix.
                if song.rating:
                    return str(song.rating)
                return UNKNOWN_PLACEHOLDER_STRING
            case _ as unreachable:
                assert_never(unreachable)

    def __str__(self) -> str:
        return f":{self.value}:"


class PathTemplateCustomPlaceholder(PathTemplateComponentToken):
    """A path template placeholder representing a custom data key."""

    _key: str

    def __init__(self, key: str) -> None:
        if not CustomData.is_valid_key(key):
            raise InvalidPlaceholderError(key)
        self._key = key

    def evaluate(self, song: UsdbSong) -> str:
        if song.sync_meta:
            return song.sync_meta.custom_data.get(self._key) or ""
        return ""

    def __str__(self) -> str:
        return f":*{self._key}:"

    @classmethod
    def options(cls) -> Iterable[PathTemplateCustomPlaceholder]:
        return (cls(k) for k in CustomData.key_options())
