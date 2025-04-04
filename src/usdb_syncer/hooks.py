"""Hooks that add-ons can subscribe to."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, ParamSpec

import attrs

from usdb_syncer.logger import logger

if TYPE_CHECKING:
    from usdb_syncer import usdb_song
    from usdb_syncer.gui.mw import MainWindow

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
            try:
                func(*args, **kwargs)
            except Exception as e:  # pylint: disable=broad-except
                logger.debug(e, exc_info=True)
                logger.warning(f"Plugin error in {func.__name__}: {e.__class__.__name__}")


class SongLoaderDidFinish(_Hook):
    """Called after downloading a song."""

    @classmethod
    def call(cls, song: usdb_song.UsdbSong) -> None:
        super().call(song)


class MainWindowDidLoad(_Hook):
    """Called after the main window has loaded."""

    @classmethod
    def call(cls, main_window: MainWindow) -> None:
        super().call(main_window)
