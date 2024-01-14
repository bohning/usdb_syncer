"""Controller for a progress bar to show the numbers of requested and finished
downloads.
"""

import attrs
from PySide6 import QtWidgets

from usdb_syncer import events


@attrs.define
class ProgressBar:
    """Progress bar controller."""

    _bar: QtWidgets.QProgressBar
    _label: QtWidgets.QLabel
    _running: int = 0
    _finished: int = 0

    def __attrs_post_init__(self) -> None:
        events.DownloadsRequested.subscribe(self._on_downloads_requested)
        events.DownloadFinished.subscribe(self._on_download_finished)

    def _on_downloads_requested(self, event: events.DownloadsRequested) -> None:
        if self._running == self._finished:
            self._running = 0
            self._finished = 0
        self._running += event.count
        self._update()

    def _on_download_finished(self, _event: events.DownloadFinished) -> None:
        self._finished += 1
        self._update()

    def _update(self) -> None:
        self._label.setText(f"{self._finished}/{self._running}")
        self._bar.setValue(int((self._finished + 1) / (self._running + 1) * 100))
