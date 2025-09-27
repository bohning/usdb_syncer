"""Data structure for storing user defined custom data."""

import builtins
import collections.abc
from collections import defaultdict
from typing import ClassVar

from usdb_syncer import db


class CustomData:
    """Dict of custom data."""

    _data: dict[str, str]
    _options: ClassVar[defaultdict[str, builtins.set[str]] | None] = None
    FORBIDDEN_CHARACTERS = '?"<>|*.:/\\'

    @classmethod
    def value_options(cls, key: str) -> builtins.set[str]:
        if cls._options is None:
            cls._options = db.get_custom_data_map()
        return cls._options.get(key, builtins.set())

    @classmethod
    def key_options(cls) -> collections.abc.Iterable[str]:
        if cls._options is None:
            cls._options = db.get_custom_data_map()
        return cls._options.keys()

    @classmethod
    def is_valid_key(cls, key: str) -> bool:
        return (
            bool(key)
            and key.strip() == key
            and not any(c in key for c in cls.FORBIDDEN_CHARACTERS)
        )

    def __init__(self, data: dict[str, str] | None = None) -> None:
        self._data = data.copy() if data else {}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str | None) -> None:
        if value is None:
            if key in self._data:
                del self._data[key]
        else:
            self._data[key] = value
            if self._options is not None:
                self._options[key].add(value)

    def items(self) -> collections.abc.ItemsView[str, str]:
        return self._data.items()

    def inner(self) -> dict[str, str]:
        return self._data.copy()

    def __eq__(self, value: object) -> bool:
        return isinstance(value, CustomData) and self._data == value._data

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and key in self._data
