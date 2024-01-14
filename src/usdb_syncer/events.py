"""Signals other components can notify and subscribe to."""

from typing import Any, Callable, Self

import attrs
from PySide6 import QtCore

from usdb_syncer import SongId, db


class _EventProcessor(QtCore.QObject):
    """Processes events."""

    def customEvent(self, event: QtCore.QEvent) -> None:
        if isinstance(event, _SubscriptableEvent):
            event.process()


class _EventProcessorManager(QtCore.QObject):
    """Singleton to manage an _EventProcessor instance."""

    _processor: _EventProcessor | None = None

    @classmethod
    def processor(cls) -> _EventProcessor:
        if cls._processor is None:
            cls._processor = _EventProcessor()
            assert (app := QtCore.QCoreApplication.instance())
            cls._processor.moveToThread(app.thread())
        return cls._processor


@attrs.define(slots=False)
class _SubscriptableEvent(QtCore.QEvent):
    """An event other components can send and subscribe to."""

    _subscribers: list[Callable[[Self], Any]] = attrs.field(init=False)

    def __attrs_pre_init__(self) -> None:
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
        QtCore.QCoreApplication.postEvent(_EventProcessorManager.processor(), self)

    def process(self) -> None:
        for func in self._subscribers:
            func(self)


# search


@attrs.define(slots=False)
class TreeFilterChanged(_SubscriptableEvent):
    """Sent when a tree filter row has been selected or deselected."""

    search: db.SearchBuilder


@attrs.define(slots=False)
class TextFilterChanged(_SubscriptableEvent):
    """Sent when the free text search has been changed."""

    search: str


# songs


@attrs.define(slots=False)
class SongChanged(_SubscriptableEvent):
    """Sent when attributes of a UsdbSong have changed."""

    song_id: SongId


@attrs.define(slots=False)
class SongDeleted(_SubscriptableEvent):
    """Sent when attributes of a UsdbSong have changed."""

    song_id: SongId


# downloads


@attrs.define(slots=False)
class DownloadsRequested(_SubscriptableEvent):
    """Sent when a song download has been queued for download."""

    count: int


@attrs.define(slots=False)
class DownloadFinished(_SubscriptableEvent):
    """Sent when a song download has finished."""

    song_id: SongId
