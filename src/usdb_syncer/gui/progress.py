"""Utilities for running a task in the background while showing a progress dialog."""

import time
import traceback
from collections.abc import Callable
from typing import Any, Generic, TypeVar

import attrs
from PySide6 import QtCore, QtGui, QtWidgets

from usdb_syncer import db, utils
from usdb_syncer.logger import logger

T = TypeVar("T")
_MINIMUM_DURATION_MS = 1000


@attrs.define
class _Error:
    """Trivial wrapper for an exception."""

    error: Exception


@attrs.define
class Result(Generic[T]):
    """The result of an operation, either a value or an error."""

    _result: T | _Error

    def result(self) -> T:
        """If the operation was successful, returns its result, and raises the original
        error otherwise.
        """
        if isinstance(self._result, _Error):
            raise self._result.error
        return self._result

    def log_error(self) -> None:
        """If there was an error, log it without raising."""
        if isinstance(self._result, _Error):
            logger.error(traceback.format_exception(self._result.error))


class _ResultSignal(QtCore.QObject):
    """Signal for when the result is ready."""

    result = QtCore.Signal()


class ProgressDialog(QtWidgets.QProgressDialog):
    """Progress dialog that cannot be closed by the user."""

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        event.ignore()


def run_with_progress(
    label: str,
    task: Callable[[], T],
    on_done: Callable[[Result[T]], Any] = lambda res: res.result(),
) -> None:
    """Runs a task on a background thread while a modal progress dialog is shown."""
    dialog = ProgressDialog(parent=None, labelText=label, minimum=0, maximum=0)
    dialog.setCancelButton(None)  # type: ignore
    dialog.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
    dialog.setWindowTitle("USDB Syncer")
    dialog.setMinimumDuration(_MINIMUM_DURATION_MS)
    dialog.setValue(0)
    signal = _ResultSignal()
    result: Result | None = None

    def wrapped_task() -> None:
        nonlocal result
        try:
            with db.managed_connection(utils.AppPaths.db):
                result = Result(task())
        except Exception as exc:  # noqa: BLE001
            result = Result(_Error(exc))
        signal.result.emit()

    def wrapped_on_done() -> None:
        assert result
        dialog.deleteLater()
        on_done(result)
        # prevent Qt from cleaning up the signal before it's done
        # https://bugreports.qt.io/browse/PYSIDE-2921
        _ = signal

    signal.result.connect(wrapped_on_done)
    QtCore.QThreadPool.globalInstance().start(wrapped_task)
    start = time.time()
    while result is None and (time.time() - start) * 1000 < _MINIMUM_DURATION_MS:
        # block until task is completed or dialog shows
        time.sleep(0.01)
