"""Dialog displaying third-party licenses."""

import os

from PySide6.QtWidgets import QDialog, QWidget

from usdb_syncer import utils
from usdb_syncer.gui import gui_utils
from usdb_syncer.gui.forms.LicensesDialog import Ui_licenses
from usdb_syncer.gui.resources.text import NOTICE


class LicensesDialog(Ui_licenses, QDialog):
    """Dialog with about info and credits."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        gui_utils.cleanup_on_close(self)
        self.setupUi(self)
        text = NOTICE.read_text(encoding="utf-8").replace(
            "$license_dir$", str(utils.AppPaths.licenses) + os.sep
        )
        self.license_textBrowser.setText(text)
