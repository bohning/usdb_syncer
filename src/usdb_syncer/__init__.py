"""A download manager for USDB songs."""

from __future__ import annotations

import base64
import binascii
import random
from pathlib import Path

from usdb_syncer import errors
from usdb_syncer._version import __version__ as __version__
from usdb_syncer.constants import Usdb


class SongId(int):
    """Bounded int representing an id on USDB.

    Use builtin str to get the canonical zero-padded five-digit str.
    """

    def __init__(self, value: int) -> None:
        if value not in range(100_000):
            raise errors.SongIdError(value)

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

    def usdb_gettxt_url(self) -> str:
        return f"{Usdb.GETTXT_URL}{self:d}"

    def usdb_detail_url(self) -> str:
        return f"{Usdb.DETAIL_URL}{self:d}"


class SyncMetaId(int):
    """8-byte signed integer with str encoding."""

    _len_bytes = 8
    # chars needed to base64-encode _len_bytes bytes without padding
    _len_chars = 11

    @classmethod
    def new(cls) -> SyncMetaId:
        return cls(random.randint(-(2**63), 2**63 - 1))  # noqa: S311

    def encode(self) -> str:
        value = base64.urlsafe_b64encode(
            self.to_bytes(self._len_bytes, "big", signed=True)
        ).decode()
        # strip padding
        return value[:-1]

    @classmethod
    def decode(cls, value: str) -> SyncMetaId | None:
        if len(value) != cls._len_chars:
            return None
        try:
            number = base64.urlsafe_b64decode(f"{value}=")
        except (binascii.Error, ValueError):
            return None
        if len(number) != cls._len_bytes:
            return None
        return cls.from_bytes(number, "big", signed=True)

    @classmethod
    def from_path(cls, path: Path) -> SyncMetaId | None:
        return cls.decode(path.stem)

    def to_filename(self) -> str:
        return f"{self.encode()}.usdb"
