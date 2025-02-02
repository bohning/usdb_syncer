"""See `PathTemplate`."""

from __future__ import annotations

import enum
from jinja2 import Environment, BaseLoader, TemplateError
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, assert_never, Any

import attrs

from usdb_syncer import errors, utils
from usdb_syncer.custom_data import CustomData

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
class NotEnoughComponentsError(PathTemplateError):
    """Raised when the path template contains less than two components."""
    
    def __str__(self) -> str:
        return "Path template must contain at least two components separated by '/'!"


@attrs.define
class InvalidPlaceholderError(PathTemplateError):
    """Raised when the path template contains an unknown placeholder name."""
    
    name: str

    def __str__(self) -> str:
        return f"Invalid placeholder in path template: '{self.name}'"


@attrs.define
class PathTemplate:
    """A path template that can be evaluated."""
    
    _template: str
    default_str = "{{ artist }} - {{ title }}/{{ artist }} - {{ title }}"

    @classmethod
    def parse(cls, template: str) -> PathTemplate:
        # Validate forbidden characters
        for char in FORBIDDEN_CHARACTERS:
            if char in template:
                raise InvalidCharError(char)
        
        # Split into components
        parts = [p.strip() for p in template.split("/") if p.strip()]
        if len(parts) < 2:
            raise NotEnoughComponentsError
        
        return cls(template)

    def evaluate(self, song: UsdbSong, parent: Path = Path()) -> Path:
        """Returns a valid path with placeholders replaced with values from `song`."""
        # Prepare the Jinja2 environment
        env = Environment(loader=BaseLoader())
        song_data = {
            "artist": song.artist,
            "title": song.title,
            "year": song.year,
            "genre": next(iter(song.genres()), ""),
            "language": next(iter(song.languages()), ""),
            "creator": next(iter(song.creators()), ""),
            "edition": song.edition,
            "rating": song.rating,
            "song_id": song.song_id,
        }

        try:
            template = env.from_string(self._template)
            return parent.joinpath(template.render(song_data))
        except TemplateError as e:
            raise PathTemplateError("Template evaluation failed") from e

    @classmethod
    def default(cls) -> PathTemplate:
        return cls.parse(cls.default_str)

    def __str__(self) -> str:
        return self._template


# The following would be deprecated, but is neccessary right now

class PathTemplateComponentToken:
    """Common base class for path template component tokens."""

    def evaluate(self, _song: UsdbSong) -> str:
        return NotImplemented


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
            raise InvalidPlaceholderError(name) from error

    def evaluate(self, song: UsdbSong) -> str:
        match self:
            case PathTemplatePlaceholder.SONG_ID:
                return str(song.song_id)
            case PathTemplatePlaceholder.ARTIST:
                return song.artist
            case PathTemplatePlaceholder.TITLE:
                return song.title
            case PathTemplatePlaceholder.GENRE:
                return next(iter(song.genres()), "")
            case PathTemplatePlaceholder.YEAR:
                return str(song.year)
            case PathTemplatePlaceholder.LANGUAGE:
                return next(iter(song.languages()), "")
            case PathTemplatePlaceholder.CREATOR:
                return next(iter(song.creators()), "")
            case PathTemplatePlaceholder.EDITION:
                return song.edition
            case PathTemplatePlaceholder.RATING:
                return str(song.rating)
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
