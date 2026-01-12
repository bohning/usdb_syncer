"""Hooks that add-ons can subscribe to."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Generic, ParamSpec, TypeVar

import attrs

from usdb_syncer.logger import logger

if TYPE_CHECKING:
    # I don't know why ruff is stupid here, but whatever
    from http.cookiejar import CookieJar  # noqa: F401

    from usdb_syncer import usdb_song  # noqa: F401

P = ParamSpec("P")  # hook arg types
R = TypeVar("R")  # hook return type


@attrs.define(slots=False)
class _Hook(Generic[P, R]):
    """Base class for hooks."""

    _subscribers: list[Callable[P, R]]

    def __init_subclass__(cls) -> None:
        cls._subscribers = []

    @classmethod
    def subscribe(cls, func: Callable[P, R]) -> bool:
        cls._subscribers.append(func)
        return True

    @classmethod
    def unsubscribe(cls, func: Callable[P, R]) -> None:
        cls._subscribers.remove(func)

    @classmethod
    def call(cls, *args: P.args, **kwargs: P.kwargs) -> Iterator[R]:
        if not cls._subscribers:
            logger.debug(f"Hook {cls.__name__} called with no subscribers.")
        for func in cls._subscribers:
            try:
                yield func(*args, **kwargs)
            except Exception as e:  # noqa: BLE001
                logger.exception(
                    f"Plugin error in {func.__name__}: {type(e).__name__}: {e}"
                )


class _SingleSubscriberHook(Generic[P, R], _Hook[P, R]):
    """Base class for hooks that only allow a single subscriber."""

    @classmethod
    def subscribe(cls, func: Callable[P, R]) -> bool:
        if len(cls._subscribers) >= 1:
            logger.exception(
                f"Hook {cls.__name__} only allows a single subscriber, "
                "but tried to add another."
            )
            return False
        super().subscribe(func)
        return True


class SongLoaderDidFinish(_Hook[["usdb_song.UsdbSong"], None]):
    """Called after downloading a song."""


class GetYtCookies(_SingleSubscriberHook[[], "CookieJar"]):
    """Called to get YouTube cookies for downloading videos."""


class GetUsdbCookies(_SingleSubscriberHook[[], "CookieJar"]):
    """Called to get USDB cookies for downloading resources."""
