"""See `PathTemplate`."""

from __future__ import annotations

import enum
from pathlib import Path
from typing import TYPE_CHECKING, assert_never

import attrs

from usdb_syncer import errors

if TYPE_CHECKING:
    from usdb_syncer.usdb_song import UsdbSong

FORBIDDEN_CHARACTERS = '?"<>|*.'


class PathTemplateError(errors.UsdbSyncerError, ValueError):
    """Raised when the path template is invalid."""


@attrs.define
class InvalidCharError(PathTemplateError):
    """Raised when the path template contains a forbidden character."""

    char: str

    def __str__(self) -> str:
        return f"Invalid character in path template: '{self.char}'"


@attrs.define
class UnknownPlaceholderError(PathTemplateError):
    """Raised when the path template contains an unknown placeholder name."""

    name: str

    def __str__(self) -> str:
        return f"Unknown placeholder in path template: '{self.name}'"


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
    DEFAULT_STR = ":artist: - :title: / :artist: - :title:"

    @classmethod
    def parse(cls, template: str) -> PathTemplate:
        for char in FORBIDDEN_CHARACTERS:
            if char in template:
                raise InvalidCharError(char)
        parts = [
            p for part in template.replace("\\", "/").split("/") if (p := part.strip())
        ]
        if len(parts) < 2:
            raise NotEnoughComponentsError
        return cls([PathTemplateComponent.parse(part) for part in parts])

    def evaluate(self, song: UsdbSong) -> Path:
        return Path(*(c.evaluate(song) for c in self._components))

    @classmethod
    def default(cls) -> PathTemplate:
        return cls.parse(cls.DEFAULT_STR)

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
                if not token:
                    raise UnknownPlaceholderError("")
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

    def evaluate(self, _song: UsdbSong) -> str:
        return str(self)


class PathTemplatePlaceholder(PathTemplateComponentToken, enum.Enum):
    """The supported placeholders for path templates."""

    SONG_ID = "id"
    ARTIST = "artist"
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
            raise UnknownPlaceholderError(name) from error

    def evaluate(self, song: UsdbSong) -> str:
        match self:
            case PathTemplatePlaceholder.SONG_ID:
                return str(song.song_id)
            case PathTemplatePlaceholder.ARTIST:
                return song.artist
            case PathTemplatePlaceholder.TITLE:
                return song.title
            case PathTemplatePlaceholder.GENRE:
                return song.genre
            case PathTemplatePlaceholder.YEAR:
                return str(song.year)
            case PathTemplatePlaceholder.LANGUAGE:
                return song.language
            case PathTemplatePlaceholder.CREATOR:
                return song.creator
            case PathTemplatePlaceholder.EDITION:
                return song.edition
            case PathTemplatePlaceholder.RATING:
                return str(song.rating)
            case _ as unreachable:
                assert_never(unreachable)

    def __str__(self) -> str:
        return f":{self.value}:"
