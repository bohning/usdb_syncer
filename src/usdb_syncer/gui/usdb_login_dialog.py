"""Dialog to manage USDB login."""


from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from usdb_syncer import settings
from usdb_syncer.gui.forms.UsdbLoginDialog import Ui_Dialog
from usdb_syncer.usdb_scraper import (
    create_session,
    get_logged_in_usdb_user,
    login_to_usdb,
    log_out_of_usdb,
)


class UsdbLoginDialog(Ui_Dialog, QDialog):
    """Dialog to manage USDB login."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self._parent = parent
        self.setupUi(self)
        self.button_check_login.pressed.connect(self._on_check_login)
        self.button_log_out.pressed.connect(self._on_log_out)
        self._load_settings()

    def _load_settings(self) -> None:
        for browser in settings.Browser:
            self.combobox_browser.addItem(QIcon(browser.icon()), str(browser), browser)
        self.combobox_browser.setCurrentIndex(
            self.combobox_browser.findData(settings.get_browser())
        )
        user, password = settings.get_usdb_auth() or ("", "")
        self.line_edit_username.setText(user)
        self.line_edit_password.setText(password)

    def accept(self) -> None:
        settings.set_browser(self.combobox_browser.currentData())
        settings.set_usdb_auth(
            self.line_edit_username.text(), self.line_edit_password.text()
        )
        return super().accept()

    def _on_check_login(self) -> None:
        session = create_session(self.combobox_browser.currentData())
        if user := get_logged_in_usdb_user(session):
            message = f"Success! Existing session found with user '{user}'."
        elif (user := self.line_edit_username.text()) and (
            password := self.line_edit_password.text()
        ):
            if login_to_usdb(session, user, password):
                message = "Success! Logged in to USDB."
            else:
                message = "Login failed!"
        else:
            message = "No existing session found!"
        QMessageBox.information(self._parent, "Login Result", message)

    def _on_log_out(self) -> None:
        log_out_of_usdb(create_session(self.combobox_browser.currentData()))
