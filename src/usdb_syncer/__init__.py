"""A download manager for USDB songs."""

from __future__ import annotations

import base64
import binascii
import random
from pathlib import Path

from usdb_syncer.constants import Usdb


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

    def usdb_url(self) -> str:
        return f"{Usdb.BASE_URL}?link=gettxt&id={self:d}"


class SyncMetaId(int):
    """8-byte signed integer with str encoding."""

    @classmethod
    def new(cls) -> SyncMetaId:
        return cls(random.randint(-(2**63), 2**63 - 1))

    def encode(self) -> str:
        value = base64.urlsafe_b64encode(self.to_bytes(8, "big", signed=True)).decode()
        # strip padding
        return value[:-1]

    @classmethod
    def decode(cls, value: str) -> SyncMetaId | None:
        try:
            number = base64.urlsafe_b64decode(f"{value}=")
        except binascii.Error:
            return None
        return cls.from_bytes(number, "big", signed=True)

    @classmethod
    def from_path(cls, path: Path) -> SyncMetaId | None:
        return cls.decode(path.stem)
