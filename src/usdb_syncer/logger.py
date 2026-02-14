"""Helpers for logging.

Logging levels:
    CRITICAL:   The app is forced to shut down or will stop working as intended.
    ERROR:      A problem occured comprimising the outcome of an operation.
    WARNING:    A problem occured, but the app has a way to recover.
    INFO:       Something happened that is of interest to the user.
    DEBUG:      Something happened that might be relevant for diagnosis or debugging.
"""

import logging
import sys
import threading
from types import TracebackType
from typing import Any, TextIO

from usdb_syncer import SongId

LOGLEVEL = int | str


class Logger(logging.LoggerAdapter):
    """Logger wrapper with our custom logic."""

    def debug(self, msg: object, *args: object, **kwargs: Any) -> None:
        """Log a message with debug level.

        Since log messages generally are unfortunately currently
        for user communication, only debug logs contain additional context.
        """
        if not isinstance(msg, str):
            super().debug(msg, *args, **kwargs)
            return

        # Append context to the message.
        thread_name = threading.current_thread().name
        context = f" [{thread_name}]"
        super().debug(msg + context, *args, **kwargs)

    def exception(
        self,
        msg: object,
        *args: object,
        exc_info: (
            bool
            | tuple[type[BaseException], BaseException, TracebackType | None]
            | tuple[None, None, None]
            | BaseException
            | None
        ) = True,
        **kwargs: Any,
    ) -> None:
        """Log exception info with debug and message with error level."""
        print(msg, args, exc_info)
        if exc_info:
            self.debug(None, exc_info=exc_info, **kwargs)
        if msg:
            self.error(msg, *args, exc_info=False, **kwargs)


class StdoutHandler(logging.StreamHandler):
    """Logging handler that writes to stdout."""

    def __init__(
        self, stream: TextIO = sys.stdout, level: LOGLEVEL = logging.DEBUG
    ) -> None:
        super().__init__(stream)
        self.setLevel(level)


class SongLogger(Logger):
    """Logger wrapper that takes care of logging the song id."""

    def __init__(self, song_id: SongId, logger_: Any, extra: Any = ...) -> None:
        super().__init__(logger_, extra)
        self.song_id = song_id

    def process(self, msg: str, kwargs: Any) -> Any:
        return f"#{self.song_id}: {msg}", kwargs


_LOGGER_NAME = "usdb_syncer"
_raw_logger = logging.getLogger(_LOGGER_NAME)
logger = Logger(_raw_logger)
error_logger = Logger(_raw_logger.getChild("errors"))
error_logger.setLevel(logging.ERROR)


def song_logger(song_id: SongId) -> SongLogger:
    return SongLogger(song_id, logger)


_FORMATTER = logging.Formatter(
    style="{", fmt="{asctime} [{levelname}] {message}", datefmt="%Y-%m-%d %H:%M:%S"
)


def configure_logging(*handlers: logging.Handler) -> None:
    logging.basicConfig(level=logging.INFO, encoding="utf-8", handlers=handlers)
    for handler in logging.getLogger().handlers:
        handler.setFormatter(_FORMATTER)
    logger.setLevel(logging.DEBUG)


def add_root_handler(handler: logging.Handler) -> None:
    handler.setFormatter(_FORMATTER)
    logging.getLogger().addHandler(handler)
