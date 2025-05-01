"""Dialog to preview a downloaded song."""

import subprocess
from pathlib import Path

import cffi
import numpy as np
import sounddevice as sd
from PySide6 import QtCore, QtGui, QtWidgets

from usdb_syncer import events, settings
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


class PreviewDialog(Ui_Dialog, QtWidgets.QDialog):
    """Dialog to preview a downloaded song."""

    def __init__(self, parent: QtWidgets.QWidget, song: UsdbSong) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        if song.sync_meta and song.sync_meta.txt:
            contents = song.sync_meta.path.parent.joinpath(
                song.sync_meta.txt.fname
            ).read_text("utf-8")
            txt = SongTxt.parse(contents, song_logger(song.song_id))
            self.setWindowTitle(txt.headers.artist_title_str())
            view = PianoRollWidget(txt)
            self.layout_main.insertWidget(0, view)
            if song.sync_meta and song.sync_meta.audio:
                path = song.sync_meta.path.parent.joinpath(song.sync_meta.audio.fname)
                self.player = AudioPlayer(path, view.update_position)
        self.button_pause.toggled.connect(lambda t: self.player.set_pause(t))
        self.button_backward.pressed.connect(
            lambda: self.player.seek_to(view.previous_start())
        )
        self.button_forward.pressed.connect(
            lambda: self.player.seek_to(view.next_start())
        )
        self._on_theme_changed(settings.get_theme())
        events.ThemeChanged.subscribe(lambda e: self._on_theme_changed(e.theme))

    def _on_theme_changed(self, theme: settings.Theme) -> None:
        self.button_pause.setIcon(icons.Icon.PAUSE_REMOTE.icon(theme))
        self.button_backward.setIcon(icons.Icon.SKIP_BACKWARD.icon(theme))
        self.button_forward.setIcon(icons.Icon.SKIP_FORWARD.icon(theme))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.player.stop()
        event.accept()


class _LineTimings:
    """Wrapper for a line with absolute timings in seconds."""

    line_break: float | None = None

    def __init__(self, line: tracks.Line, gap: int, bpm: BeatsPerMinute) -> None:
        self.line = line
        self.start = gap / 1000 + bpm.beats_to_secs(line.start())
        self.end = gap / 1000 + bpm.beats_to_secs(line.end())
        self.len = self.end - self.start
        if line.line_break:
            self.line_break = gap / 1000 + bpm.beats_to_secs(
                line.line_break.previous_line_out_time
            )


class PianoRollWidget(QtWidgets.QWidget):
    def __init__(self, txt: SongTxt):
        super().__init__()
        self.txt = txt
        self.lines = [
            _LineTimings(line, txt.headers.gap, txt.headers.bpm)
            for line in txt.notes.track_1
        ]
        self.current_time = 0.0  # In seconds
        self._current_idx = 0
        self._current_line = self.lines[0]
        self.setMinimumSize(800, 200)

    # def _current_line(self) -> _LineTimings:
    #     return next(
    #         li
    #         for li in self.lines
    #         if li.line_break is None or li.line_break > self.current_time
    #     )

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        with QtGui.QPainter(self) as painter:
            height = self.height()
            width = self.width()
            line = self._current_line.line

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
                (self.current_time - self._current_line.start)
                / self._current_line.len
                * width
            )
            x_pos = min(max(x_pos, 0), width - _NEEDLE_WIDTH)
            painter.drawLine(x_pos, 0, x_pos, height)

    def update_position(self, time_in_seconds: float) -> None:
        self.current_time = time_in_seconds
        new_idx, new_line = next(
            (i, li)
            for i, li in enumerate(self.lines)
            if li.line_break is None or li.line_break > self.current_time
        )
        self._current_idx = new_idx
        self._current_line = new_line
        self.update()

    def previous_start(self) -> float:
        if (
            self._current_idx > 0
            and self.current_time - _DOUBLECLICK_DELAY_SECS < self._current_line.start
        ):
            return self.lines[self._current_idx - 1].start
        return self._current_line.start

    def next_start(self) -> float | None:
        if self._current_idx + 1 >= len(self.lines):
            return None
        return self.lines[self._current_idx + 1].start


class AudioPlayer:
    def __init__(self, source: Path, ui_update_callback) -> None:
        self.source = source
        self.ui_update_callback = ui_update_callback

        self.samples_played = 0
        self.paused = False
        self.stream = None
        self.process = None

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.tick)

        self.buffer_size = 2048  # Can be adjusted for latency/performance tradeoff

        self.start_ffmpeg()
        self.start_stream()

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
            blocksize=self.buffer_size,
            callback=self.callback,
        )
        self.stream.start()
        self.timer.start(_REFRESH_RATE_MS)

    def callback(
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
            self.ui_update_callback(current_time)

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
            blocksize=self.buffer_size,
            callback=self.callback,
        )
        self.stream.start()
        self.timer.start(_REFRESH_RATE_MS)
        self.paused = False
