"""Debug Console with a REPL."""

import io
import traceback
from contextlib import redirect_stdout

from PySide6.QtGui import QFontDatabase, QTextCursor
from PySide6.QtWidgets import QDialog, QWidget

from usdb_syncer.gui import gui_utils
from usdb_syncer.gui.forms.DebugConsole import Ui_Dialog


class DebugConsole(Ui_Dialog, QDialog):
    """Debug Console with a REPL."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self._set_font()
        self._set_shortcuts()

    def _set_font(self) -> None:
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.input.setFont(font)
        self.output.setFont(font)

    def _set_shortcuts(self) -> None:
        gui_utils.set_shortcut("Ctrl+Return", self, self._execute)
        gui_utils.set_shortcut("Ctrl+Shift+Return", self, self._execute_and_print)
        gui_utils.set_shortcut("Ctrl+L", self, self.output.clear)
        gui_utils.set_shortcut("Ctrl+Shift+L", self, self.input.clear)

    def _execute_and_print(self) -> None:
        cursor = self.input.textCursor()
        position = cursor.position()
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        line = cursor.selectedText()
        whitespace, stripped = split_off_leading_whitespace(line)
        opening, closing = "print(", ")"
        if not stripped.startswith(opening):
            line = f"{whitespace}{opening}{stripped}{closing}"
            cursor.insertText(line)
            cursor.setPosition(position + len(opening))
            self.input.setTextCursor(cursor)
        self._execute()

    def _execute(self) -> None:
        code = self.input.toPlainText()
        with redirect_stdout(io.StringIO()) as captured:
            try:
                exec(code, {"mw": self.parent()})  # noqa: S102
            except Exception:  # noqa: BLE001
                print(traceback.format_exc())
        self._log_output(code, captured.getvalue())

    def _log_output(self, code: str, output: str) -> None:
        indented_code = ">>> " + code.strip().replace("\n", "\n... ") + "\n"
        output = output or "<no output>"
        self.output.appendPlainText(indented_code + (output or "<no output>"))
        gui_utils.scroll_to_bottom(self.output)


def split_off_leading_whitespace(text: str) -> tuple[str, str]:
    stripped = text.lstrip()
    whitespace = text[: len(text) - len(stripped)]
    return whitespace, stripped
