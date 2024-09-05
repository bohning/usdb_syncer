"""Hooks that add-ons can subscribe to."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Generic, ParamSpec

import attrs

if TYPE_CHECKING:
    from usdb_syncer import usdb_song

# pylint currently lacks support for ParamSpec
# https://github.com/pylint-dev/pylint/issues/9424
# pylint: disable=arguments-differ

P = ParamSpec("P")


@attrs.define(slots=False)
class _Hook(Generic[P]):
    """Base class for hooks."""

    _subscribers: list[Callable[P, None]]

    def __init_subclass__(cls) -> None:
        cls._subscribers = []

    @classmethod
    def subscribe(cls, func: Callable[P, None]) -> None:
        cls._subscribers.append(func)

    @classmethod
    def unsubscribe(cls, func: Callable[P, None]) -> None:
        cls._subscribers.remove(func)

    @classmethod
    def call(cls, *args: P.args, **kwargs: P.kwargs) -> None:
        for func in cls._subscribers:
            func(*args, **kwargs)


class SongLoaderDidFinish(_Hook):
    """Called after downloading a song."""

    @classmethod
    def call(cls, song: usdb_song.UsdbSong) -> None:
        super().call(song)
