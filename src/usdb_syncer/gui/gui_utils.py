"""General-purpose utilities for the GUI."""

import attrs
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractScrollArea, QApplication


@attrs.define(kw_only=True)
class Modifiers:
    """Pressed keyboard modifiers."""

    ctrl: bool
    shift: bool
    alt: bool


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
