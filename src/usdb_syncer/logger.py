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
from types import TracebackType
from typing import Any, TextIO

from usdb_syncer import SongId

LOGLEVEL = int | str


class Logger(logging.LoggerAdapter):
    """Logger wrapper with our custom logic."""

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
        if exc_info:
            self.debug(None, exc_info=exc_info, **kwargs)
        if msg:
            self.error(msg, *args, exc_info=False, **kwargs)


class StderrHandler(logging.StreamHandler):
    """Logging handler that writes to stdout."""

    def __init__(
        self, stream: TextIO = sys.stderr, level: LOGLEVEL = logging.DEBUG
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


GUI_FORMATTER = logging.Formatter(
    style="{", fmt="{asctime} [{levelname}] {message}", datefmt="%Y-%m-%d %H:%M:%S"
)
DEBUG_FORMATTER = logging.Formatter(
    style="{", fmt="{asctime} [{levelname}] [{filename}:{lineno}, {threadName}] {message}"
)


def configure_logging(*handlers: logging.Handler, formatter: logging.Formatter) -> None:
    logging.basicConfig(level=logging.INFO, encoding="utf-8", handlers=handlers)
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)
    logger.setLevel(logging.DEBUG)


def add_root_handler(handler: logging.Handler) -> None:
    logging.getLogger().addHandler(handler)
