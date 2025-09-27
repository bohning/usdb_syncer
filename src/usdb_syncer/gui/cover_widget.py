"""Widget to display the cover of the currently selected song."""

from functools import lru_cache
from pathlib import Path

import requests
from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from usdb_syncer import SongId
from usdb_syncer.constants import Usdb
from usdb_syncer.usdb_song import UsdbSong

NO_COVER_PIXMAP = QPixmap(":/images/nocover.png")


class CoverLoaderSignals(QObject):
    finished = Signal(int, QPixmap)


class ScaledCoverLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._pixmap: QPixmap | None = None
        self._signals = CoverLoaderSignals()

    def set_cover(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self._update_scaled_pixmap()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self) -> None:
        if self._pixmap:
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(scaled)

    def _update_cover(self, song: UsdbSong) -> None:
        self._current_song_id = song.song_id

        worker = CoverLoader(
            song.song_id,
            self._signals,
            song.cover_path() if song.is_local() else None,
            None if song.is_local() else f"{Usdb.COVER_URL}{song.song_id:d}.jpg",
        )
        worker.signals.finished.connect(self._set_cover)
        QThreadPool.globalInstance().start(worker)

    def _set_cover(self, song_id: int, pixmap: QPixmap) -> None:
        if song_id == self._current_song_id:
            self.set_cover(pixmap)


def load_cover(local_path: Path | None, remote_url: str | None) -> QPixmap:
    if local_path and local_path.exists():
        pixmap = QPixmap(str(local_path))
        if not pixmap.isNull():
            return pixmap
    if remote_url and (pixmap := fetch_remote_cover(remote_url)):
        return pixmap
    return NO_COVER_PIXMAP


@lru_cache(maxsize=32)
def fetch_remote_cover(remote_url: str) -> QPixmap | None:
    try:
        resp = requests.get(remote_url, timeout=10)
    except requests.RequestException:
        pass
    else:
        if resp.ok:
            pixmap = QPixmap()
            if pixmap.loadFromData(resp.content):
                return pixmap
    return None


class CoverLoader(QRunnable):
    def __init__(
        self,
        song_id: SongId,
        signals: CoverLoaderSignals,
        local_path: Path | None,
        remote_url: str | None,
    ) -> None:
        super().__init__()
        self.signals = signals
        self.song_id = song_id
        self.local_path = local_path
        self.remote_url = remote_url

    def run(self) -> None:
        pixmap = load_cover(self.local_path, self.remote_url)
        self.signals.finished.emit(self.song_id, pixmap)
