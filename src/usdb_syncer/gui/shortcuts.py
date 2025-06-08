"""Keyboard shortcut definitions and utils."""

import enum
from collections.abc import Callable

from PySide6.QtCore import QObject
from PySide6.QtGui import QKeySequence, QShortcut


class Shortcut(enum.StrEnum):
    """Helper for setting keyboard shortcuts."""

    def connect(self, parent: QObject, func: Callable[[], None]) -> None:
        QShortcut(QKeySequence(self.value), parent).activated.connect(func)


class MainWindowShortcut(Shortcut):
    """Keyboard shortcuts within the main window."""

    SELECT_FOLDER = "Ctrl+O"
    PAUSE_DOWNLOAD = "Ctrl+Shift+Return"
    OPEN_PREFERENCES = "Ctrl+,"
    OPEN_DEBUG_CONSOLE = "Ctrl+."
    GO_TO_SEARCH = "Ctrl+F"
    GO_TO_SONG_TABLE = "Ctrl+T"
    GO_TO_FILTERS = "Ctrl+S"
    GO_TO_FILTER_SEARCH = "Ctrl+Shift+F"


class SongTableShortcut(Shortcut):
    """Keyboard shortcuts usable when the song table is focused."""

    DOWNLOAD = "Ctrl+Return"
    ABORT_DOWNLOAD = "Ctrl+Alt+Return"
    TRASH_SONG = "Ctrl+D"
    PIN_SONG = "Ctrl+P"
    PLAY_SAMPLE = "Space"
    PREVIEW = "Shift+Space"
    OPEN_SONG = "Ctrl+Shift+O"


class DebugConsoleShortcut(Shortcut):
    """Keyboard shortcuts within the debug console window."""

    EXECUTE = "Ctrl+Return"
    EXECUTE_PRINT = "Ctrl+Shift+Return"
    CLEAR_OUTPUT = "Ctrl+L"
    CLEAR_INPUT = "Ctrl+Shift+L"
