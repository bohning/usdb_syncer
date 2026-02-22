"""Utilities for running a task in the background while showing a progress dialog."""

from __future__ import annotations

import time
import traceback
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import attrs
from PySide6 import QtCore, QtGui, QtWidgets

from usdb_syncer import db, utils
from usdb_syncer.logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable


T = TypeVar("T")
_MINIMUM_DURATION_MS = 1000


@attrs.define
class _Error:
    """Trivial wrapper for an exception."""

    error: Exception


@attrs.define
class Result(Generic[T]):  # noqa: UP046 python3.12 feature
    """The result of an operation, either a value or an error."""

    _result: T | _Error

    def result(self) -> T:
        """Check if the operation was successful.

        If the operation was successful, returns its result
        Raises the original error otherwise.
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

    _allow_close = False

    def __init__(self, label: str) -> None:
        super().__init__(parent=None, labelText=label, minimum=0, maximum=0)
        self.setCancelButton(None)
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.setWindowTitle("USDB Syncer")
        self.setMinimumDuration(_MINIMUM_DURATION_MS)
        self.setValue(0)
        self.progress = utils.ProgressProxy(label)
        self._timer = QtCore.QTimer(self, singleShot=False, interval=100)
        self._timer.timeout.connect(self._set_progress)
        self._timer.start()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        if self._allow_close:
            super().closeEvent(event)
        else:
            event.ignore()

    def reject(self) -> None:
        pass

    def _set_progress(self) -> None:
        self.setLabelText(self.progress.label)
        self.setMaximum(self.progress.maximum)
        if self.progress.maximum > 0:
            # setting value to maximum would close the dialog
            self.setValue(min(self.progress.value, self.progress.maximum - 1))

    def finish(self) -> None:
        self._timer.stop()
        self._timer.deleteLater()
        self._allow_close = True
        self.close()
        self.deleteLater()


def run_with_progress(
    label: str,
    task: Callable[[utils.ProgressProxy], T],
    on_done: Callable[[Result[T]], Any] = lambda res: res.result(),
) -> None:
    """Run a task on a background thread while a modal progress dialog is shown."""
    dialog = ProgressDialog(label)
    done = False

    def wrapped_on_done(result: Result[T]) -> None:
        nonlocal done
        done = True
        dialog.finish()
        on_done(result)

    run_background_task(dialog.progress, task, wrapped_on_done)
    start = time.time()
    while not done and (time.time() - start) * 1000 < _MINIMUM_DURATION_MS:
        # block until task is completed or dialog shows
        time.sleep(0.01)


def run_background_task(
    progress: utils.ProgressProxy,
    task: Callable[[utils.ProgressProxy], T],
    on_done: Callable[[Result[T]], Any] = lambda res: res.result(),
) -> None:
    """Run a task on a background thread."""
    signal = _ResultSignal()
    result: Result | None = None

    def wrapped_task() -> None:
        nonlocal result
        try:
            with db.managed_connection(utils.AppPaths.db):
                result = Result(task(progress))
        except Exception as exc:  # noqa: BLE001
            result = Result(_Error(exc))
        signal.result.emit()

    def wrapped_on_done() -> None:
        # prevent Qt from cleaning up the signal before it's done
        # https://bugreports.qt.io/browse/PYSIDE-2921
        signal.deleteLater()
        assert result
        on_done(result)

    signal.result.connect(wrapped_on_done)
    QtCore.QThreadPool.globalInstance().start(wrapped_task)
