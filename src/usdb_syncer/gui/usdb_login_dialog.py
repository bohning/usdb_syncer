"""Dialog to manage USDB login."""

from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from usdb_syncer import settings
from usdb_syncer.constants import Usdb
from usdb_syncer.gui import icons
from usdb_syncer.gui.forms.UsdbLoginDialog import Ui_Dialog
from usdb_syncer.usdb_scraper import (
    SessionManager,
    get_logged_in_usdb_user,
    log_out_of_usdb,
    login_to_usdb,
    new_session_with_cookies,
)


class UsdbLoginDialog(Ui_Dialog, QDialog):
    """Dialog to manage USDB login."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self._parent = parent
        self.setupUi(self)
        self.command_link_register.pressed.connect(
            lambda: QDesktopServices.openUrl(Usdb.REGISTER_URL)
        )
        self.button_check_login.pressed.connect(self._on_check_login)
        self.button_log_out.pressed.connect(self._on_log_out)
        self._load_settings()

    def _load_settings(self) -> None:
        for browser in settings.Browser:
            if icon := icons.browser_icon(browser):
                self.combobox_browser.addItem(icon, str(browser), browser)
            else:
                self.combobox_browser.addItem(str(browser), browser)
        self.combobox_browser.setCurrentIndex(
            self.combobox_browser.findData(settings.get_browser())
        )
        user, password = settings.get_usdb_auth()
        self.line_edit_username.setText(user)
        self.line_edit_password.setText(password)

    def accept(self) -> None:
        settings.set_browser(self.combobox_browser.currentData())
        settings.set_usdb_auth(
            self.line_edit_username.text(), self.line_edit_password.text()
        )
        SessionManager.reset_session()
        super().accept()

    def _on_check_login(self) -> None:
        session = new_session_with_cookies(self.combobox_browser.currentData())
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
        log_out_of_usdb(new_session_with_cookies(self.combobox_browser.currentData()))
