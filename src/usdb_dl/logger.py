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

from usdb_dl import SongId


class SongLogger(logging.LoggerAdapter):
    """Logger wrapper that takes care of logging the song id."""

    def __init__(self, song_id: SongId, logger: Any, extra: Any = ...) -> None:
        super().__init__(logger, extra)
        self.song_id = song_id

    def process(self, msg: str, kwargs: Any) -> Any:
        return f"#{self.song_id}: {msg}", kwargs


def get_logger(file: str, song_id: SongId) -> SongLogger:
    logger = logging.getLogger(file)
    return SongLogger(song_id, logger)
