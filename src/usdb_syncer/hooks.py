"""Hooks that add-ons can subscribe to."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, ParamSpec

import attrs

from usdb_syncer.logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from http.cookiejar import CookieJar  # noqa: F401

    from usdb_syncer import usdb_song  # noqa: F401

P = ParamSpec("P")


@attrs.define(slots=False)
class _Hook(Generic[P]):  # noqa: UP046 python3.12 feature
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
            except Exception as e:  # noqa: BLE001
                logger.exception(
                    f"Plugin error in {func.__name__}: {type(e).__name__}: {e}"
                )


class SongLoaderDidFinish(_Hook["usdb_song.UsdbSong"]):
    """Called after downloading a song."""


class GetYtCookies(_Hook["CookieJar"]):
    """Called to get YouTube cookies for downloading videos."""


class GetUsdbCookies(_Hook["CookieJar"]):
    """Called to get USDB cookies for downloading resources."""
