"""Dialog to start and stop the webserver."""

from PySide6 import QtGui, QtWidgets

from usdb_syncer import errors, webserver
from usdb_syncer.gui.forms.WebserverDialog import Ui_Dialog


class WebserverDialog(Ui_Dialog, QtWidgets.QDialog):
    """Dialog to start and stop the webserver."""

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self._update_ui()
        self.edit_title.setPlaceholderText(webserver.DEFAULT_TITLE)
        self.button_start.clicked.connect(self._start)
        self.button_stop.clicked.connect(self._stop)

    def _update_ui(self) -> None:
        running = webserver.is_running()
        self.edit_title.setEnabled(not running)
        self.box_port.setEnabled(not running)
        self.button_start.setEnabled(not running)
        self.button_stop.setEnabled(running)
        address = webserver.address()
        self.label_status.setText(
            f"The webserver is running on <a href='{address}'>{address}</a>."
            if running
            else "The webserver is not currently running."
        )
        pixmap = QtGui.QPixmap()
        if running:
            pixmap.loadFromData(webserver.get_qrcode(webserver.address()))
        self.label_qrcode.setPixmap(pixmap)

    def _start(self) -> None:
        try:
            webserver.start(title=self.edit_title.text(), port=self.box_port.value())
        except errors.WebserverError as e:
            QtWidgets.QMessageBox.warning(None, "Failed to start webserver", str(e))
        self._update_ui()

    def _stop(self) -> None:
        webserver.stop()
        self._update_ui()
