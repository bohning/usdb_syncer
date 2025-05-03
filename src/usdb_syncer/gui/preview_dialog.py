"""Dialog to preview a downloaded song."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import attrs
import numpy as np
import sounddevice as sd
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from usdb_syncer import utils
from usdb_syncer.gui import events, icons, theme
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
_DOUBLECLICK_DELAY_MS = 200
_DOUBLECLICK_DELAY_SECS = _DOUBLECLICK_DELAY_MS / 1000
_STREAM_BUFFER_SIZE = 2048
_PITCH_ROWS = 16
_RELATIVE_TEXT_ROW_HEIGHT = 2
_EPS_SECS = 0.01


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


T = TypeVar("T", int, float)


def clamp(value: T, lower: T, upper: T) -> T:
    return min(max(value, lower), upper)


class PreviewDialog(Ui_Dialog, QtWidgets.QDialog):
    """Dialog to preview a downloaded song."""

    def __init__(self, parent: QtWidgets.QWidget, txt: SongTxt, audio: Path) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self.setWindowTitle(txt.headers.artist_title_str())

        self._state = _PlayState.new(txt, audio)
        palette = theme.Theme.from_settings().preview_palette()
        self._song_view = _SongView(self._state, palette, self._on_drag)
        self.layout_main.insertWidget(0, self._song_view)
        self._line_view = _LineView(self._state, palette)
        self.layout_main.insertWidget(1, self._line_view)
        self.player = _AudioPlayer.new(audio, self._state)
        self._update_timer = QtCore.QTimer(self, interval=_REFRESH_RATE_MS)
        self._update_timer.timeout.connect(self._update_time)
        self._update_timer.start()

        self.button_pause.toggled.connect(self._on_pause_toggled)
        self._seek_timer = QtCore.QTimer(
            self, singleShot=True, interval=_DOUBLECLICK_DELAY_MS
        )
        self._seek_timer.timeout.connect(self._on_seek_timeout)
        self.button_to_start.pressed.connect(self._on_seek_start)
        self.button_backward.pressed.connect(self._on_seek_backward)
        self.button_forward.pressed.connect(self._on_seek_forward)
        self.button_to_end.pressed.connect(self._on_seek_end)

        self._on_theme_changed(theme.Theme.from_settings())
        events.ThemeChanged.subscribe(lambda e: self._on_theme_changed(e.theme))

    def _update_time(self) -> None:
        # only get current time from playback stream if not currently seeking
        if not self._state.seeking:
            self._state.calculate_time_from_samples()
        self._song_view.update()
        self._line_view.update()

    def _on_pause_toggled(self, paused: bool) -> None:
        self._state.paused = paused

    def _on_seek_start(self) -> None:
        self._start_seeking(-self._state.current_idx)

    def _on_seek_end(self) -> None:
        self._start_seeking(len(self._state.lines) - self._state.current_idx - 1)

    def _on_seek_backward(self) -> None:
        line_elapsed = self._state.current_time - self._state.current_line.start
        if line_elapsed > _DOUBLECLICK_DELAY_SECS:
            self._start_seeking(0)
        elif self._state.current_idx > 0:
            self._start_seeking(-1)

    def _on_seek_forward(self) -> None:
        if (
            self._state.current_idx == 0
            and self._state.current_time + _EPS_SECS < self._state.current_line.start
        ):
            self._start_seeking(0)
        elif self._state.current_idx < len(self._state.lines) - 1:
            self._start_seeking(1)

    def _start_seeking(self, line_delta: int) -> None:
        self._state.seeking = True
        idx = self._state.current_idx + line_delta
        self._state.set_current_time(self._state.lines[idx].start)
        self._seek_timer.start()

    def _on_drag(self, target_time: float, released: bool) -> None:
        self._state.seeking = not released
        self._seek_timer.stop()
        self._state.set_current_time(target_time)
        if released:
            self.player.seek_to(self._state.current_time)

    def _on_seek_timeout(self) -> None:
        self.player.seek_to(self._state.current_time)
        self._state.seeking = False

    def _on_theme_changed(self, theme: theme.Theme) -> None:
        self.button_pause.setIcon(icons.Icon.PAUSE_REMOTE.icon(theme.KEY))
        self.button_to_start.setIcon(icons.Icon.SKIP_TO_START.icon(theme.KEY))
        self.button_backward.setIcon(icons.Icon.SKIP_BACKWARD.icon(theme.KEY))
        self.button_forward.setIcon(icons.Icon.SKIP_FORWARD.icon(theme.KEY))
        self.button_to_end.setIcon(icons.Icon.SKIP_TO_END.icon(theme.KEY))
        self._song_view.colors = self._line_view.colors = theme.preview_palette()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.player.stop()
        event.accept()


@attrs.define
class _PlayState:
    """State of the current playback."""

    txt: SongTxt
    lines: list[_Line]
    current_idx: int
    current_line: _Line
    current_time: float
    current_rel_pos: float
    samples_played: int
    song_secs: float
    seeking: bool = False
    paused: bool = False

    @classmethod
    def new(cls, txt: SongTxt, audio: Path) -> _PlayState:
        song_secs = utils.get_media_duration(audio)
        lines = [
            _Line.new(line, txt.headers.gap, txt.headers.bpm, song_secs)
            for line in txt.notes.track_1
        ]
        return cls(
            txt=txt,
            lines=lines,
            current_idx=0,
            current_line=lines[0],
            current_time=lines[0].start,
            current_rel_pos=0.0,
            samples_played=0,
            song_secs=song_secs,
        )

    def calculate_time_from_samples(self) -> None:
        self.current_time = self.samples_played / _SAMPLE_RATE
        self._update_with_current_time()

    def set_current_time(self, secs: float) -> None:
        self.current_time = secs
        self._update_with_current_time()

    def _update_with_current_time(self) -> None:
        self.current_rel_pos = self.current_time / self.song_secs
        self.current_idx, self.current_line = next(
            (i, li)
            for i, li in enumerate(self.lines)
            if li.line_break is None or li.line_break > self.current_time
        )


@attrs.define
class _Line:
    """Information for rendering a line."""

    notes: list[_Note]
    start: float
    end: float
    duration: float
    line_break: float | None
    rel_start: float
    rel_end: float
    rel_duration: float
    text: str

    @classmethod
    def new(
        cls, line: tracks.Line, gap: int, bpm: BeatsPerMinute, song_duration: float
    ) -> _Line:
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
            notes=_Note.from_line(line),
            start=start,
            end=end,
            duration=duration,
            rel_start=start / song_duration,
            rel_end=end / song_duration,
            rel_duration=duration / song_duration,
            line_break=line_break,
            text="".join(n.text for n in line.notes).strip(),
        )


@attrs.define
class _Note:
    """Information for rendering a note."""

    note: tracks.Note
    start: float
    duration: float
    pitch: float

    @classmethod
    def new(
        cls, note: tracks.Note, line_start: int, line_len: int, line_pitch: range
    ) -> _Note:
        start = (note.start - line_start) / line_len
        duration = note.duration / line_len
        # move to the middle of available space
        shift = max(_PITCH_ROWS - len(line_pitch), 0) // 2
        pitch = 1 - (note.pitch - line_pitch.start + shift) / _PITCH_ROWS
        return cls(note=note, start=start, duration=duration, pitch=pitch)

    @classmethod
    def from_line(cls, line: tracks.Line) -> list[_Note]:
        start = line.start()
        duration = line.end() - start
        min_pitch = min(n.pitch for n in line.notes)
        max_pitch = max(n.pitch for n in line.notes)
        pitch = range(min_pitch, max_pitch + 1)
        return [_Note.new(n, start, duration, pitch) for n in line.notes]


class _SongView(QtWidgets.QWidget):
    _is_dragging = False

    def __init__(
        self,
        state: _PlayState,
        colors: theme.PreviewPalette,
        on_drag: Callable[[float, bool], None],
    ):
        super().__init__()
        self._state = state
        self.colors = colors
        self._on_drag = on_drag
        self.setMinimumSize(600, 20)
        self.setMaximumHeight(40)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        height = self.height()
        width = self.width()
        with QtGui.QPainter(self) as painter:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.colors.line)
            for line in self._state.lines:
                x = round(line.rel_start * width)
                w = round(line.rel_duration * width)
                painter.drawRect(x, 0, w, height)

            painter.setPen(QtGui.QPen(self.colors.needle, _NEEDLE_WIDTH))
            x_pos = round(self._state.current_rel_pos * width)
            x_pos = clamp(x_pos, _NEEDLE_WIDTH // 2, width - _NEEDLE_WIDTH // 2)
            painter.drawLine(x_pos, 0, x_pos, height)

    def _x_pos_to_current_time(self, x: int) -> float:
        return self._state.song_secs * clamp(x / self.width(), 0.0, 1.0)

    def mousePressEvent(self, event: QtGui.QMouseEvent):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._on_drag(self._x_pos_to_current_time(event.pos().x()), False)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):  # noqa: N802
        if self._is_dragging:
            self._on_drag(self._x_pos_to_current_time(event.pos().x()), False)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):  # noqa: N802
        if self._is_dragging:
            self._is_dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._on_drag(self._x_pos_to_current_time(event.pos().x()), True)


@attrs.define
class _LinePaintContext:
    """Values for painting a line."""

    total_width: int
    row_height: int
    notes_height: int
    current_pos: float
    radius: float
    text_height: int

    @classmethod
    def new(cls, view: _LineView) -> _LinePaintContext:
        total_height = view.height()
        total_width = view.width()

        # divide into equally sized pitch rows plus one scaled row for text
        row_height = round(total_height / (_PITCH_ROWS + _RELATIVE_TEXT_ROW_HEIGHT))
        notes_height = row_height * _PITCH_ROWS
        text_height = total_height - notes_height

        line_elapsed = view._state.current_time - view._state.current_line.start
        current_pos = line_elapsed / view._state.current_line.duration

        return cls(
            total_width=total_width,
            row_height=row_height,
            notes_height=notes_height,
            current_pos=current_pos,
            # make sides circular
            radius=row_height / 2,
            text_height=text_height,
        )


class _LineView(QtWidgets.QWidget):
    _POINTER_SIZE_IN_ROWS = 1.5

    def __init__(self, state: _PlayState, colors: theme.PreviewPalette):
        super().__init__()
        self._state = state
        self.colors = colors
        self.setMinimumSize(600, 200)
        self.setMaximumHeight(400)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        with QtGui.QPainter(self) as painter:
            ctx = _LinePaintContext.new(self)
            self._draw_grid(painter, ctx)
            self._draw_notes(painter, ctx)
            self._draw_text(painter, ctx)
            self._draw_pointer(painter, ctx)

    def _draw_grid(self, painter: QtGui.QPainter, ctx: _LinePaintContext) -> None:
        painter.setPen(QtGui.QPen(self.colors.grid, 1))
        for i in range(1, _PITCH_ROWS):
            y = ctx.notes_height - i * ctx.row_height
            painter.drawLine(0, y, ctx.total_width, y)

    def _draw_notes(self, painter: QtGui.QPainter, ctx: _LinePaintContext) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        for note in self._state.current_line.notes:
            active = ctx.current_pos > note.start
            painter.setBrush(self.colors.active_note if active else self.colors.note)
            x = round(note.start * ctx.total_width)
            y = round(note.pitch * ctx.notes_height) - ctx.row_height
            w = round(note.duration * ctx.total_width)
            painter.drawRoundedRect(x, y, w, ctx.row_height, ctx.radius, ctx.radius)

    def _draw_text(self, painter: QtGui.QPainter, ctx: _LinePaintContext) -> None:
        font = painter.font()
        font.setPixelSize(ctx.text_height * 2 // 3)
        painter.setFont(font)
        font_metrics = QtGui.QFontMetrics(font)
        text_width = font_metrics.horizontalAdvance(self._state.current_line.text)
        text_start = (ctx.total_width - text_width) // 2
        for note in self._state.current_line.notes:
            active = ctx.current_pos > note.start
            painter.setPen(self.colors.active_text if active else self.colors.text)
            painter.drawText(
                QtCore.QRect(text_start, ctx.notes_height, text_width, ctx.text_height),
                Qt.AlignmentFlag.AlignVCenter,
                note.note.text,
            )
            text_start += font_metrics.horizontalAdvance(note.note.text)

    def _draw_pointer(self, painter: QtGui.QPainter, ctx: _LinePaintContext):
        pointer_size = round(ctx.row_height * self._POINTER_SIZE_IN_ROWS)
        x = round(ctx.current_pos * ctx.total_width)
        current_pitch = next(
            (
                n
                for n in reversed(self._state.current_line.notes)
                if n.start < ctx.current_pos
            ),
            self._state.current_line.notes[0],
        ).pitch
        if current_pitch > 0.1:
            y_point = round(current_pitch * ctx.notes_height) - ctx.row_height
            y_base = y_point - pointer_size
        else:
            # close to top border, show pointer below note
            # also ensure it's in view, even if the note is too high
            y_point = max(round(current_pitch * ctx.notes_height), 0)
            y_base = y_point + pointer_size
        points = (
            QtCore.QPoint(x, y_point),
            QtCore.QPoint(x - pointer_size // 2, y_base),
            QtCore.QPoint(x + pointer_size // 2, y_base),
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.colors.active_note)
        painter.drawPolygon(points)


@attrs.define
class _AudioPlayer:
    _source: Path
    _state: _PlayState
    stream: sd.OutputStream | None = None
    process: subprocess.Popen | None = None

    @classmethod
    def new(cls, source: Path, state: _PlayState) -> _AudioPlayer:
        player = cls(source=source, state=state)
        player.start_ffmpeg()
        player.start_stream()
        return player

    def start_ffmpeg(self) -> None:
        self.process = subprocess.Popen(
            [
                "ffmpeg",
                "-i",
                self._source,
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

    def _stream_callback(
        self, outdata: np.ndarray, frames: int, time: Any, status: sd.CallbackFlags
    ) -> None:
        if (
            not (self.process and self.process.stdout and self.stream)
            or self._state.paused
        ):
            outdata[:] = np.zeros((frames, _CHANNELS), dtype=np.int16)
            return
        bytes_needed = frames * _CHANNELS * 2
        data = self.process.stdout.read(bytes_needed)
        if len(data) < bytes_needed:
            outdata[:] = np.zeros((frames, _CHANNELS), dtype=np.int16)
            self.stream.stop()
            return
        array = np.frombuffer(data, dtype=np.int16).reshape(-1, _CHANNELS)
        outdata[:] = array
        self._state.samples_played += frames

    def stop(self) -> None:
        if self.stream:
            self.stream.stop()
            self.stream.close()
        if self.process:
            self.process.terminate()
            self.process = None

    def seek_to(self, seconds: float) -> None:
        """Optional: restart FFmpeg from a given time."""
        self.stop()
        self._state.samples_played = int(seconds * _SAMPLE_RATE)

        self.process = subprocess.Popen(
            [
                "ffmpeg",
                "-ss",
                str(seconds),
                "-i",
                self._source,
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
