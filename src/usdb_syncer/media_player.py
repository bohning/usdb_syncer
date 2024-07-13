import time
from pathlib import Path
from typing import Callable

import attrs
from ffpyplayer.player import MediaPlayer
from PySide6 import QtCore


@attrs.define
class Handle:
    is_playing: Callable[[], bool]
    stop: Callable[[], None]


def play_file(path: Path, seek_secs: float = 0.0) -> Handle:
    return _play(path.absolute().as_posix(), seek_secs)


def play_url(url: str) -> Handle:
    return _play(url, 0.0)


def _play(path: str, seek_secs: float = 0.0) -> Handle:
    playing = True
    stop = False

    def get_playing() -> bool:
        return playing

    def set_stop() -> None:
        nonlocal stop
        stop = True

    def task() -> None:
        nonlocal playing
        player = MediaPlayer(path)
        # necessary to avoid crash (https://github.com/matham/ffpyplayer/issues/136)
        time.sleep(0.01)
        if seek_secs:
            player.seek(seek_secs)
        duration: float | None = player.get_metadata()["duration"]
        while not stop and (
            (duration := player.get_metadata()["duration"]) is None
            or player.get_pts() < duration - 0.1
        ):
            time.sleep(0.01)
        player.close_player()
        playing = False

    QtCore.QThreadPool.globalInstance().start(task)
    return Handle(get_playing, set_stop)
