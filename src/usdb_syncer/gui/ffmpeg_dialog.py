"""Dialog to report missing ffmpeg."""

import os
import shutil
import sys
from typing import Callable

from PySide6.QtWidgets import QDialog, QFileDialog, QWidget

from usdb_syncer import settings
from usdb_syncer.gui.forms.FfmpegDialog import Ui_Dialog
from usdb_syncer.utils import add_to_system_path


def check_ffmpeg(parent: QWidget, on_success: Callable[[], None]) -> None:
    """If ffmpeg is available, can be restored from the settings or is provided
    by the user, executes `on_sucess`.
    """
    if shutil.which("ffmpeg"):
        on_success()
        return
    if (path := settings.get_ffmpeg_dir()) and path not in os.environ["PATH"]:
        # first run; restore path from settings
        add_to_system_path(path)
        if shutil.which("ffmpeg"):
            on_success()
            return
    FfmpegDialog(parent, on_success).show()


class FfmpegDialog(Ui_Dialog, QDialog):
    """Dialog to report missing ffmpeg."""

    def __init__(self, parent: QWidget, on_success: Callable[[], None]) -> None:
        self.on_success = on_success
        super().__init__(parent=parent)
        self.setupUi(self)
        self.set_location.clicked.connect(self._set_location)

    def _set_location(self) -> None:
        if not (path := self._get_ffmpeg_dir()):
            return
        add_to_system_path(path)
        settings.set_ffmpeg_dir(path)
        self.accept()
        self.on_success()

    def _get_ffmpeg_dir(self) -> str:
        filt = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        path = QFileDialog.getOpenFileName(self, "Select ffmpeg", "", filt)[0]
        return os.path.dirname(path)
