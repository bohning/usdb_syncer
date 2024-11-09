"""Settings tests."""

from pathlib import Path
from typing import Any, Callable

import pytest
from PySide6 import QtCore, QtWidgets

from usdb_syncer import settings


def make_app() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication()
    app.setOrganizationName("bohning")
    app.setApplicationName("usdb_syncer/test")
    return app


@pytest.mark.parametrize(
    "getter,setter,value",
    [
        (settings.get_audio, settings.set_audio, False),
        (settings.get_song_dir, settings.set_song_dir, Path("/song/dir")),
        (
            settings.get_audio_bitrate,
            settings.set_audio_bitrate,
            settings.AudioBitrate.KBPS_320,
        ),
    ],
)
def test_setting_and_getting_setting(
    getter: Callable[[], Any], setter: Callable[[Any], None], value: Any
) -> None:
    try:
        app = make_app()
        setter(value)
        assert value == getter()
        # persistence method may be different between sessions
        # on Linux, only when the app is closed an INI file is used
        app.shutdown()
        app = make_app()
        assert value == getter()
    finally:
        QtCore.QSettings().clear()
        if instance := QtWidgets.QApplication.instance():
            instance.shutdown()
