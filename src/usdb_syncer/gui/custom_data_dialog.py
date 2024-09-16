"""Dialog for adding custom sync meta data."""

from typing import Callable

from PySide6 import QtWidgets

from usdb_syncer.gui.forms.CustomDataDialog import Ui_Dialog


class CustomDataDialog(Ui_Dialog, QtWidgets.QDialog):
    """Dialog with about info and credits."""

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        on_accept: Callable[[str, str], None],
        key: str | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self._on_accept = on_accept
        if key:
            self.edit_key.setText(key)

    def accept(self) -> None:
        if (key := self.edit_key.text()) and (value := self.edit_value.text()):
            self._on_accept(key, value)
            super().accept()
        else:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Both key and value must be supplied!"
            )
