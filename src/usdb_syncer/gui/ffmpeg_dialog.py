"""Dialog to report missing ffmpeg."""

import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QWidget

from usdb_syncer import settings
from usdb_syncer.gui.forms.FfmpegDialog import Ui_Dialog
from usdb_syncer.utils import add_to_system_path


def check_ffmpeg(parent: QWidget, on_success: Callable[[], None]) -> None:
    """If ffmpeg is available, can be restored from the settings or is provided
    by the user, executes `on_sucess`.
    """
    if settings.ffmpeg_is_available():
        on_success()
    else:
        FfmpegDialog(parent, on_success).show()


class FfmpegDialog(Ui_Dialog, QDialog):
    """Dialog to report missing ffmpeg."""

    def __init__(self, parent: QWidget, on_success: Callable[[], None]) -> None:
        self.on_success = on_success
        super().__init__(parent=parent)
        self.setupUi(self)
        match sys.platform:
            case "win32":
                self.label_windows.setVisible(True)
                self.label_macos.setVisible(False)
                self.label_linux.setVisible(False)
                self.setFixedHeight(194)
            case "darwin":
                self.label_windows.setVisible(False)
                self.label_macos.setVisible(True)
                self.label_linux.setVisible(False)
                self.setFixedHeight(140)
            case "linux" | "linux2":
                self.label_windows.setVisible(False)
                self.label_macos.setVisible(False)
                self.label_linux.setVisible(True)
                self.setFixedHeight(140)
            case _:
                pass
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
        return str(Path(path).parent)
