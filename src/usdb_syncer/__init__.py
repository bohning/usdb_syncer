"""A download manager for USDB songs."""

from __future__ import annotations


class SongId(int):
    """Bounded int representing an id on USDB.

    Use builtin str to get the canonical zero-padded five-digit str.
    """

    def __init__(self, value: int) -> None:
        if value not in range(100_000):
            raise ValueError("SongId out of range")

    def __str__(self) -> str:
        return f"{self:05}"

    @classmethod
    def parse(cls, value: str) -> SongId:
        return cls(int(value))

    @classmethod
    def try_parse(cls, value: str) -> SongId | None:
        try:
            return cls.parse(value)
        except ValueError:
            return None
