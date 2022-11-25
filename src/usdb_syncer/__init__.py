#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""A download manager for USDB songs."""

from typing import Optional


class SongId:
    """Dataclass for an id on USDB.

    Use builtins int and str to get an integer or the canonical zero-padded five-digit
    str respectively."""

    _value: int

    def __init__(self, value: int | str) -> None:
        self._value = int(value)
        assert 0 < self._value < 100_000

    def __int__(self) -> int:
        return self._value

    def __str__(self) -> str:
        return f"{self._value:05}"

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, SongId):
            return self._value == __o._value
        return False

    def __hash__(self) -> int:
        return hash(self._value)

    @staticmethod
    def try_from(value: str | int) -> Optional["SongId"]:
        try:
            return SongId(value)
        except (ValueError, AssertionError):
            return None
