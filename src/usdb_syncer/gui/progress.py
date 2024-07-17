"""Utilities for running a task in the background while showing a progress dialog."""

from typing import Callable, TypeVar, cast

from PySide6 import QtCore, QtWidgets

T = TypeVar("T")


def run_with_progress(label: str, task: Callable[[QtWidgets.QProgressDialog], T]) -> T:
    """Runs a task on a background thread. A progress dialog is shown in the meantime
    and is exposed, so progress can be updated via `setLabel()`, `setMaximum()` and
    `setValue()`.
    If the user aborts the dialog, an exception is raised.
    """
    dialog = QtWidgets.QProgressDialog(
        labelText=label, cancelButtonText="Abort", maximum=0, minimum=0
    )
    dialog.setCancelButton(None)  # type: ignore
    dialog.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
    dialog.setWindowTitle("USDB Syncer")
    # show immediately
    dialog.setMinimumDuration(0)
    dialog.setValue(1)
    out: T | None = None
    exception: Exception | None = None
    finished = False

    def wrapped_task() -> None:
        nonlocal out, exception, finished
        try:
            out = task(dialog)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            exception = exc
        finished = True

    QtCore.QThreadPool.globalInstance().start(wrapped_task)
    while not finished:
        QtCore.QCoreApplication.processEvents()
    dialog.close()
    if exception:
        raise cast(Exception, exception)  # pylint: disable=raising-bad-type
    return cast(T, out)
