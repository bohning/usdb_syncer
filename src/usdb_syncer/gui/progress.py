"""Utilities for running a task in the background while showing a progress dialog."""

from typing import Callable, TypeVar

from PySide6.QtCore import QObject, Qt, QThreadPool, Signal
from PySide6.QtWidgets import QProgressDialog


class Signals(QObject):
    """Custom signals."""

    obj = Signal(object)


T = TypeVar("T")


def run_with_progress(
    label: str,
    task: Callable[[QProgressDialog], T],
    on_done: Callable[[T], None] | None = None,
) -> None:
    """Runs a task on a background thread. A progress dialog is shown in the meantime
    and is exposed, so progress can be updated via `setLabel()`, `setMaximum()` and
    `setValue()`. Also takes a callback to be run on the main thread afterwards.
    """
    dialog = QProgressDialog(
        labelText=label, cancelButtonText="Abort", maximum=0, minimum=0
    )
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    # show immediately
    dialog.setMinimumDuration(0)
    dialog.setValue(1)
    signal = Signals()

    def wrapped_task() -> None:
        out = task(dialog)
        if not dialog.wasCanceled():
            signal.obj.emit(out)

    def wrapped_on_done(obj: T) -> None:
        dialog.accept()
        if on_done:
            on_done(obj)

    signal.obj.connect(wrapped_on_done)
    QThreadPool.globalInstance().start(wrapped_task)
