"""Dialog to manage USDB uploads."""

from __future__ import annotations

import functools
from dataclasses import dataclass
from html import escape

from diff_match_patch import diff_match_patch
from PySide6.QtWidgets import QDialog, QWidget

from usdb_syncer.gui import progress
from usdb_syncer.gui.forms.UsdbUploadDialog import Ui_Dialog
from usdb_syncer.gui.resources import styles
from usdb_syncer.logger import song_logger
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.usdb_scraper import get_notes, submit_local_changes
from usdb_syncer.usdb_song import UsdbSong


@dataclass
class SongChanges:
    """Information about changes between local and remote versions."""

    uploadable_str: str
    diff_remote: str
    diff_local: str


def _html_prefix(action: str = "", symbol: str = " ") -> str:
    class_attr = f"line-prefix {action}".strip()
    return f'<td class="line-content"><span class="{class_attr}">{symbol}</span>'


def generate_diffs(remote: str, local: str) -> tuple[str, str]:
    """Generate a side-by-side HTML diff with per-character highlights."""

    dmp = diff_match_patch()
    diffs = dmp.diff_main(remote, local)
    dmp.diff_cleanupSemantic(diffs)

    remote_lines: list[str] = []
    local_lines: list[str] = []

    line_num_remote = 1
    line_num_local = 1

    def render_inline_diff(chunk: str, op: int) -> str:
        """Render inline character-level differences."""
        if not chunk:
            return ""
        text = escape(chunk).replace(" ", "&nbsp;")
        if op == -1:  # deletion (only left side)
            return f"<span class='del-inline'>{text}</span>"
        elif op == 1:  # insertion (only right side)
            return f"<span class='add-inline'>{text}</span>"
        return text

    # Process diffs and build line-by-line representation
    left_line = ""
    right_line = ""
    left_has_change = False
    right_has_change = False

    def flush_lines() -> None:
        """Output the current line buffers to both sides."""
        nonlocal line_num_remote, line_num_local, left_line, right_line
        nonlocal left_has_change, right_has_change

        # Determine if we need to output lines
        has_left = len(left_line) > 0
        has_right = len(right_line) > 0

        if has_left:
            line_class = "del" if left_has_change else "equal"
            remote_lines.append(
                f"<tr><td class='lineno'>{line_num_remote}</td>"
                f"<td class='line {line_class}'>{left_line}</td></tr>"
            )
            line_num_remote += 1
        elif has_right:
            # Right has content but left doesn't - add empty line on left
            remote_lines.append(
                "<tr><td class='lineno'>&nbsp;</td>"
                "<td class='line empty'>&nbsp;</td></tr>"
            )

        if has_right:
            line_class = "add" if right_has_change else "equal"
            local_lines.append(
                f"<tr><td class='lineno'>{line_num_local}</td>"
                f"<td class='line {line_class}'>{right_line}</td></tr>"
            )
            line_num_local += 1
        elif has_left:
            # Left has content but right doesn't - add empty line on right
            local_lines.append(
                "<tr><td class='lineno'>&nbsp;</td>"
                "<td class='line empty'>&nbsp;</td></tr>"
            )

        # Reset for next line
        left_line = ""
        right_line = ""
        left_has_change = False
        right_has_change = False

    for op, data in diffs:
        # Split by newlines but keep track of them
        parts = data.split("\r\n")

        for i, part in enumerate(parts):
            if op == 0:  # Equal content on both sides
                left_line += render_inline_diff(part, 0)
                right_line += render_inline_diff(part, 0)
            elif op == -1:  # Deletion (only on left)
                left_line += render_inline_diff(part, op)
                left_has_change = True
            elif op == 1:  # Addition (only on right)
                right_line += render_inline_diff(part, op)
                right_has_change = True

            # If this isn't the last part, we encountered a newline
            if i < len(parts) - 1:
                flush_lines()

    # Flush any remaining content
    if left_line or right_line:
        flush_lines()

    html_remote = "<table class='diff-table'>" + "".join(remote_lines) + "</table>"
    html_local = "<table class='diff-table'>" + "".join(local_lines) + "</table>"
    return html_remote, html_local


def analyze_song_changes(song: UsdbSong) -> SongChanges | None:
    """Analyze changes between local and remote versions of a song."""

    logger = song_logger(song.song_id)

    # Get latest song txt from USDB
    if not (remote_str := get_notes(song.song_id, logger)):
        logger.warning("Failed to fetch remote song txt, skipping upload.")
        return None
    if not (remote_txt := SongTxt.try_parse(remote_str, logger)):
        logger.warning("Failed to parse remote song txt, skipping upload.")
        return None
    remote_str = remote_txt.str_for_upload(remote_txt.meta_tags, remote_txt.headers)

    # Read local song file and get uploadable string
    if not (sync_meta := song.sync_meta):
        logger.warning("Song is not local, skipping upload.")
        return None
    if not (txt_path := sync_meta.txt_path()):
        logger.warning("Song has no local txt path, skipping upload.")
        return None
    if not (txt_path.is_file()):
        logger.warning("Song has no local txt file, skipping upload.")
        return None
    if not (local_txt := SongTxt.try_from_file(txt_path, logger)):
        logger.warning("Failed to parse local song txt, skipping upload.")
        return None
    local_str = local_txt.str_for_upload(sync_meta.meta_tags, remote_txt.headers)

    diff_remote, diff_local = generate_diffs(remote_str, local_str)

    # --- Load and embed CSS from package resource ---
    css = styles.DIFF_CSS.read_text(encoding="utf-8")
    css_block = f"<style>{css}</style>"

    # --- Wrap HTML ---
    def html_template(body: str) -> str:
        return f"<html><head>{css_block}</head><body>{body}</body></html>"

    diff_remote = html_template(diff_remote)
    diff_local = html_template(diff_local)

    if diff_remote == diff_local:
        logger.warning("No changes, skipping upload.")
        return None

    return SongChanges(local_str, diff_remote, diff_local)


@functools.lru_cache
def get_diff_css() -> str:
    return f"<style>{styles.DIFF_CSS.read_text(encoding='utf-8')}</style>"


class UsdbUploadDialog(Ui_Dialog, QDialog):
    """Dialog to manage USDB uploads."""

    def __init__(self, parent: QWidget, songs: list[UsdbSong]) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self.resize(1200, 800)
        if ok_button := self.buttonBox.button(self.buttonBox.StandardButton.Ok):
            ok_button.setText("Submit")

        self.songs = songs
        self.submittable_songs: list[UsdbSong] = []
        self.song_changes: list[SongChanges] = []

        self.comboBox_songs.currentIndexChanged.connect(self._on_song_changed)
        # Scroll sync
        self.textBrowser_diff_remote.verticalScrollBar().valueChanged.connect(
            lambda v: self.textBrowser_diff_local.verticalScrollBar().setValue(v)
        )
        self.textBrowser_diff_local.verticalScrollBar().valueChanged.connect(
            lambda v: self.textBrowser_diff_remote.verticalScrollBar().setValue(v)
        )

        for song in songs:
            if song_changes := analyze_song_changes(song):
                self.song_changes.append(song_changes)
                self.submittable_songs.append(song)

                self.comboBox_songs.addItem(
                    f"{song.song_id}: {song.artist} - {song.title} "
                )

    def _on_song_changed(self, index: int) -> None:
        self.textBrowser_diff_remote.setHtml(self.song_changes[index].diff_remote)
        self.textBrowser_diff_local.setHtml(self.song_changes[index].diff_local)

    def accept(self) -> None:
        """Submit selected songs and close dialog."""

        def task() -> None:
            for song, changes in zip(
                self.submittable_songs, self.song_changes, strict=True
            ):
                assert song.sync_meta is not None
                assert song.sync_meta.txt is not None
                submit_local_changes(
                    song.song_id,
                    song.sample_url,
                    changes.uploadable_str,
                    song.sync_meta.txt.fname,
                    song_logger(song.song_id),
                )

        num_songs = len(self.submittable_songs)
        plural = "s" if num_songs != 1 else ""
        progress.run_with_progress(f"Submitting {num_songs} song{plural}…", task)
        super().accept()

    def reject(self) -> None:
        """Close dialog without submitting."""
        super().reject()
