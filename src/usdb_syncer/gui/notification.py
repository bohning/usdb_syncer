"""Background notification system."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QStyle,
    QStyleOption,
    QWidget,
)

from usdb_syncer import logger
from usdb_syncer.gui import events as gui_events
from usdb_syncer.gui import main_window_instance, theme

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent, QPaintEvent

    from usdb_syncer.gui.icons import Icon


_TOAST_MARGIN = 50
_TOAST_SPACING = 10
_FADE_DURATION_MS = 300


class ToastType(Enum):
    """Type of toast."""

    INFO = QColor(0, 128, 255)
    WARNING = QColor(255, 165, 0)
    ERROR = QColor(255, 0, 0)


class Toast(QWidget):
    """A floating notification widget that fades in and out."""

    def __init__(
        self,
        message: str,
        toast_type: ToastType,
        icon: Icon | None = None,
        delay_ms: int = 3000,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.icon = icon

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

        self.setStyleSheet(
            theme.generate_toast_css(
                theme.Theme.from_settings().toast_palette(toast_type.value)
            )
        )

        if icon:
            self.icon_label = QLabel(self, pixmap=icon.icon().pixmap(16, 16))
            layout.addWidget(self.icon_label)

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

        if main_window_instance:
            main_window_instance.installEventFilter(self)
        gui_events.ThemeChanged.subscribe(self._on_theme_changed)

    def _on_theme_changed(self, event: gui_events.ThemeChanged) -> None:
        css = theme.generate_toast_css(event.theme.toast_palette())
        for toast in self.toasts:
            toast.setStyleSheet(css)
            if toast.icon:
                toast.icon_label.setPixmap(
                    toast.icon.icon(event.theme.KEY).pixmap(16, 16)
                )

    @classmethod
    def get_instance(cls) -> ToastManager:
        if cls._instance is None:
            app = QApplication.instance()
            parent = app if app else None
            cls._instance = ToastManager(parent)
        return cls._instance

    @classmethod
    def show_message(
        cls,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        icon: Icon | None = None,
        delay_ms: int = 10_000,
    ) -> None:
        """Show a toast message."""
        if not main_window_instance:
            logger.logger.warning(
                "No main window instance available to show toast: %s", message
            )
            return
        cls.get_instance()._spawn_toast(message, toast_type, icon, delay_ms)

    def _spawn_toast(
        self, message: str, toast_type: ToastType, icon: Icon | None, delay_ms: int
    ) -> None:
        toast = Toast(message, toast_type, icon, delay_ms, parent=main_window_instance)
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
        if not main_window_instance:
            raise
        return main_window_instance.mapToGlobal(
            main_window_instance.rect().bottomRight()
        )

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
        if watched == main_window_instance and event.type() in (
            QEvent.Type.Move,
            QEvent.Type.Resize,
        ):
            self._update_positions(animate=False)
        return super().eventFilter(watched, event)
