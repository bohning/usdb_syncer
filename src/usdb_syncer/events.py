"""Signals other components can notify and subscribe to."""

from typing import Any, Callable, Self

from PySide6 import QtCore

from usdb_syncer import db


class _EventProcessor(QtCore.QObject):
    """Processes events."""

    def customEvent(self, event: QtCore.QEvent) -> None:
        if isinstance(event, _SubscriptableEvent):
            event.process()


class _SubscriptableEvent(QtCore.QEvent):
    """An event other components can send and subscribe to."""

    _subscribers: list[Callable[[Self], Any]] = []
    __processor: _EventProcessor | None = None

    def __init__(self) -> None:
        super().__init__(QtCore.QEvent.Type.User)

    def __init_subclass__(cls) -> None:
        cls._subscribers = []

    @classmethod
    def subscribe(cls, callback: Callable[[Self], Any]) -> None:
        cls._subscribers.append(callback)

    @classmethod
    def unsubscribe(cls, callback: Callable[[Self], Any]) -> None:
        cls._subscribers.remove(callback)

    def post(self) -> None:
        QtCore.QCoreApplication.postEvent(self._processor(), self)

    @classmethod
    def _processor(cls) -> _EventProcessor:
        if cls.__processor is None:
            cls.__processor = _EventProcessor()
            assert (app := QtCore.QCoreApplication.instance())
            cls.__processor.moveToThread(app.thread())
        return cls.__processor

    def process(self) -> None:
        for func in self._subscribers:
            func(self)


class TreeFilterChanged(_SubscriptableEvent):
    """Sent when a tree filter row has been selected or deselected."""

    def __init__(self, search: db.SearchBuilder) -> None:
        super().__init__()
        self.search = search


class TextFilterChanged(_SubscriptableEvent):
    """Sent when the free text search has been changed."""

    def __init__(self, search: str) -> None:
        super().__init__()
        self.search = search
