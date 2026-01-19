"""Dialog to report missing external dependencies."""

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QDialog, QFileDialog, QWidget

from usdb_syncer import settings, utils
from usdb_syncer.gui.forms.ExternalDepsDialog import Ui_Dialog


def check_external_deps(parent: QWidget, on_success: Callable[[], Any]) -> None:
    """Check if external dependencies are available.

    If external dependencies (currently: ffmpeg, deno) are available, can be
    restored from the settings or are provided by the user, executes `on_success`.
    """
    ffmpeg_available = utils.ffmpeg_is_available()
    deno_available = utils.deno_is_available()
    if ffmpeg_available and deno_available:
        on_success()
    else:
        ExternalDepsDialog(parent, ffmpeg_available, deno_available, on_success).show()


class ExternalDepsDialog(Ui_Dialog, QDialog):
    """Dialog to report missing external dependencies."""

    def __init__(
        self,
        parent: QWidget,
        ffmpeg_available: bool,
        deno_available: bool,
        on_success: Callable[[], None],
    ) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self.ffmpeg_available = ffmpeg_available
        self.deno_available = deno_available
        self.on_success = on_success

        self.groupBox_ffmpeg.setVisible(not ffmpeg_available)
        self.groupBox_deno.setVisible(not deno_available)

        windows = sys.platform == "win32"
        macos = sys.platform == "darwin"
        linux = sys.platform in ["linux", "linux2"]
        self.label_ffmpeg_windows.setVisible(windows)
        self.label_ffmpeg_macos.setVisible(macos)
        self.label_ffmpeg_linux.setVisible(linux)
        self.label_deno_windows.setVisible(windows)
        self.label_deno_macos.setVisible(macos)
        self.label_deno_linux.setVisible(linux)

        self.adjustSize()
        self.setFixedSize(450, self.sizeHint().height())

        self.set_ffmpeg_location.clicked.connect(self._set_ffmpeg_location)
        self.set_deno_location.clicked.connect(self._set_deno_location)

    def _set_ffmpeg_location(self) -> None:
        if not (path := self._get_ffmpeg_dir()):
            return
        utils.add_to_system_path(path)
        settings.set_ffmpeg_dir(path)
        self.ffmpeg_available = True
        if self.deno_available:
            self.accept()

    def _get_ffmpeg_dir(self) -> str:
        filt = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        path = QFileDialog.getOpenFileName(self, "Select ffmpeg", "", filt)[0]
        return str(Path(path).parent)

    def _set_deno_location(self) -> None:
        if not (path := self._get_deno_dir()):
            return
        utils.add_to_system_path(path)
        settings.set_deno_dir(path)
        self.deno_available = True
        if self.ffmpeg_available:
            self.accept()

    def _get_deno_dir(self) -> str:
        filt = "deno.exe" if sys.platform == "win32" else "deno"
        path = QFileDialog.getOpenFileName(self, "Select deno", "", filt)[0]
        return str(Path(path).parent)

    def accept(self) -> None:
        if self.ffmpeg_available and self.deno_available:
            super().accept()
            self.on_success()
