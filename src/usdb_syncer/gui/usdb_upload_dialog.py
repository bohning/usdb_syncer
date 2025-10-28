"""Dialog to manage USDB uploads."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import IntEnum, auto
from html import escape
from typing import assert_never

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from usdb_syncer.gui import progress
from usdb_syncer.gui.forms.UsdbUploadDialog import Ui_Dialog
from usdb_syncer.gui.icons import Icon
from usdb_syncer.gui.resources import styles
from usdb_syncer.logger import song_logger
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.usdb_scraper import (
    get_notes,
    prepare_txt_for_upload,
    submit_local_changes,
)
from usdb_syncer.usdb_song import UsdbSong


class Column(IntEnum):
    """Table columns."""

    SONG_ID = 0
    ARTIST = auto()
    TITLE = auto()
    CHANGES = auto()
    DIFF = auto()
    SUBMIT = auto()

    def display_data(self) -> str:
        match self:
            case Column.SONG_ID:
                return "ID"
            case Column.ARTIST:
                return "Artist"
            case Column.TITLE:
                return "Title"
            case Column.CHANGES:
                return "Changes"
            case Column.DIFF:
                return "Diff"
            case Column.SUBMIT:
                return "Submit?"
            case _ as unreachable:
                assert_never(unreachable)

    def decoration_data(self) -> QIcon:
        match self:
            case Column.SONG_ID:
                icon = Icon.ID
            case Column.ARTIST:
                icon = Icon.ARTIST
            case Column.TITLE:
                icon = Icon.TITLE
            case Column.CHANGES:
                icon = Icon.CHANGES
            case Column.DIFF:
                icon = Icon.DIFF
            case Column.SUBMIT:
                icon = Icon.UPLOAD
            case _ as unreachable:
                assert_never(unreachable)
        return icon.icon()

    def fixed_size(self) -> int | None:
        match self:
            case Column.SONG_ID:
                return 60
            case Column.ARTIST | Column.TITLE:
                return None
            case Column.CHANGES:
                return 90
            case Column.DIFF:
                return 60
            case Column.SUBMIT:
                return 80
            case _ as unreachable:
                assert_never(unreachable)

    def stretch(self) -> bool:
        """Return whether the column should stretch to fill available space."""
        return self in (Column.ARTIST, Column.TITLE)


@dataclass
class SongChanges:
    """Information about changes between local and remote versions."""

    has_changes: bool
    change_str: str
    local_str: str | None = None
    remote_str: str | None = None

    @property
    def is_submittable(self) -> bool:
        """Check if the song can be submitted."""
        return (
            self.has_changes
            and self.local_str is not None
            and self.remote_str is not None
        )


def _html_prefix(action: str = "", symbol: str = " ") -> str:
    class_attr = f"line-prefix {action}".strip()
    return f'<td class="line-content"><span class="{class_attr}">{symbol}</span>'


def generate_diff_html(original: str, modified: str) -> str:
    """Generate GitHub-style unified diff HTML."""

    original_lines = original.splitlines()
    modified_lines = modified.splitlines()

    matcher = SequenceMatcher(None, original_lines, modified_lines)

    css = styles.DIFF_CSS.read_text(encoding="utf-8")
    html_parts = [f"<style>{css}</style>", '<div class="diff-container">']
    html_parts.append('<div class="diff-header">Remote File (USDB) → Local File</div>')
    html_parts.append('<table class="diff-table">')

    def add_diff_lines(
        lines: list[str], start: int, css_class: str, prefix_html: str
    ) -> None:
        for i, line in enumerate(lines):
            line_num = start + i + 1
            html_parts.append(
                f'<tr class="diff-line{f" {css_class}" if css_class else ""}">'
            )
            html_parts.append(f'<td class="line-number">{line_num}</td>')
            html_parts.append(f"{prefix_html}{escape(line)}</td>")
            html_parts.append("</tr>")

    prefix = _html_prefix()
    prefix_delete = _html_prefix("delete", "−")  # noqa: RUF001
    prefix_add = _html_prefix("add", "+")

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            add_diff_lines(original_lines[i1:i2], i1, "", prefix)
        elif tag == "delete":
            add_diff_lines(original_lines[i1:i2], i1, "deleted", prefix_delete)
        elif tag == "insert":
            add_diff_lines(modified_lines[j1:j2], j1, "added", prefix_add)
        elif tag == "replace":
            add_diff_lines(original_lines[i1:i2], i1, "deleted", prefix_delete)
            add_diff_lines(modified_lines[j1:j2], j1, "added", prefix_add)

    html_parts.append("</table></div>")
    return "".join(html_parts)


def count_line_changes(original: str, modified: str) -> tuple[int, int]:
    """
    Count line changes between two text blobs.

    Returns:
        Tuple of (insertions, deletions)
    """
    matcher = SequenceMatcher(None, original.splitlines(), modified.splitlines())

    insertions = deletions = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        match tag:
            case "insert":
                insertions += j2 - j1
            case "delete":
                deletions += i2 - i1
            case "replace":
                deletions += i2 - i1
                insertions += j2 - j1

    return insertions, deletions


def analyze_song_changes(song: UsdbSong) -> SongChanges:
    """Analyze changes between local and remote versions of a song."""
    if not song.is_local():
        return SongChanges(has_changes=False, change_str="not local")

    logger = song_logger(song.song_id)
    remote_txt = SongTxt.try_parse(get_notes(song.song_id, logger), logger)

    if remote_txt and remote_txt.notes.track_2:
        remote_txt.headers.title += " [DUET]"

    remote_str = str(remote_txt) if remote_txt else None

    if not remote_str:
        return SongChanges(has_changes=False, change_str="not remote")

    assert song.sync_meta is not None
    local_str = prepare_txt_for_upload(song.sync_meta, logger)

    if not local_str:
        return SongChanges(has_changes=False, change_str="invalid local")

    insertions, deletions = count_line_changes(remote_str, local_str)

    if insertions == 0 and deletions == 0:
        return SongChanges(
            has_changes=False,
            change_str="no changes",
            local_str=local_str,
            remote_str=remote_str,
        )

    return SongChanges(
        has_changes=True,
        change_str=f"+{insertions} | -{deletions}",
        local_str=local_str,
        remote_str=remote_str,
    )


class DiffPreviewDialog(QDialog):
    """Dialog to preview text differences."""

    def __init__(self, parent: QWidget, remote: str, local: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("Diff Preview")
        self.resize(1000, 600)

        view = QTextBrowser()
        view.setHtml(generate_diff_html(remote, local))

        layout = QVBoxLayout(self)
        layout.addWidget(view)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)


class UsdbUploadDialog(Ui_Dialog, QDialog):
    """Dialog to manage USDB uploads."""

    def __init__(self, parent: QWidget, songs: list[UsdbSong]) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self.resize(1000, 600)

        self.songs = songs
        self.song_changes: list[SongChanges] = []
        self.selected = [False] * len(songs)

        self._setup_table()
        self._populate_table()

        self.checkBox_submittable_only.stateChanged.connect(self._update_row_visibility)
        self._update_row_visibility()

    def _setup_table(self) -> None:
        """Configure table properties and headers."""
        self.table.setColumnCount(len(Column))
        self.table.setRowCount(len(self.songs))

        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(60)
        self.table.setSortingEnabled(True)

        for col in Column:
            item = QTableWidgetItem(col.decoration_data(), col.display_data())
            self.table.setHorizontalHeaderItem(col, item)

            if (size := col.fixed_size()) is not None:
                self.table.setColumnWidth(col, size)
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            elif col.stretch():
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(
                    col, QHeaderView.ResizeMode.ResizeToContents
                )

    def _populate_table(self) -> None:
        """Populate table with song data."""
        for row, song in enumerate(self.songs):
            changes = analyze_song_changes(song)
            self.song_changes.append(changes)

            self.table.setItem(row, Column.SONG_ID, QTableWidgetItem(str(song.song_id)))
            self.table.setItem(row, Column.ARTIST, QTableWidgetItem(song.artist))
            self.table.setItem(row, Column.TITLE, QTableWidgetItem(song.title))
            self.table.setItem(
                row, Column.CHANGES, QTableWidgetItem(changes.change_str)
            )

            if changes.is_submittable:
                self.selected[row] = True
                self._add_diff_button(row, changes)
                self._add_submit_checkbox(row)

    def _add_diff_button(self, row: int, changes: SongChanges) -> None:
        """Add diff preview button for a row."""
        btn = QPushButton("Diff")
        btn.clicked.connect(
            lambda: self._show_diff(changes.remote_str, changes.local_str)
        )
        self.table.setCellWidget(row, Column.DIFF, btn)

    def _add_submit_checkbox(self, row: int) -> None:
        """Add submit checkbox for a row."""
        checkbox = QCheckBox()
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(
            lambda state, r=row: self._update_selection(r, state)
        )

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        self.table.setCellWidget(row, Column.SUBMIT, container)

    def _update_row_visibility(self) -> None:
        """Update which rows are visible based on filter."""
        submittable_only = self.checkBox_submittable_only.isChecked()

        for row, changes in enumerate(self.song_changes):
            self.table.setRowHidden(
                row, submittable_only and not changes.is_submittable
            )

    def _update_selection(self, row: int, state: int) -> None:
        """Update selection state for a row."""
        self.selected[row] = state == Qt.CheckState.Checked.value

    def _show_diff(self, remote: str | None, local: str | None) -> None:
        """Show diff preview dialog."""
        if remote and local:
            DiffPreviewDialog(self, remote, local).exec()

    @property
    def selected_songs(self) -> list[UsdbSong]:
        """Return list of selected songs."""
        return [song for i, song in enumerate(self.songs) if self.selected[i]]

    def accept(self) -> None:
        """Submit selected songs and close dialog."""

        def task() -> None:
            for song in self.selected_songs:
                submit_local_changes(song)

        def on_done(result: progress.Result) -> None:
            pass

        num_songs = len(self.selected_songs)
        plural = "s" if num_songs != 1 else ""
        progress.run_with_progress(
            f"Submitting {num_songs} song{plural}…", task, on_done
        )
        super().accept()

    def reject(self) -> None:
        """Close dialog without submitting."""
        super().reject()
