"""Helpers for logging.

Logging levels:
    CRITICAL:   The app is forced to shut down or will stop working as intended.
    ERROR:      A problem occured comprimising the outcome of an operation.
    WARNING:    A problem occured, but the app has a way to recover.
    INFO:       Something happened that is of interest to the user.
    DEBUG:      Something happened that might be relevant for diagnosis or debugging.
"""

import logging
from types import TracebackType
from typing import Any

from usdb_syncer import SongId


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
        self.error(msg, *args, exc_info=False, **kwargs)


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


def configure_logging(*handlers: logging.Handler) -> None:
    logging.basicConfig(
        level=logging.INFO,
        style="{",
        format="{asctime} [{levelname}] {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8",
        handlers=handlers,
    )
    logger.setLevel(logging.DEBUG)
