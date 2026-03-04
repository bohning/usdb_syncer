"""Dialog with app settings."""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QDialog, QWidget

import usdb_syncer
from usdb_syncer.gui import gui_utils
from usdb_syncer.gui.fonts import get_version_font
from usdb_syncer.gui.forms.AboutDialog import Ui_Dialog

CREDITS_HTML = """
<body style="text-align: center; color: white; font-size: 10pt; margin-top: 2em;">

***

<p><b>Thank you</b> for using USDB Syncer!</p>

<p>Keep your karaoke song collection up to date at the click of a button.</p>

***

<p>Licensed under <a href="https://www.gnu.org/licenses/gpl-3.0.html">GPL-3.0-only</a>.<br>
Find the source code on <a href="https://github.com/bohning/usdb_syncer/">GitHub</a>.</p>

***

<p><b>More info</b><br>
<a href="https://github.com/bohning/usdb_syncer/wiki">USDB Syncer Wiki</a></p>

***

<p><b>Support</b><br>
You can support the developers by buying them some <a href="https://www.buymeacoffee.com/usdbsyncer">vegan 🍕</a>!</p>

***

<p><b>Main Programmers</b><br>
bohning<br>
RumovZ<br>
randompersona1</p>

<p><b>Contributing Programmers</b><br>
mjhalwa<br>
g3n35i5<br>
BWagener</p>

***

<p><b>Application Icon</b><br>
rawpixel.com on Freepik<br>
Website: <a href="https://www.freepik.com/free-vector/pink-neon-cloud-icon-digital-networking-system_16406257.htm">freepik.com</a></p>

<p><b>Fugue Icons</b><br>
© 2021 Yusuke Kamiyamane<br>
Website: <a href="https://p.yusukekamiyamane.com/">p.yusukekamiyamane.com</a><br>
License: <a href="http://creativecommons.org/licenses/by/3.0">CC Attribution 3.0 Unported</a></p>

***

<p><b>Copyright © 2026</b></p>

</body>
"""
RESET_GAP = 4000
SCROLL_STEP = 1
SCROLL_GAP = 100


class AboutDialog(Ui_Dialog, QDialog):
    """Dialog with about info and credits."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        gui_utils.cleanup_on_close(self)
        self.setupUi(self)
        font = get_version_font() or QFont()
        font.setPixelSize(20)
        self.label_version.setFont(font)
        self.label_version.setText(usdb_syncer.__version__[:12])
        self.credits.setHtml(CREDITS_HTML)
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
