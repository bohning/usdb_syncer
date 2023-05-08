"""Dialog with app settings."""

from PySide6.QtWidgets import QDialog, QWidget

from usdb_syncer.gui.forms.AboutDialog import Ui_Dialog


class AboutDialog(Ui_Dialog, QDialog):
    """Dialog with app settings."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
