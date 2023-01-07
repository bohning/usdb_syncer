"""General-purpose utilities for the GUI."""

from typing import Any, Callable

from PySide6.QtCore import QObject
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QAbstractScrollArea


def set_shortcut(key: str, parent: QObject, func: Callable[[], Any]) -> None:
    QShortcut(QKeySequence(key), parent).activated.connect(func)  # type: ignore


def scroll_to_bottom(scroll_area: QAbstractScrollArea) -> None:
    slider = scroll_area.verticalScrollBar()
    slider.setValue(slider.maximum())
