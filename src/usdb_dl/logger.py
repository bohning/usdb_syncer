"""Helpers for logging"""

import logging
from typing import Any

from usdb_dl import SongId


class SongLogger(logging.LoggerAdapter):
    """Logger wrapper that takes care of logging the song id."""

    def __init__(self, song_id: SongId, logger: Any, extra: Any = ...) -> None:
        super().__init__(logger, extra)
        self.song_id = song_id

    def process(self, msg: str, _kwargs: Any) -> Any:
        return f"#{self.song_id}: {msg}"


def get_logger(file: str, song_id: SongId) -> SongLogger:
    logger = logging.getLogger(file)
    return SongLogger(song_id, logger)
