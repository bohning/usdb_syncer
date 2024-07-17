"""Manages the media player singleton."""

from PySide6 import QtMultimedia


class _MediaPlayer:
    player: QtMultimedia.QMediaPlayer | None = None


def media_player() -> QtMultimedia.QMediaPlayer:
    if _MediaPlayer.player is None:
        _MediaPlayer.player = QtMultimedia.QMediaPlayer()
        _MediaPlayer.player.setAudioOutput(
            QtMultimedia.QAudioOutput(_MediaPlayer.player)
        )
    return _MediaPlayer.player
