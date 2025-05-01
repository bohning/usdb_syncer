"""Dialog to preview a downloaded song."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import attrs
import cffi
import numpy as np
import sounddevice as sd
from PySide6 import QtCore, QtGui, QtWidgets

from usdb_syncer import events, settings, utils
from usdb_syncer.gui import icons, theme
from usdb_syncer.gui.forms.PreviewDialog import Ui_Dialog
from usdb_syncer.logger import song_logger
from usdb_syncer.song_txt import SongTxt, tracks
from usdb_syncer.song_txt.auxiliaries import BeatsPerMinute
from usdb_syncer.usdb_song import UsdbSong

_SAMPLE_RATE = 44100
_CHANNELS = 2
_FPS = 60
_REFRESH_RATE_MS = 1000 // _FPS
_NEEDLE_WIDTH = 2
_DOUBLECLICK_DELAY_SECS = 0.3
_STREAM_BUFFER_SIZE = 2048


def load_preview_dialog(parent: QtWidgets.QWidget, song: UsdbSong) -> None:
    if not (txt_path := song.txt_path()) or not (audio_path := song.audio_path()):
        QtWidgets.QMessageBox.warning(
            parent, "Aborted", "Song must have txt and audio files!"
        )
        return
    logger = song_logger(song.song_id)
    if not (txt := SongTxt.try_from_file(txt_path, logger)):
        QtWidgets.QMessageBox.warning(parent, "Aborted", "Txt file is invalid!")
        return
    PreviewDialog(parent, txt, audio_path).show()


class PreviewDialog(Ui_Dialog, QtWidgets.QDialog):
    """Dialog to preview a downloaded song."""

    def __init__(self, parent: QtWidgets.QWidget, txt: SongTxt, audio: Path) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self.setWindowTitle(txt.headers.artist_title_str())
        self._state = _PlayState.new(txt, audio)
        self._line_view = _LineView(self._state)
        self._song_view = _SongView(self._state)
        self.layout_main.insertWidget(0, self._line_view)
        self.layout_main.insertWidget(0, self._song_view)
        self.player = _AudioPlayer.new(audio, self._update_time)
        self.button_pause.toggled.connect(lambda t: self.player.set_pause(t))
        self.button_backward.pressed.connect(
            lambda: self.player.seek_to(self._state.previous_start())
        )
        self.button_forward.pressed.connect(
            lambda: None
            if (s := self._state.next_start()) is None
            else self.player.seek_to(s)
        )
        self._on_theme_changed(settings.get_theme())
        events.ThemeChanged.subscribe(lambda e: self._on_theme_changed(e.theme))

    def _update_time(self, secs: float) -> None:
        self._state.set_current_time(secs)
        self._song_view.update()
        self._line_view.update()

    def _on_theme_changed(self, theme: settings.Theme) -> None:
        self.button_pause.setIcon(icons.Icon.PAUSE_REMOTE.icon(theme))
        self.button_backward.setIcon(icons.Icon.SKIP_BACKWARD.icon(theme))
        self.button_forward.setIcon(icons.Icon.SKIP_FORWARD.icon(theme))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.player.stop()
        event.accept()


@attrs.define
class _PlayState:
    """State of the current playback."""

    txt: SongTxt
    lines: list[_LineTimings]
    current_idx: int
    current_line: _LineTimings
    current_time: float
    current_rel_pos: float
    song_secs: float

    @classmethod
    def new(cls, txt: SongTxt, audio: Path) -> _PlayState:
        song_secs = utils.get_media_duration(audio)
        lines = [
            _LineTimings.new(line, txt.headers.gap, txt.headers.bpm, song_secs)
            for line in txt.notes.track_1
        ]
        return cls(
            txt=txt,
            lines=lines,
            current_idx=0,
            current_line=lines[0],
            current_time=lines[0].start,
            current_rel_pos=0.0,
            song_secs=song_secs,
        )

    def set_current_time(self, secs: float) -> None:
        self.current_time = secs
        self.current_rel_pos = secs / self.song_secs
        self.current_idx, self.current_line = next(
            (i, li)
            for i, li in enumerate(self.lines)
            if li.line_break is None or li.line_break > secs
        )

    def previous_start(self) -> float:
        if (
            self.current_idx > 0
            and self.current_time - _DOUBLECLICK_DELAY_SECS < self.current_line.start
        ):
            return self.lines[self.current_idx - 1].start
        return self.current_line.start

    def next_start(self) -> float | None:
        if self.current_idx + 1 >= len(self.lines):
            return None
        return self.lines[self.current_idx + 1].start


@attrs.define
class _LineTimings:
    """Wrapper for a line with absolute timings in seconds."""

    line: tracks.Line
    start: float
    end: float
    duration: float
    line_break: float | None
    rel_start: float
    rel_end: float
    rel_duration: float

    @classmethod
    def new(
        cls, line: tracks.Line, gap: int, bpm: BeatsPerMinute, song_duration: float
    ) -> _LineTimings:
        start = gap / 1000 + bpm.beats_to_secs(line.start())
        end = gap / 1000 + bpm.beats_to_secs(line.end())
        duration = end - start
        if line.line_break:
            line_break = gap / 1000 + bpm.beats_to_secs(
                line.line_break.previous_line_out_time
            )
        else:
            line_break = None
        return cls(
            line=line,
            start=start,
            end=end,
            duration=duration,
            rel_start=start / song_duration,
            rel_end=end / song_duration,
            rel_duration=duration / song_duration,
            line_break=line_break,
        )


class _SongView(QtWidgets.QWidget):
    def __init__(self, state: _PlayState):
        super().__init__()
        self._state = state

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        height = self.height()
        width = self.width()
        with QtGui.QPainter(self) as painter:
            painter.setBrush(QtGui.QColor(100, 150, 255))
            for line in self._state.lines:
                x = round(line.rel_start * width)
                w = round(line.rel_duration * width)
                painter.drawRect(x, 0, w, height)

            painter.setPen(
                QtGui.QPen(theme.current_palette().highlight(), _NEEDLE_WIDTH)
            )
            x_pos = round(self._state.current_rel_pos * width)
            x_pos = min(x_pos, width - _NEEDLE_WIDTH)
            painter.drawLine(x_pos, 0, x_pos, height)


class _LineView(QtWidgets.QWidget):
    def __init__(self, state: _PlayState):
        super().__init__()
        self._state = state
        self.setMinimumSize(800, 200)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        height = self.height()
        width = self.width()
        with QtGui.QPainter(self) as painter:
            line = self._state.current_line.line

            rel_start = line.start()
            rel_end = line.end()
            rel_len = rel_end - rel_start
            max_pitch = max(n.pitch for n in line.notes)
            min_pitch = min(n.pitch for n in line.notes)
            pitch_spread = max_pitch - min_pitch + 1
            bar_height = round(height / pitch_spread)
            painter.setBrush(QtGui.QColor(100, 150, 255))
            for note in line.notes:
                x = round((note.start - rel_start) / rel_len * width)
                w = round(note.duration / rel_len * width)
                y = round((note.pitch - min_pitch) / pitch_spread * height)
                painter.drawRect(x, y, w, bar_height)

            # Draw playback position
            painter.setPen(
                QtGui.QPen(theme.current_palette().highlight(), _NEEDLE_WIDTH)
            )
            x_pos = round(
                (self._state.current_time - self._state.current_line.start)
                / self._state.current_line.duration
                * width
            )
            x_pos = min(max(x_pos, 0), width - _NEEDLE_WIDTH)
            painter.drawLine(x_pos, 0, x_pos, height)


@attrs.define
class _AudioPlayer:
    source: Path
    callback: Callable[[float], None]
    timer: QtCore.QTimer
    start_secs: float = 0.0

    samples_played: int = 0
    paused: bool = False
    stream: sd.OutputStream | None = None
    process: subprocess.Popen | None = None
    buffer_size: int = 2048

    @classmethod
    def new(
        cls, source: Path, callback: Callable[[float], None], start_secs: float = 0.0
    ) -> _AudioPlayer:
        player = cls(
            source=source,
            callback=callback,
            timer=QtCore.QTimer(),
            start_secs=start_secs,
        )
        player.timer.timeout.connect(player.tick)
        player.start_ffmpeg()
        player.start_stream()
        return player

    def start_ffmpeg(self) -> None:
        self.process = subprocess.Popen(
            [
                "ffmpeg",
                "-i",
                self.source,
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(_SAMPLE_RATE),
                "-ac",
                str(_CHANNELS),
                "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def start_stream(self) -> None:
        self.stream = sd.OutputStream(
            samplerate=_SAMPLE_RATE,
            channels=_CHANNELS,
            dtype="int16",
            blocksize=_STREAM_BUFFER_SIZE,
            callback=self._stream_callback,
        )
        self.stream.start()
        self.timer.start(_REFRESH_RATE_MS)

    def _stream_callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time: "cffi.FFI.CData",
        status: sd.CallbackFlags,
    ) -> None:
        if self.paused or not self.process or not self.process.stdout:
            outdata[:] = np.zeros((frames, _CHANNELS), dtype=np.int16)
            return

        bytes_needed = frames * _CHANNELS * 2
        data = self.process.stdout.read(bytes_needed)
        if len(data) < bytes_needed:
            outdata[:] = np.zeros((frames, _CHANNELS), dtype=np.int16)
            self.stream.stop()
            self.timer.stop()
            return

        array = np.frombuffer(data, dtype=np.int16).reshape(-1, _CHANNELS)
        outdata[:] = array
        self.samples_played += frames

    def tick(self) -> None:
        if not self.paused:
            current_time = self.samples_played / _SAMPLE_RATE
            self.callback(current_time)

    def set_pause(self, value: bool) -> None:
        self.paused = value

    def stop(self) -> None:
        self.paused = True
        if self.stream:
            self.stream.stop()
            self.stream.close()
        if self.process:
            self.process.terminate()
            self.process = None
        self.timer.stop()

    def seek_to(self, seconds: float) -> None:
        """Optional: restart FFmpeg from a given time."""
        self.stop()
        self.samples_played = int(seconds * _SAMPLE_RATE)

        self.process = subprocess.Popen(
            [
                "ffmpeg",
                "-ss",
                str(seconds),
                "-i",
                self.source,
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(_SAMPLE_RATE),
                "-ac",
                str(_CHANNELS),
                "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        self.stream = sd.OutputStream(
            samplerate=_SAMPLE_RATE,
            channels=_CHANNELS,
            dtype="int16",
            blocksize=_STREAM_BUFFER_SIZE,
            callback=self._stream_callback,
        )
        self.stream.start()
        self.timer.start(_REFRESH_RATE_MS)
        self.paused = False
