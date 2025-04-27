"""Signals other components can notify and subscribe to."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Self, cast

import attrs
from PySide6 import QtCore

from usdb_syncer import SongId, db, settings


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


# search


@attrs.define(slots=False)
class TreeFilterChanged(SubscriptableEvent):
    """Sent when a tree filter row has been selected or deselected."""

    search: db.SearchBuilder


@attrs.define(slots=False)
class TextFilterChanged(SubscriptableEvent):
    """Sent when the free text search has been changed."""

    search: str


@attrs.define(slots=False)
class SearchOrderChanged(SubscriptableEvent):
    """Sent when the search order has been changed or reversed."""

    order: db.SongOrder
    descending: bool


@attrs.define(slots=False)
class SavedSearchRestored(SubscriptableEvent):
    """Sent when the a save search is set."""

    search: db.SearchBuilder


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


# UI


@attrs.define(slots=False)
class ThemeChanged(SubscriptableEvent):
    """Sent when a new theme has been applied."""

    theme: settings.Theme
