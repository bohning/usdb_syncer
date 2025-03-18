"""General-purpose utilities for the GUI."""

from collections.abc import Callable
from typing import Any

import attrs
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QAbstractScrollArea, QApplication


@attrs.define(kw_only=True)
class Modifiers:
    """Pressed keyboard modifiers."""

    ctrl: bool
    shift: bool
    alt: bool


def set_shortcut(key: str, parent: QObject, func: Callable[[], Any]) -> None:
    QShortcut(QKeySequence(key), parent).activated.connect(func)


def scroll_to_bottom(scroll_area: QAbstractScrollArea) -> None:
    slider = scroll_area.verticalScrollBar()
    slider.setValue(slider.maximum())


def keyboard_modifiers() -> Modifiers:
    mods = QApplication.keyboardModifiers()
    return Modifiers(
        ctrl=bool(mods & Qt.KeyboardModifier.ControlModifier),
        shift=bool(mods & Qt.KeyboardModifier.ShiftModifier),
        alt=bool(mods & Qt.KeyboardModifier.AltModifier),
    )
