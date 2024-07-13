import time
from pathlib import Path
from typing import Any

from ffpyplayer.player import MediaPlayer


class _Player:
    player: MediaPlayer | None = None


def _callback(selector: str, _value: Any) -> None:
    if selector == "eof":
        stop()


def play_file(path: Path, seek_secs: float = 0.0) -> None:
    if _Player.player:
        _Player.player.close_player()
    _Player.player = player = MediaPlayer(path.absolute().as_posix(), _callback)
    if seek_secs:
        # necessary to avoid crash (https://github.com/matham/ffpyplayer/issues/136)
        time.sleep(0.01)
        player.seek(seek_secs)


def play_url(url: str) -> None:
    if _Player.player:
        _Player.player.close_player()
    _Player.player = MediaPlayer(url, _callback)


def stop() -> None:
    if _Player.player:
        _Player.player.close_player()
        _Player.player = None


def is_playing() -> bool:
    return bool(_Player.player)
