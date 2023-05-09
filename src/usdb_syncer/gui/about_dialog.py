"""Dialog with app settings."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QWidget

from usdb_syncer.gui.forms.AboutDialog import Ui_Dialog

RESET_GAP = 4000
SCROLL_STEP = 1
SCROLL_GAP = 100


class AboutDialog(Ui_Dialog, QDialog):
    """Dialog with about info and credits."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        credits_text = ""
        credits_text += "<style>a { color: #4479D4 text-decoration: none}</style>"
        credits_text += "<center><br><br><br>"
        credits_text += "<b>Thank you</b> for using USDB Syncer!<br><br>"
        credits_text += (
            "Keep your karaoke song collection up to date at the click of a button."
        )
        credits_text += "<br><br>***<br><br>"
        credits_text += "<b>More info</b>"
        credits_text += "<br><a href='https://github.com/bohning/usdb_syncer/wiki'>USDB Syncer Wiki</a><br>"
        credits_text += "<br><br>***<br><br>"
        credits_text += "<b>Support</b>"
        credits_text += "<br>You can support the developers by buying them some <a href='https://www.buymeacoffee.com/usdbsyncer'>vegan pizza!</a><br>"
        credits_text += "<br><br>***<br><br>"
        credits_text += "<b>Main Programmers</b>"
        credits_text += "<br>bohning<br>Ultorex<br><br>"
        credits_text += "<b>Contributing Programmers</b>"
        credits_text += "<br>mjhalwa<br>g3n35i5<br>BWagener"
        credits_text += "<br><br>***<br><br>"
        credits_text += "<b>Application Icon</b>"
        credits_text += "<br>rawpixel.com on Freepik<br>"
        credits_text += "Website:"
        credits_text += ' <a href="https://www.freepik.com/free-vector/pink-neon-cloud-icon-digital-networking-system_16406257.htm">freepik.com</a><br><br>'
        credits_text += "<b>Fugue Icons</b>"
        credits_text += "<br>© 2021 Yusuke Kamiyamane<br>"
        credits_text += "Website:"
        credits_text += (
            ' <a href="https://p.yusukekamiyamane.com/">p.yusukekamiyamane.com/</a><br>'
        )
        credits_text += "License:"
        credits_text += ' <a href="http://creativecommons.org/licenses/by/3.0">CC Attribution 3.0 Unported</a>'
        credits_text += "<br><br>***<br><br>"
        credits_text += "<b>Tester</b>"
        credits_text += "<br>Rakuri"
        credits_text += "<br>Hoanzl"
        credits_text += "<br>GrüneNeun<br><br><br><br><br>"
        credits_text += "<b>Copyright © 2023</b></center>"

        self.credits.setHtml(credits_text)
        self.credits.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.credits.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._reset_text()

    def _scroll_down(self) -> None:
        scroll_bar = self.credits.verticalScrollBar()
        if scroll_bar.value() >= scroll_bar.maximum():
            QTimer.singleShot(RESET_GAP, self._reset_text)
        else:
            scroll_bar.setValue(scroll_bar.value() + SCROLL_STEP)
            QTimer.singleShot(SCROLL_GAP, self._scroll_down)

    def _reset_text(self) -> None:
        scroll_bar = self.credits.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.minimum())
        QTimer.singleShot(SCROLL_GAP, self._scroll_down)
