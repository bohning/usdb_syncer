"""A download manager for USDB songs."""

from __future__ import annotations

import attrs


@attrs.frozen(auto_attribs=True)
class SongId:
    """Dataclass for an id on USDB.

    Use builtins int and str to get an integer or the canonical zero-padded five-digit
    str respectively."""

    value: int = attrs.field(validator=attrs.validators.in_(range(100_000)))

    def __str__(self) -> str:
        return f"{self.value:05}"

    @classmethod
    def parse(cls, value: str) -> SongId:
        return cls(int(value))
