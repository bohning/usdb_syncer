"""Widget to display the cover of the currently selected song."""

from functools import lru_cache
from pathlib import Path

import requests
from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import QDockWidget, QLabel, QSizePolicy

from usdb_syncer import SongId, logger
from usdb_syncer.constants import Usdb
from usdb_syncer.gui import events as gui_events
from usdb_syncer.usdb_song import UsdbSong

NO_COVER_PIXMAP = QPixmap(":/images/nocover.png")


class CoverLoaderSignals(QObject):
    finished = Signal(int, QPixmap)


class ScaledCoverLabel(QLabel):
    _pixmap: QPixmap | None = None
    _current_song: UsdbSong | None = None

    def __init__(self, dock_cover: QDockWidget) -> None:
        super().__init__(dock_cover)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setMinimumSize(50, 50)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._set_cover_for_current_song)
        self._signals = CoverLoaderSignals()
        self._signals.finished.connect(self._on_cover_loaded)
        layout = dock_cover.widget().layout()
        assert layout
        layout.addWidget(self)
        dock_cover.visibilityChanged.connect(self._on_visibility_changed)
        self._visible = dock_cover.isVisible()
        gui_events.CurrentSongChanged.subscribe(self._on_current_song_changed)

    def set_cover(self, pixmap: QPixmap | None) -> None:
        self._pixmap = pixmap
        self._update_scaled_pixmap()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self) -> None:
        self.clear()
        if self._pixmap:
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(scaled)

    def _on_current_song_changed(self, event: gui_events.CurrentSongChanged) -> None:
        self._current_song = event.song
        if self._visible:
            self._timer.start()

    def _set_cover_for_current_song(self) -> None:
        self._timer.stop()
        if not (song := self._current_song):
            self.set_cover(None)
            return
        worker = CoverLoader(
            song.song_id,
            self._signals,
            song.cover_path() if song.is_local() else None,
            None if song.is_local() else f"{Usdb.COVER_URL}{song.song_id:d}.jpg",
        )
        QThreadPool.globalInstance().start(worker)

    def _on_cover_loaded(self, song_id: SongId, pixmap: QPixmap) -> None:
        if self._current_song and song_id == self._current_song.song_id:
            self.set_cover(pixmap)

    def _on_visibility_changed(self, visible: bool) -> None:
        self._visible = visible
        if visible:
            self._set_cover_for_current_song()
        else:
            self.set_cover(None)


def load_cover(local_path: Path | None, remote_url: str | None) -> QPixmap:
    if local_path and local_path.exists():
        pixmap = QPixmap(str(local_path))
        if not pixmap.isNull():
            return pixmap
    if remote_url and (remote_pixmap := fetch_remote_cover(remote_url)):
        return remote_pixmap
    return NO_COVER_PIXMAP


@lru_cache(maxsize=32)
def fetch_remote_cover(remote_url: str) -> QPixmap | None:
    try:
        logger.logger.debug(f"Fetching remote cover from {remote_url}")
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
