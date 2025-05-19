"""Dialog for adding custom sync meta data."""

from collections.abc import Callable

from PySide6 import QtWidgets

from usdb_syncer.custom_data import CustomData
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
        key = self.edit_key.text().strip()
        value = self.edit_value.text().strip()
        if not key or not value:
            warning = "Both key and value must be supplied!"
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Both key and value must be supplied!"
            )
        elif not CustomData.is_valid_key(key):
            warning = (
                "Key must not contain any of these characters: "
                + CustomData.FORBIDDEN_CHARACTERS
            )
        else:
            self._on_accept(key, value)
            super().accept()
            return
        QtWidgets.QMessageBox.warning(self, "Warning", warning)
