"""Signals other components can notify and subscribe to."""

from typing import Any, Callable, Generic, TypeVar

from usdb_syncer import db

T = TypeVar("T", bound=Callable)


class _Signal(Generic[T]):
    """A signal other components can notify and subscribe to."""

    _subscribers: list[T] = []

    @classmethod
    def subscribe(cls, callback: T) -> None:
        cls._subscribers.append(callback)

    @classmethod
    def unsubscribe(cls, callback: T) -> None:
        cls._subscribers.remove(callback)

    # type hints must be added in inheriting class because it is not possible to make a
    # function generic over the number of arguments
    @classmethod
    def emit(cls, *args: Any, **kwargs: Any) -> None:
        for func in cls._subscribers:
            func(*args, **kwargs)


class TreeFilterChanged(_Signal[Callable[[db.SearchBuilder], Any]]):
    """Called when a tree filter row has been selected or deselected."""

    emit: Callable[[db.SearchBuilder], None]


class TextFilterChanged(_Signal[Callable[[str], Any]]):
    """Called when the free text search has been changed."""

    emit: Callable[[str], None]
