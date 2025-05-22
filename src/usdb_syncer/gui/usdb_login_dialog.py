"""Dialog to manage USDB login."""

from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from usdb_syncer import settings, usdb_scraper
from usdb_syncer.constants import Usdb
from usdb_syncer.gui import icons
from usdb_syncer.gui.forms.UsdbLoginDialog import Ui_Dialog


class UsdbLoginDialog(Ui_Dialog, QDialog):
    """Dialog to manage USDB login."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self.session = usdb_scraper.UsdbSession()
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
        usdb_scraper.UsdbSessionManager.reset_session()
        super().accept()

    def _on_check_login(self) -> None:
        self.session.clear_cookies()
        self.session.set_cookies(self.combobox_browser.currentData())
        if self.session.establish_login():
            message = (
                f"Success! Existing browser session found with user "
                f"'{self.session.username}'."
            )
        else:
            message = "No existing browser session found."

            if (user := self.line_edit_username.text()) and (
                password := self.line_edit_password.text()
            ):
                if self.session.manual_login(user, password):
                    message = (
                        f"Success! Logged in to USDB with user "
                        f"'{self.session.username}'."
                    )
                else:
                    message = "Login failed. Please check your credentials."

        QMessageBox.information(self._parent, "Login Result", message)

    def _on_log_out(self) -> None:
        self.session.logout()
