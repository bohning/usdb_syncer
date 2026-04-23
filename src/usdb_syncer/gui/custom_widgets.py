"""Custom widgets for the Syncer."""

import PySide6.QtGui
import PySide6.QtWidgets
from PySide6.QtWidgets import QGroupBox, QPushButton, QSizePolicy


class CornerButtonGroupBox(QGroupBox):
    """A QGroupBox with a button in the top right corner."""

    def __init__(self, parent: PySide6.QtWidgets.QWidget | None = None) -> None:
        """Initialize the CornerButtonGroupBox."""
        super().__init__(parent)

        self.corner_button = QPushButton("", self)
        self.corner_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.corner_button.setFixedSize(20, 20)
        # Style it so it looks like a small tab/button on the border
        # self.corner_button.setStyleSheet("""
        #    QPushButton {
        #        border: 1px solid;
        #        font-size: 9px;
        #        font-weight: bold;
        #    }
        # """)

    def resizeEvent(self, event: PySide6.QtGui.QResizeEvent) -> None:  # noqa: N802
        """Move the corner button."""
        super().resizeEvent(event)
        # Position button at top right
        # Move it slightly left (10px) and up (0px) to sit on the border
        self.corner_button.move(self.width() - self.corner_button.width() - 5, 0)
