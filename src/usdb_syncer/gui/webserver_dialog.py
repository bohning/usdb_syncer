"""Dialog to start and stop the webserver."""

from PySide6 import QtGui, QtWidgets

from usdb_syncer import errors, settings
from usdb_syncer.gui import gui_utils, notification
from usdb_syncer.gui.forms.WebserverDialog import Ui_Dialog
from usdb_syncer.webserver import webserver


class WebserverDialog(Ui_Dialog, QtWidgets.QDialog):
    """Dialog to start and stop the webserver."""

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent=parent)
        gui_utils.cleanup_on_close(self)
        self.setupUi(self)
        self._update_ui()
        self.edit_title.setPlaceholderText(webserver.DEFAULT_TITLE)
        self._load_settings()
        self.button_start.clicked.connect(self._start)
        self.button_stop.clicked.connect(self._stop)

    def _update_ui(self) -> None:
        running = webserver.is_running()
        self.edit_title.setEnabled(not running)
        self.box_port.setEnabled(not running)
        self.checkBox_only_local_songs.setEnabled(not running)
        self.checkBox_allow_downloads.setEnabled(not running)
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
        try_to_start_webserver(
            title=self.edit_title.text(),
            port=self.box_port.value(),
            show_nonlocal_songs=not self.checkBox_only_local_songs.isChecked(),
            allow_downloading=self.checkBox_allow_downloads.isChecked(),
        )
        self._update_ui()

    def _stop(self) -> None:
        webserver.stop()
        notification.success("Webserver stopped.")
        self._update_ui()

    def _load_settings(self) -> None:
        self.edit_title.setText(settings.get_webserver_title())
        self.box_port.setValue(settings.get_webserver_port())
        self.checkBox_only_local_songs.setChecked(
            not settings.get_webserver_show_nonlocal_songs()
        )
        self.checkBox_allow_downloads.setChecked(
            settings.get_webserver_allow_downloading()
        )
        self.checkBox_auto_start.setChecked(settings.get_webserver_auto_start())

    def _save_settings(self) -> None:
        settings.set_webserver_title(self.edit_title.text())
        settings.set_webserver_port(self.box_port.value())
        settings.set_webserver_show_nonlocal_songs(
            not self.checkBox_only_local_songs.isChecked()
        )
        settings.set_webserver_allow_downloading(
            self.checkBox_allow_downloads.isChecked()
        )
        settings.set_webserver_auto_start(self.checkBox_auto_start.isChecked())

    def accept(self) -> None:
        self._save_settings()
        super().accept()

    def reject(self) -> None:
        self._save_settings()
        super().reject()


def try_to_start_webserver(
    port: int | None = None,
    title: str | None = None,
    show_nonlocal_songs: bool = False,
    allow_downloading: bool = False,
) -> None:
    try:
        webserver.start(
            port=port,
            title=title,
            show_nonlocal_songs=show_nonlocal_songs,
            allow_downloading=allow_downloading,
        )
        notification.success("Webserver started successfully.")
    except errors.WebserverError as e:
        QtWidgets.QMessageBox.warning(None, "Failed to start webserver", str(e))
