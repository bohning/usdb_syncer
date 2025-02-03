"""See `PathTemplate`."""

from __future__ import annotations

import enum
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, assert_never

import attrs
from jinja2 import BaseLoader, Environment, TemplateError

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
class TemplateRenderingError(PathTemplateError):
    """Raised when the path template contains an unknown placeholder name."""

    name: str

    def __str__(self) -> str:
        return f"Invalid template: '{self.name}'"


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
    default_str = "{{ artist }} - {{ title }} / {{ artist }} - {{ title }}"

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
    template syntax. Uses jinja2 for rendering.
    """

    _component_str: str
    _tokens: list[str] = [
        ""
    ]  # This is here for backwards compatibility with old versions of usdb_syncer.

    @classmethod
    def parse(cls, component: str) -> PathTemplateComponent:
        return cls(component)

    def evaluate(self, song: UsdbSong) -> str:
        song_data = {
            placeholder.value: placeholder.evaluate(song)
            for placeholder in PathTemplatePlaceholder
        }

        try:
            template = Environment(loader=BaseLoader()).from_string(self._component_str)
            rendered = template.render(song_data)
        except TemplateError as error:
            raise TemplateRenderingError("Invalid template.") from error

        for char in FORBIDDEN_CHARACTERS:
            if char in rendered:
                raise InvalidCharError(char)

        return rendered

    def __str__(self) -> str:
        # Return the original template string without rendering it
        return str(self._component_str)


class PathTemplatePlaceholder(enum.Enum):
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
            raise TemplateRenderingError(name) from error

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
        return f"{{{{ {self.value} }}}}"


class PathTemplateCustomPlaceholder:
    """A path template placeholder representing a custom data key."""

    _key: str

    def __init__(self, key: str) -> None:
        if not CustomData.is_valid_key(key):
            raise TemplateRenderingError(key)
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
