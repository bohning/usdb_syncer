"""Helpers for logging.

Logging levels:
    CRITICAL:   The app is forced to shut down or will stop working as intended.
    ERROR:      A problem occured comprimising the outcome of an operation.
    WARNING:    A problem occured, but the app has a way to recover.
    INFO:       Something happened that is of interest to the user.
    DEBUG:      Something happened that might be relevant for diagnosis or debugging.
"""

import logging
from typing import Any

from usdb_syncer import SongId


class SongLogger(logging.LoggerAdapter):
    """Logger wrapper that takes care of logging the song id."""

    def __init__(self, song_id: SongId, logger_: Any, extra: Any = ...) -> None:
        super().__init__(logger_, extra)
        self.song_id = song_id

    def process(self, msg: str, kwargs: Any) -> Any:
        return f"#{self.song_id}: {msg}", kwargs


Log = logging.Logger | SongLogger
_LOGGER_NAME = "usdb_syncer"
logger = logging.getLogger(_LOGGER_NAME)
error_logger = logger.getChild("errors")
error_logger.setLevel(logging.ERROR)


def song_logger(song_id: SongId) -> Log:
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
