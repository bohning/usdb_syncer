"""Dialog to manage USDB uploads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from PySide6.QtGui import Qt
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from usdb_syncer import settings
from usdb_syncer.gui import progress, theme
from usdb_syncer.gui.forms.UsdbUploadDialog import Ui_Dialog
from usdb_syncer.gui.theme import generate_diff_css
from usdb_syncer.logger import song_logger
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.usdb_scraper import get_notes, submit_local_changes
from usdb_syncer.usdb_song import DownloadStatus, SongChanges, UsdbSong


@dataclass
class ValidationSuccess:
    changes: SongChanges


@dataclass
class ValidationFailure:
    reason: str


def get_diff_css() -> str:
    current_theme = theme.Theme.from_settings()
    css = generate_diff_css(current_theme.diff_palette())
    return f"<style>{css}</style>"


class UsdbUploadDialog(Ui_Dialog, QDialog):
    """Dialog to manage USDB uploads."""

    _instance: ClassVar[UsdbUploadDialog | None] = None

    def __init__(
        self, parent: QWidget | None, submittable: list[tuple[UsdbSong, SongChanges]]
    ) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self.resize(1200, 800)
        if ok_button := self.buttonBox.button(self.buttonBox.StandardButton.Ok):
            ok_button.setText("Submit")

        self.submittable = submittable
        self._load_settings()

        self.comboBox_songs.currentIndexChanged.connect(self._on_song_changed)
        self.textBrowser_diff_remote.verticalScrollBar().valueChanged.connect(
            lambda v: self.textBrowser_diff_local.verticalScrollBar().setValue(v)
        )
        self.textBrowser_diff_local.verticalScrollBar().valueChanged.connect(
            lambda v: self.textBrowser_diff_remote.verticalScrollBar().setValue(v)
        )
        self.checkBox_show_only_changes.stateChanged.connect(self._update_diff_view)
        self.spinBox_context_lines.valueChanged.connect(self._update_diff_view)
        self.checkBox_show_only_changes.stateChanged.connect(
            lambda: self.spinBox_context_lines.setEnabled(
                self.checkBox_show_only_changes.isChecked()
            )
        )

        for song, _ in self.submittable:
            self.comboBox_songs.addItem(f"{song.song_id}: {song.artist_title_str()}")

    @classmethod
    def load(
        cls, parent: QWidget, submittable: list[tuple[UsdbSong, SongChanges]]
    ) -> None:
        if cls._instance:
            cls._instance.submittable = submittable
            cls._instance.raise_()
        else:
            cls._instance = cls(parent, submittable)
            cls._instance.show()

    def _on_song_changed(self) -> None:
        self._update_diff_view()

    def _update_diff_view(self) -> None:
        """Update the diff view based on current filter settings."""
        index = self.comboBox_songs.currentIndex()
        if index < 0:
            return

        _, changes = self.submittable[index]

        if self.checkBox_show_only_changes.isChecked():
            context = self.spinBox_context_lines.value()
            diff_remote, diff_local = changes.builder.build_filtered_html(
                context, changes.builder.changed_line_numbers
            )
        else:
            diff_remote, diff_local = changes.builder.build_html()

        css_block = get_diff_css()

        def html_template(body: str) -> str:
            return f"<html><head>{css_block}</head><body>{body}</body></html>"

        self.textBrowser_diff_remote.setHtml(html_template(diff_remote))
        self.textBrowser_diff_local.setHtml(html_template(diff_local))

    def _load_settings(self) -> None:
        self.checkBox_show_only_changes.setChecked(settings.get_diff_only_changes())
        self.spinBox_context_lines.setValue(settings.get_diff_context_lines())

    def _save_settings(self) -> None:
        settings.set_diff_only_changes(self.checkBox_show_only_changes.isChecked())
        settings.set_diff_context_lines(self.spinBox_context_lines.value())

    def accept(self) -> None:
        """Submit selected songs and close dialog."""

        def task() -> None:
            for song, changes in self.submittable:
                assert song.sync_meta is not None
                assert song.sync_meta.txt is not None
                assert song.sync_meta.txt.file is not None
                assert song.sync_meta.txt.file.fname is not None
                submit_local_changes(
                    song.song_id,
                    song.sample_url,
                    changes.uploadable_str,
                    song.sync_meta.txt.file.fname,
                    song_logger(song.song_id),
                )

        num_songs = len(self.submittable)
        plural = "s" if num_songs != 1 else ""
        progress.run_with_progress(f"Submitting {num_songs} song{plural}…", task)
        UsdbUploadDialog._instance = None
        self._save_settings()
        super().accept()

    def reject(self) -> None:
        """Close dialog without submitting."""
        self._save_settings()
        UsdbUploadDialog._instance = None
        super().reject()


def submit_or_reject_selected(parent: QWidget, selected: list[UsdbSong]) -> None:
    submittable: list[tuple[UsdbSong, SongChanges]] = []
    rejected: list[tuple[UsdbSong, str]] = []

    for song in selected:
        match _validate_song_for_submission(song):
            case ValidationSuccess(changes):
                submittable.append((song, changes))
            case ValidationFailure(reason):
                rejected.append((song, reason))

    if rejected:
        _show_rejection_message(parent, rejected)

    if submittable:
        UsdbUploadDialog(parent, submittable).show()


def _validate_song_for_submission(
    song: UsdbSong,
) -> ValidationFailure | ValidationSuccess:
    logger = song_logger(song.song_id)

    remote_str = get_notes(song.song_id, logger)
    if not remote_str:
        logger.info("Cannot submit: song is not remote.")
        return ValidationFailure("not remote")

    remote_txt = SongTxt.try_parse(remote_str, logger)
    if not remote_txt:
        logger.info("Cannot submit: remote song parsing failed.")
        return ValidationFailure("remote parsing failed")

    sync_meta = song.sync_meta
    if not sync_meta or not sync_meta.path.exists():
        logger.info("Cannot submit: song is not local.")
        return ValidationFailure("not local")

    if song.status is not DownloadStatus.SYNCHRONIZED:
        logger.info("Cannot submit: song is not synchronized.")
        return ValidationFailure("not synchronized")

    song_changes = song.get_changes(remote_txt)
    if not song_changes or not song_changes.has_changes():
        logger.info("Cannot submit: song has no local changes.")
        return ValidationFailure("no local changes")

    return ValidationSuccess(song_changes)


def _show_rejection_message(
    parent: QWidget, rejected_songs: list[tuple[UsdbSong, str]]
) -> None:
    """Show a message listing why songs cannot be submitted."""
    if not rejected_songs:
        return

    if len(rejected_songs) == 1:
        song, reason = rejected_songs[0]
        html = (
            f"<p>The song <b>{song.song_id}: {song.artist_title_str()}</b> cannot "
            f"be submitted:</p><p style='color: #888;'>{reason}</p>"
        )
    else:
        rows = []
        for song, reason in rejected_songs:
            rows.append(
                f"<tr>"
                f"<td style='padding-right: 10px;'><b>{song.song_id}</b></td>"
                f"<td style='padding-right: 10px;'>{song.artist_title_str()}</td>"
                f"<td style='color: #888;'>{reason}</td>"
                f"</tr>"
            )

        html = (
            "<p>The following songs cannot be submitted:</p>"
            "<table cellspacing='0' cellpadding='5'>" + "".join(rows) + "</table>"
        )

    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setWindowTitle("Not Submittable")
    msg_box.setTextFormat(Qt.TextFormat.RichText)
    msg_box.setText(html)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.resize(msg_box.sizeHint())

    msg_box.exec()
