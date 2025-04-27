"""Dialog with app settings."""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QWidget

import usdb_syncer
from usdb_syncer.gui.forms.AboutDialog import Ui_Dialog

RESET_GAP = 4000
SCROLL_STEP = 1
SCROLL_GAP = 100


class AboutDialog(Ui_Dialog, QDialog):
    """Dialog with about info and credits."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self.label_version.setText(usdb_syncer.__version__)
        self._reset_text()

    def _scroll_down(self) -> None:
        scroll_bar = self.credits.verticalScrollBar()
        if scroll_bar.value() >= scroll_bar.maximum():
            QTimer.singleShot(RESET_GAP, self._reset_text)
        else:
            scroll_bar.setValue(scroll_bar.value() + SCROLL_STEP)
            QTimer.singleShot(SCROLL_GAP, self._scroll_down)

    def _reset_text(self) -> None:
        scroll_bar = self.credits.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.minimum())
        QTimer.singleShot(SCROLL_GAP, self._scroll_down)
