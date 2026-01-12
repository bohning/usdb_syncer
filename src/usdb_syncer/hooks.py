"""Hooks that add-ons can subscribe to."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Generic, ParamSpec, TypeVar

import attrs

from usdb_syncer.logger import logger

if TYPE_CHECKING:
    from usdb_syncer import (
        usdb_song,  # noqa: F401  # I don't know why ruff is stupid here, but whatever
    )

P = ParamSpec("P")  # hook arg types
R = TypeVar("R")  # hook return type


@attrs.define(slots=False)
class _Hook(Generic[P, R]):
    """Base class for hooks."""

    _subscribers: list[Callable[P, R]]

    def __init_subclass__(cls) -> None:
        cls._subscribers = []

    @classmethod
    def subscribe(cls, func: Callable[P, R]) -> None:
        cls._subscribers.append(func)

    @classmethod
    def unsubscribe(cls, func: Callable[P, R]) -> None:
        cls._subscribers.remove(func)

    @classmethod
    def call(cls, *args: P.args, **kwargs: P.kwargs) -> Iterator[R]:
        for func in cls._subscribers:
            try:
                yield func(*args, **kwargs)
            except Exception as e:  # noqa: BLE001
                logger.exception(
                    f"Plugin error in {func.__name__}: {type(e).__name__}: {e}"
                )


class SongLoaderDidFinish(_Hook[["usdb_song.UsdbSong"], None]):
    """Called after downloading a song."""
