"""Background notification system."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStyle,
    QStyleOption,
    QWidget,
)

from usdb_syncer.gui.resources.styles import TOAST_QSS

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent, QPaintEvent

    from usdb_syncer.gui.icons import Icon


_TOAST_MARGIN = 30
_TOAST_SPACING = 10
_FADE_DURATION_MS = 300


class Toast(QWidget):
    """A floating notification widget that fades in and out."""

    def __init__(
        self,
        message: str,
        icon: Icon | None = None,
        delay_ms: int = 3000,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        self.setStyleSheet(TOAST_QSS.read_text())

        if icon:
            icon_label = QLabel(self, pixmap=icon.icon().pixmap(16, 16))
            layout.addWidget(icon_label)

        text_label = QLabel(message, self)
        layout.addWidget(text_label)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)

        self.fade_in_anim = self._create_fade_anim(0.0, 1.0)
        self.fade_out_anim = self._create_fade_anim(1.0, 0.0)
        self.fade_out_anim.finished.connect(self.close)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(delay_ms)
        self.timer.timeout.connect(self.fade_out)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        super().paintEvent(event)

    def _create_fade_anim(self, start: float, end: float) -> QPropertyAnimation:
        anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        anim.setDuration(_FADE_DURATION_MS)
        anim.setStartValue(start)
        anim.setEndValue(end)
        return anim

    def show_toast(self) -> None:
        self.show()
        self.fade_in_anim.start()
        self.timer.start()

    def fade_out(self) -> None:
        if self.fade_out_anim.state() != QPropertyAnimation.State.Running:
            self.fade_out_anim.start()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        ToastManager.get_instance().remove_toast(self)
        super().closeEvent(event)


class ToastManager(QObject):
    """Manages Toasts."""

    _instance: ToastManager | None = None

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.toasts: list[Toast] = []
        self.slide_animations: list[QPropertyAnimation] = []

        app = QApplication.instance()
        if isinstance(app, QApplication):
            for widget in app.topLevelWidgets():
                if isinstance(widget, QMainWindow):
                    self.main_window = widget
                    widget.installEventFilter(self)
                    break

    @classmethod
    def get_instance(cls) -> ToastManager:
        if cls._instance is None:
            app = QApplication.instance()
            parent = app if app else None
            cls._instance = ToastManager(parent)
        return cls._instance

    @classmethod
    def show_message(
        cls, message: str, icon: Icon | None = None, delay_ms: int = 10_000
    ) -> None:
        """Show a toast message."""
        cls.get_instance()._spawn_toast(message, icon, delay_ms)

    def _spawn_toast(self, message: str, icon: Icon | None, delay_ms: int) -> None:
        toast = Toast(message, icon, delay_ms, parent=self.main_window)
        toast.adjustSize()

        bottom_right = self._get_bottom_right()
        target_y = bottom_right.y() - _TOAST_MARGIN

        for t in self.toasts:
            target_y -= t.height() + _TOAST_SPACING

        target_x = bottom_right.x() - toast.width() - _TOAST_MARGIN
        toast.move(QPoint(target_x, target_y - toast.height()))

        self.toasts.append(toast)
        toast.show_toast()

    def _get_bottom_right(self) -> QPoint:
        return self.main_window.mapToGlobal(self.main_window.rect().bottomRight())

    def remove_toast(self, toast: Toast) -> None:
        if toast in self.toasts:
            self.toasts.remove(toast)
            self._update_positions()

    def _update_positions(self, animate: bool = True) -> None:
        """Update positions of existing toasts to fill gaps or snap after window move.

        If animate is True, the toasts will animate to their new positions.
        If animate is False, the toasts will snap to their new positions.
        """
        for anim in self.slide_animations:
            anim.stop()
        self.slide_animations.clear()

        bottom_right = self._get_bottom_right()
        current_y = bottom_right.y() - _TOAST_MARGIN

        for toast in self.toasts:
            target_y = current_y - toast.height()
            target_pos = QPoint(
                bottom_right.x() - toast.width() - _TOAST_MARGIN, target_y
            )

            if animate and toast.pos() != target_pos:
                anim = QPropertyAnimation(toast, b"pos", self)
                anim.setDuration(200)
                anim.setStartValue(toast.pos())
                anim.setEndValue(target_pos)
                anim.start()
                self.slide_animations.append(anim)
            elif not animate:
                toast.move(target_pos)

            current_y = target_y - _TOAST_SPACING

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        """Move toasts when main window moves or resizes."""
        if watched == self.main_window and event.type() in (
            QEvent.Type.Move,
            QEvent.Type.Resize,
        ):
            self._update_positions(animate=False)
        return super().eventFilter(watched, event)
