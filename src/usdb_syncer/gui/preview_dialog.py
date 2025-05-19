"""Dialog to preview a downloaded song."""

from __future__ import annotations

import functools
import subprocess
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any, NewType, TypeVar

import attrs
import numpy as np
import sounddevice
import soundfile
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from usdb_syncer import utils
from usdb_syncer.gui import events, icons, theme
from usdb_syncer.gui.forms.PreviewDialog import Ui_Dialog
from usdb_syncer.gui.resources.audio import METRONOME_TICK_WAV
from usdb_syncer.logger import song_logger
from usdb_syncer.song_txt import SongTxt, tracks
from usdb_syncer.song_txt.auxiliaries import BeatsPerMinute
from usdb_syncer.usdb_song import UsdbSong

Seconds = NewType("Seconds", float)
Milliseconds = NewType("Milliseconds", int)
Sample = NewType("Sample", int)
Pixel = NewType("Pixel", int)
Fraction = NewType("Fraction", float)
"""A relative size, i.e. from the interval [0, 1]."""

_PITCH_ROWS = 16
_EPS_SECS = Seconds(0.01)
_INT16_MAX = 2**15 - 1
_INT16_MIN = -(2**15)
_SAMPLE_RATE = Sample(44100)
_SYNTH_AMPLITUDE = 0.4
_SYNTH_ATTACK_SECS = Seconds(0.01)
_SYNTH_RELEASE_SECS = Seconds(0.05)
_SYNTH_ATTACK_SAMPLES = Sample(int(_SYNTH_ATTACK_SECS * _SAMPLE_RATE))
_SYNTH_RELEASE_SAMPLES = Sample(int(_SYNTH_RELEASE_SECS * _SAMPLE_RATE))


T = TypeVar("T", int, float)


def clamp(value: T, lower: T, upper: T) -> T:
    return min(max(value, lower), upper)


class PreviewDialog(Ui_Dialog, QtWidgets.QDialog):
    """Dialog to preview a downloaded song."""

    _MIN_COVER_SIZE = Pixel(100)
    _MAX_COVER_SIZE = Pixel(200)
    _FPS = 60
    _REFRESH_RATE = Milliseconds(1000 // _FPS)
    _DOUBLECLICK_DELAY_MS = Milliseconds(200)
    _DOUBLECLICK_DELAY_SECS = Seconds(_DOUBLECLICK_DELAY_MS / 1000)

    def __init__(
        self, parent: QtWidgets.QWidget, txt: SongTxt, audio: Path, cover: Path | None
    ) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self.setWindowTitle(txt.headers.artist_title_str())
        self._setup_voice_selection(txt)
        self._state = _PlayState.new(txt, audio)
        self._player = _AudioPlayer.new(audio, self._state)
        self._setup_views()
        self._set_song_info(txt, cover)
        self._connect_ui_inputs()
        self._setup_timers()
        self._on_theme_changed(theme.Theme.from_settings())
        events.ThemeChanged.subscribe(lambda e: self._on_theme_changed(e.theme))

    @classmethod
    def load(cls, parent: QtWidgets.QWidget, song: UsdbSong) -> None:
        if not (txt_path := song.txt_path()) or not (audio_path := song.audio_path()):
            QtWidgets.QMessageBox.warning(
                parent, "Aborted", "Song must have txt and audio files!"
            )
            return
        logger = song_logger(song.song_id)
        if not (txt := SongTxt.try_from_file(txt_path, logger)):
            QtWidgets.QMessageBox.warning(parent, "Aborted", "Txt file is invalid!")
            return
        cls(parent, txt, audio_path, song.cover_path()).show()

    def _setup_voice_selection(self, txt: SongTxt) -> None:
        self.label_voice.setVisible(bool(txt.notes.track_2))
        self.comboBox_voice.setVisible(bool(txt.notes.track_2))
        self.comboBox_voice.addItem(txt.headers.p1 or "P1")
        self.comboBox_voice.addItem(txt.headers.p2 or "P2")

    def _setup_views(self) -> None:
        palette = theme.Theme.from_settings().preview_palette()
        self._song_view = _SongView(self._state, palette, self._on_drag)
        self.layout_main.insertWidget(0, self._song_view, 10)
        self._line_view = _LineView(self._state, palette)
        self.layout_main.insertWidget(1, self._line_view, 10)
        self.layout_main.insertStretch(2, 1)

    def _connect_ui_inputs(self) -> None:
        self.button_pause.toggled.connect(self._on_pause_toggled)
        self.button_to_start.pressed.connect(self._on_seek_start)
        self.button_backward.pressed.connect(self._on_seek_backward)
        self.button_forward.pressed.connect(self._on_seek_forward)
        self.button_to_end.pressed.connect(self._on_seek_end)
        self._on_source_volume_changed(self.slider_source.value())
        self._on_ticks_volume_changed(self.slider_ticks.value())
        self._on_pitch_volume_changed(self.slider_pitch.value())
        self.slider_source.valueChanged.connect(self._on_source_volume_changed)
        self.slider_ticks.valueChanged.connect(self._on_ticks_volume_changed)
        self.slider_pitch.valueChanged.connect(self._on_pitch_volume_changed)
        self.comboBox_voice.currentIndexChanged.connect(self._state.set_voice)

    def _set_song_info(self, txt: SongTxt, cover: Path | None) -> None:
        if cover:
            label = _SquareLabel("")
            label.setScaledContents(True)
            label.setPixmap(QtGui.QPixmap(cover))
            label.setMinimumSize(self._MIN_COVER_SIZE, self._MIN_COVER_SIZE)
            label.setMaximumSize(self._MAX_COVER_SIZE, self._MAX_COVER_SIZE)
            self.layout_extra.insertWidget(1, label)
        self.label_bpm.setText(f"#BPM: {txt.headers.bpm}")
        self.label_gap.setText(f"#GAP: {txt.headers.gap}")
        self.label_start.setText(f"#START: {txt.headers.start or '-'}")
        self.label_end.setText(f"#END: {txt.headers.end or '-'}")

    def _setup_timers(self) -> None:
        self._update_timer = QtCore.QTimer(self, interval=self._REFRESH_RATE)
        self._update_timer.timeout.connect(self._update_time)
        self._update_timer.start()
        self._seek_timer = QtCore.QTimer(
            self, singleShot=True, interval=self._DOUBLECLICK_DELAY_MS
        )
        self._seek_timer.timeout.connect(self._on_seek_timeout)

    def _update_time(self) -> None:
        # only get current time from playback stream if not currently seeking
        if not self._state.seeking:
            self._state.calculate_video_time_from_audio()
        self._song_view.update()
        self._line_view.update()
        current = _secs_to_str(self._state.current_video_time)
        song = _secs_to_str(self._state.song_duration)
        self.label_time.setText(f"{current} / {song}")

    def _on_pause_toggled(self, paused: bool) -> None:
        self._state.paused = paused

    def _on_seek_start(self) -> None:
        self._start_seeking(-self._state.current_video_line_idx)

    def _on_seek_end(self) -> None:
        self._start_seeking(
            len(self._state.lines) - self._state.current_video_line_idx - 1
        )

    def _on_seek_backward(self) -> None:
        line_elapsed = (
            self._state.current_video_time - self._state.current_video_line.start
        )
        if line_elapsed > self._DOUBLECLICK_DELAY_SECS:
            self._start_seeking(0)
        elif self._state.current_video_line_idx > 0:
            self._start_seeking(-1)

    def _on_seek_forward(self) -> None:
        if (
            self._state.current_video_line_idx == 0
            and self._state.current_video_time + _EPS_SECS
            < self._state.current_video_line.start
        ):
            self._start_seeking(0)
        elif self._state.current_video_line_idx < len(self._state.lines) - 1:
            self._start_seeking(1)

    def _start_seeking(self, line_delta: int) -> None:
        self._state.seeking = True
        idx = self._state.current_video_line_idx + line_delta
        self._state.set_current_video_time(self._state.lines[idx].start)
        self._seek_timer.start()

    def _on_drag(self, target_time: Seconds, released: bool) -> None:
        self._state.seeking = not released
        self._seek_timer.stop()
        self._state.set_current_video_time(Seconds(target_time))
        if released:
            self._player.seek_to(self._state.current_video_time)

    def _on_seek_timeout(self) -> None:
        self._player.seek_to(self._state.current_video_time)
        self._state.seeking = False

    def _on_theme_changed(self, theme: theme.Theme) -> None:
        self.button_pause.setIcon(icons.Icon.PAUSE_REMOTE.icon(theme.KEY))
        self.button_to_start.setIcon(icons.Icon.SKIP_TO_START.icon(theme.KEY))
        self.button_backward.setIcon(icons.Icon.SKIP_BACKWARD.icon(theme.KEY))
        self.button_forward.setIcon(icons.Icon.SKIP_FORWARD.icon(theme.KEY))
        self.button_to_end.setIcon(icons.Icon.SKIP_TO_END.icon(theme.KEY))
        self._song_view.colors = self._line_view.colors = theme.preview_palette()

    def _on_source_volume_changed(self, value: int) -> None:
        # ticks are in 10% steps
        value = value * 10
        self.label_source_volume.setText(str(value))
        self._state.source_volume = _percentage_to_amplitude_factor(value)

    def _on_ticks_volume_changed(self, value: int) -> None:
        value = value * 10
        self.label_ticks_volume.setText(str(value))
        self._state.ticks_volume = _percentage_to_amplitude_factor(value)

    def _on_pitch_volume_changed(self, value: int) -> None:
        value = value * 10
        self.label_pitch_volume.setText(str(value))
        self._state.pitch_volume = _percentage_to_amplitude_factor(value)

    def _on_voice_changed(self, voice: int) -> None:
        pass

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self._player.stop()
        event.accept()

    def reject(self) -> None:
        self._player.stop()
        super().reject()


def _secs_to_str(seconds: Seconds) -> str:
    secs = int(seconds)
    return f"{secs // 60:02}:{secs % 60:02}"


class _SquareLabel(QtWidgets.QLabel):
    """Custom widget to contain the cover image and maintain sqaured."""

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return width

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802
        base = super().sizeHint()
        side = min(base.width(), base.height())
        return QtCore.QSize(side, side)


@attrs.define
class _PlayState:
    """State of the current playback."""

    # shared state
    _tracks: list[list[_Line]]
    lines: list[_Line] = attrs.field(init=False)
    song_duration: Seconds
    seeking: bool = False
    paused: bool = False

    # video state
    current_video_line_idx: int = 0
    current_video_line: _Line = attrs.field(init=False)
    current_video_time: Seconds = attrs.field(init=False)
    current_pos_in_line: Fraction = Fraction(0.0)

    # audio state
    current_sample: Sample = Sample(0)
    _audio_note_iter: Generator[_Note, None, None] = attrs.field(init=False)
    current_audio_note: _Note | None = attrs.field(init=False)
    source_volume: float = 0.0
    ticks_volume: float = 0.0
    pitch_volume: float = 0.0

    @classmethod
    def new(cls, txt: SongTxt, audio: Path) -> _PlayState:
        song_duration = Seconds(utils.get_media_duration(audio))
        track_list = list(filter(None, [txt.notes.track_1, txt.notes.track_2]))
        tracks_ = [
            [
                _Line.new(
                    line, Milliseconds(txt.headers.gap), txt.headers.bpm, song_duration
                )
                for line in track
            ]
            for track in track_list
        ]
        state = cls(tracks=tracks_, song_duration=song_duration)
        if txt.headers.previewstart is not None:
            start = Seconds(txt.headers.previewstart)
        else:
            start = state.lines[0].start
        state.set_current_video_time(start)
        return state

    def __attrs_post_init__(self) -> None:
        self.lines = self._tracks[0]
        self.current_video_line = self.lines[0]
        self.current_video_time = self.lines[0].start
        self._audio_note_iter = self._iter_notes()
        self.current_audio_note = next(self._audio_note_iter, None)

    def calculate_video_time_from_audio(self) -> None:
        self.set_current_video_time(Seconds(self.current_sample / _SAMPLE_RATE))

    def set_current_video_time(self, secs: Seconds) -> None:
        self.current_video_time = secs
        self.current_pos_in_line = Fraction(
            self.current_video_time / self.song_duration
        )
        self.current_video_line_idx, self.current_video_line = next(
            (i, li)
            for i, li in enumerate(self.lines)
            if li.line_break is None or li.line_break > self.current_video_time
        )

    def advance_current_sample(self, delta: int) -> None:
        self.current_sample = Sample(self.current_sample + delta)
        self._advance_to_next_unplayed_note()

    def set_current_sample_from_secs(self, secs: float) -> None:
        self.current_sample = Sample(int(secs * _SAMPLE_RATE))
        self._reset_current_audio_note()

    def _reset_current_audio_note(self) -> None:
        self._audio_note_iter = self._iter_notes()
        self.current_audio_note = next(self._audio_note_iter, None)
        self._advance_to_next_unplayed_note()

    def _advance_to_next_unplayed_note(self) -> None:
        while (
            self.current_audio_note
            and self.current_sample > self.current_audio_note.end_sample
        ):
            self.current_audio_note = next(self._audio_note_iter, None)

    def _iter_notes(self) -> Generator[_Note, None, None]:
        for line in self.lines:
            yield from line.notes

    def set_voice(self, voice: int) -> None:
        self.lines = self._tracks[voice]
        self.set_current_video_time(self.current_video_time)
        self._reset_current_audio_note()


def _beat_to_secs(beat: int, gap: Milliseconds, bpm: BeatsPerMinute) -> Seconds:
    return Seconds(gap / 1000 + bpm.beats_to_secs(beat))


def _beat_to_sample(beat: int, gap: Milliseconds, bpm: BeatsPerMinute) -> Sample:
    return Sample(int(_beat_to_secs(beat, gap, bpm) * _SAMPLE_RATE))


@attrs.define
class _Line:
    """Information for rendering a line."""

    notes: list[_Note]
    start: Seconds
    end: Seconds
    duration: Seconds
    line_break: Seconds | None
    rel_x_pos_in_song: Fraction
    rel_width_in_song: Fraction
    text: str

    @classmethod
    def new(
        cls,
        line: tracks.Line,
        gap: Milliseconds,
        bpm: BeatsPerMinute,
        song_duration: Seconds,
    ) -> _Line:
        start = _beat_to_secs(line.start(), gap, bpm)
        end = _beat_to_secs(line.end(), gap, bpm)
        duration = Seconds(end - start)
        if line.line_break:
            line_break = _beat_to_secs(line.line_break.previous_line_out_time, gap, bpm)
        else:
            line_break = None
        return cls(
            notes=_Note.from_line(line, gap, bpm),
            start=start,
            end=end,
            duration=duration,
            rel_x_pos_in_song=Fraction(start / song_duration),
            rel_width_in_song=Fraction(duration / song_duration),
            line_break=line_break,
            text="".join(n.text for n in line.notes).strip(),
        )


@attrs.define
class _Note:
    """Information for rendering and playing a note."""

    text: str
    x_pos: Fraction
    width: Fraction
    y_pos: Fraction

    freq: float
    start_sample: Sample
    end_sample: Sample
    kind: tracks.NoteKind

    @classmethod
    def new(
        cls,
        note: tracks.Note,
        line_start: int,
        line_len: int,
        line_pitch: range,
        gap: Milliseconds,
        bpm: BeatsPerMinute,
    ) -> _Note:
        x_pos = Fraction((note.start - line_start) / line_len)
        width = Fraction(note.duration / line_len)
        # move to the middle of available space
        shift = max(_PITCH_ROWS - len(line_pitch), 0) // 2
        y_pos = Fraction(1 - (note.pitch - line_pitch.start + shift) / _PITCH_ROWS)
        return cls(
            text=note.text,
            kind=note.kind,
            x_pos=x_pos,
            width=width,
            y_pos=y_pos,
            freq=_ultrastar_pitch_to_freq(note.pitch),
            start_sample=_beat_to_sample(note.start, gap, bpm),
            end_sample=_beat_to_sample(note.end(), gap, bpm),
        )

    @classmethod
    def from_line(
        cls, line: tracks.Line, gap: Milliseconds, bpm: BeatsPerMinute
    ) -> list[_Note]:
        start = line.start()
        duration = line.end() - start
        min_pitch = min(n.pitch for n in line.notes)
        max_pitch = max(n.pitch for n in line.notes)
        pitch = range(min_pitch, max_pitch + 1)
        return [_Note.new(n, start, duration, pitch, gap, bpm) for n in line.notes]


class _SongView(QtWidgets.QWidget):
    _is_dragging = False
    _MIN_HEIGHT = Pixel(20)
    _MAX_HEIGHT = Pixel(40)
    _NEEDLE_WIDTH = Pixel(2)

    def __init__(
        self,
        state: _PlayState,
        colors: theme.PreviewPalette,
        on_drag: Callable[[Seconds, bool], None],
    ):
        super().__init__()
        self._state = state
        self.colors = colors
        self._on_drag = on_drag
        self.setMinimumHeight(self._MIN_HEIGHT)
        self.setMaximumHeight(self._MAX_HEIGHT)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        height = self.height()
        width = self.width()
        with QtGui.QPainter(self) as painter:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.colors.line)
            for line in self._state.lines:
                x = round(line.rel_x_pos_in_song * width)
                w = round(line.rel_width_in_song * width)
                painter.drawRect(x, 0, w, height)

            painter.setPen(QtGui.QPen(self.colors.needle, self._NEEDLE_WIDTH))
            x_pos = round(self._state.current_pos_in_line * width)
            half_needle = self._NEEDLE_WIDTH // 2
            x_pos = clamp(x_pos, half_needle, width - half_needle)
            painter.drawLine(x_pos, 0, x_pos, height)

    def _current_time_at_mouse(self, event: QtGui.QMouseEvent) -> Seconds:
        return Seconds(
            self._state.song_duration * clamp(event.pos().x() / self.width(), 0.0, 1.0)
        )

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._on_drag(self._current_time_at_mouse(event), False)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if self._is_dragging:
            self._on_drag(self._current_time_at_mouse(event), False)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if self._is_dragging:
            self._is_dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._on_drag(self._current_time_at_mouse(event), True)


@attrs.define
class _LinePaintContext:
    """Values for painting a line."""

    total_width: Pixel
    row_height: Pixel
    notes_height: Pixel
    current_pos: Fraction
    radius: float
    text_height: Pixel

    _RELATIVE_TEXT_ROW_HEIGHT = 2

    @classmethod
    def new(cls, view: _LineView) -> _LinePaintContext:
        total_height = Pixel(view.height())
        total_width = Pixel(view.width())

        # divide into equally sized pitch rows plus one scaled row for text
        row_height = Pixel(
            round(total_height / (_PITCH_ROWS + cls._RELATIVE_TEXT_ROW_HEIGHT))
        )
        notes_height = Pixel(row_height * _PITCH_ROWS)
        text_height = Pixel(total_height - notes_height)

        line_elapsed = (
            view._state.current_video_time - view._state.current_video_line.start
        )
        current_pos = Fraction(line_elapsed / view._state.current_video_line.duration)

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
    _GRID_LINE_WIDTH = Pixel(1)
    _MIN_SIZE = (Pixel(600), Pixel(200))
    _MAX_HEIGHT = Pixel(600)

    def __init__(self, state: _PlayState, colors: theme.PreviewPalette):
        super().__init__()
        self._state = state
        self.colors = colors
        self.setMinimumSize(*self._MIN_SIZE)
        self.setMaximumHeight(self._MAX_HEIGHT)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        with QtGui.QPainter(self) as painter:
            ctx = _LinePaintContext.new(self)
            self._draw_grid(painter, ctx)
            self._draw_notes(painter, ctx)
            self._draw_text(painter, ctx)
            self._draw_pointer(painter, ctx)

    def _draw_grid(self, painter: QtGui.QPainter, ctx: _LinePaintContext) -> None:
        painter.setPen(QtGui.QPen(self.colors.grid, self._GRID_LINE_WIDTH))
        for i in range(1, _PITCH_ROWS):
            y = ctx.notes_height - i * ctx.row_height
            painter.drawLine(0, y, ctx.total_width, y)

    def _draw_notes(self, painter: QtGui.QPainter, ctx: _LinePaintContext) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        for note in self._state.current_video_line.notes:
            painter.setBrush(self._brush_for_note(note, ctx))
            x = round(note.x_pos * ctx.total_width)
            net_row_height = ctx.row_height - self._GRID_LINE_WIDTH
            y = round(note.y_pos * ctx.notes_height) - net_row_height
            w = round(note.width * ctx.total_width)
            painter.drawRoundedRect(x, y, w, net_row_height, ctx.radius, ctx.radius)

    def _brush_for_note(self, note: _Note, ctx: _LinePaintContext) -> QtGui.QBrush:
        if ctx.current_pos > note.x_pos:
            if note.kind.is_golden():
                color = self.colors.active_golden_note
            else:
                color = self.colors.active_note
        else:
            if note.kind.is_golden():
                color = self.colors.golden_note
            else:
                color = self.colors.note
        if note.kind.has_pitch():
            style = Qt.BrushStyle.SolidPattern
        else:
            style = Qt.BrushStyle.Dense5Pattern
        return QtGui.QBrush(color, style)

    def _draw_text(self, painter: QtGui.QPainter, ctx: _LinePaintContext) -> None:
        font = painter.font()
        font.setPixelSize(ctx.text_height * 2 // 3)
        font_metrics = QtGui.QFontMetrics(font)
        # for simplicity's sake, don't take account for italicization
        text_width = font_metrics.horizontalAdvance(self._state.current_video_line.text)
        text_start = (ctx.total_width - text_width) // 2
        font.setItalic(True)
        italic_font_metrics = QtGui.QFontMetrics(font)
        for note in self._state.current_video_line.notes:
            font.setItalic(not note.kind.has_pitch())
            painter.setFont(font)
            active = ctx.current_pos > note.x_pos
            painter.setPen(self.colors.active_text if active else self.colors.text)
            painter.drawText(
                QtCore.QRect(text_start, ctx.notes_height, text_width, ctx.text_height),
                Qt.AlignmentFlag.AlignVCenter,
                note.text,
            )
            metrics = font_metrics if note.kind.has_pitch() else italic_font_metrics
            text_start += metrics.horizontalAdvance(note.text)

    def _draw_pointer(self, painter: QtGui.QPainter, ctx: _LinePaintContext) -> None:
        pointer_size = round(ctx.row_height * self._POINTER_SIZE_IN_ROWS)
        x = round(ctx.current_pos * ctx.total_width)
        current_pitch = next(
            (
                n
                for n in reversed(self._state.current_video_line.notes)
                if n.x_pos < ctx.current_pos
            ),
            self._state.current_video_line.notes[0],
        ).y_pos
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
    _tick_data: np.ndarray
    _stream: sounddevice.OutputStream | None = None
    _process: subprocess.Popen | None = None
    _CHANNELS = 2
    _STREAM_BUFFER_SIZE = Sample(2048)

    @classmethod
    def new(cls, source: Path, state: _PlayState) -> _AudioPlayer:
        data, _samplerate = soundfile.read(METRONOME_TICK_WAV, dtype="float32")
        player = cls(source=source, state=state, tick_data=data)
        player._start_ffmpeg(state.current_video_time)
        player._start_stream()
        return player

    def stop(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
        if self._process:
            self._process.terminate()
            self._process = None

    def seek_to(self, seconds: Seconds) -> None:
        self.stop()
        self._start_ffmpeg(seconds)
        self._start_stream()

    def _start_ffmpeg(self, start: Seconds = Seconds(0.0)) -> None:
        self._state.set_current_sample_from_secs(start)
        cmd = [
            "ffmpeg",
            "-ss",
            str(start),
            "-i",
            str(self._source),
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(_SAMPLE_RATE),
            "-ac",
            str(self._CHANNELS),
            "-",
        ]
        self._process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )

    def _start_stream(self) -> None:
        self._stream = sounddevice.OutputStream(
            samplerate=_SAMPLE_RATE,
            channels=self._CHANNELS,
            dtype="int16",
            blocksize=self._STREAM_BUFFER_SIZE,
            callback=self._stream_callback,
        )
        self._stream.start()

    def _stream_callback(
        self,
        outdata: np.ndarray,
        samples: Sample,
        time: Any,
        status: sounddevice.CallbackFlags,
    ) -> None:
        if (
            not (self._process and self._process.stdout and self._stream)
            or self._state.paused
        ):
            outdata[:] = np.zeros((samples, self._CHANNELS), dtype=np.int16)
            return
        bytes_needed = samples * self._CHANNELS * 2
        data = self._process.stdout.read(bytes_needed)
        if len(data) < bytes_needed:
            outdata[:] = np.zeros((samples, self._CHANNELS), dtype=np.int16)
            self._stream.stop()
            return
        array = np.frombuffer(data, dtype=np.int16).reshape(-1, self._CHANNELS)
        outdata[:] = self._mix_audio(array, samples)
        self._state.advance_current_sample(samples)

    def _mix_audio(self, data: np.ndarray, samples: Sample) -> np.ndarray:
        ticks = self._get_tick_start_and_data(samples)
        pitch = self._get_pitch_start_and_data(samples)
        if ticks is None and pitch is None and self._state.source_volume == 1.0:
            # nothing to mix; skip conversion
            return data
        data = data.astype(np.float32) / _INT16_MAX
        data *= self._state.source_volume
        if ticks is not None:
            tick_start, tick_data = ticks
            data[tick_start : tick_start + len(tick_data)] += tick_data
        if pitch is not None:
            pitch_start, pitch_data = pitch
            data[pitch_start : pitch_start + len(pitch_data)] += pitch_data
        return np.clip(data * _INT16_MAX, _INT16_MIN, _INT16_MAX).astype(np.int16)

    def _get_tick_start_and_data(
        self, samples: Sample
    ) -> tuple[Sample, np.ndarray] | None:
        if (note := self._state.current_audio_note) is None:
            return None
        if self._state.ticks_volume == 0.0:
            return None

        start_sample = self._state.current_sample
        end_sample = start_sample + samples
        tick_end = note.start_sample + len(self._tick_data)
        overlap_start = max(start_sample, note.start_sample)
        overlap_end = min(end_sample, tick_end)
        if overlap_start >= overlap_end:
            return None
        main_offset = Sample(overlap_start - start_sample)
        tick_offset = overlap_start - note.start_sample
        length = overlap_end - overlap_start

        data = self._tick_data[tick_offset : tick_offset + length]
        return main_offset, data * self._state.ticks_volume

    def _get_pitch_start_and_data(
        self, samples: Sample
    ) -> tuple[Sample, np.ndarray] | None:
        if (note := self._state.current_audio_note) is None:
            return None
        if self._state.pitch_volume == 0.0:
            return None
        if not note.kind.has_pitch():
            return None

        start_sample = self._state.current_sample
        end_sample = start_sample + samples
        overlap_start = max(start_sample, note.start_sample)
        overlap_end = min(end_sample, note.end_sample)
        if overlap_start >= overlap_end:
            return None
        main_offset = Sample(overlap_start - start_sample)
        pitch_offset = overlap_start - note.start_sample
        length = overlap_end - overlap_start

        data = _synth_note(
            note.freq, note.end_sample - note.start_sample, self._CHANNELS
        )[pitch_offset : pitch_offset + length]
        return main_offset, data * self._state.pitch_volume


def _percentage_to_amplitude_factor(value: int) -> float:
    """Given a percentage of volume, return the amplitude factor.

    - 0%   -> silence
    - 100% -> original
    - 200% -> double perceived loudness, i.e. +10dB
    """
    return 10 ** ((value / 100 - 1) / 2) if value > 0 else 0


def _ultrastar_to_midi_pitch(pitch: int) -> float:
    return pitch + 60


def _ultrastar_pitch_to_freq(pitch: int) -> float:
    # https://en.wikipedia.org/wiki/MIDI_tuning_standard
    return 440.0 * 2 ** ((_ultrastar_to_midi_pitch(pitch) - 69) / 12.0)


@functools.lru_cache(1)
def _synth_note(freq: float, samples: Sample, channels: int) -> np.ndarray:
    t = np.linspace(0, samples / _SAMPLE_RATE, samples, endpoint=False)
    waveform = _SYNTH_AMPLITUDE * np.sin(2 * np.pi * freq * t)
    envelope = _get_synth_envelope(samples)
    mono_wave = (waveform * envelope).astype(np.float32)
    return np.column_stack([mono_wave for _ in range(channels)])


def _get_synth_envelope(samples: Sample) -> np.ndarray:
    attack_samples = min(_SYNTH_ATTACK_SAMPLES, samples)
    release_samples = min(_SYNTH_RELEASE_SAMPLES, samples - attack_samples)
    sustain_samples = samples - (attack_samples + release_samples)
    attack = np.linspace(0, 1, attack_samples)
    sustain = np.ones(sustain_samples)
    release = np.linspace(1, 0, release_samples)
    return np.concatenate((attack, sustain, release))
