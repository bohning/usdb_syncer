"""Signals other components can notify and subscribe to."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Self, cast

import attrs
from PySide6 import QtCore

from usdb_syncer import SongId


class _EventProcessor(QtCore.QObject):
    """Processes events."""

    def customEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802
        if isinstance(event, SubscriptableEvent):
            event.process()


class _EventProcessorManager(QtCore.QObject):
    """Singleton to manage an _EventProcessor instance."""

    _processor: _EventProcessor | None = None

    @classmethod
    def processor(cls) -> _EventProcessor:
        if cls._processor is None:
            cls._processor = _EventProcessor()
            app = QtCore.QCoreApplication.instance()
            assert app
            cls._processor.moveToThread(app.thread())
        return cls._processor


@attrs.define(slots=False)
class SubscriptableEvent(QtCore.QEvent):
    """An event other components can send and subscribe to."""

    _subscribers: list[Callable[[Self], Any]] = attrs.field(init=False)

    def __attrs_pre_init__(self) -> None:
        super().__init__(QtCore.QEvent.Type.User)

    def __init_subclass__(cls) -> None:
        cls._subscribers = []

    @classmethod
    def subscribe(cls, callback: Callable[[Self], Any]) -> None:
        # mypy seems to have a lot of trouble with the Self type
        cast(list[Callable[[Self], Any]], cls._subscribers).append(callback)

    @classmethod
    def unsubscribe(cls, callback: Callable[[Self], Any]) -> None:
        cast(list[Callable[[Self], Any]], cls._subscribers).remove(callback)

    def post(self) -> None:
        QtCore.QCoreApplication.postEvent(_EventProcessorManager.processor(), self)

    def process(self: Self) -> None:
        for func in self._subscribers:
            func(self)


# songs


@attrs.define(slots=False)
class SongChanged(SubscriptableEvent):
    """Sent when attributes of a UsdbSong have changed."""

    song_id: SongId


@attrs.define(slots=False)
class SongDeleted(SubscriptableEvent):
    """Sent when attributes of a UsdbSong have changed."""

    song_id: SongId


# downloads


@attrs.define(slots=False)
class DownloadsRequested(SubscriptableEvent):
    """Sent when a song download has been queued for download."""

    count: int


@attrs.define(slots=False)
class DownloadFinished(SubscriptableEvent):
    """Sent when a song download has finished."""

    song_id: SongId


# files


@attrs.define(slots=False)
class SongDirChanged(SubscriptableEvent):
    """Sent when the selected song directory has changed."""

    new_dir: Path
