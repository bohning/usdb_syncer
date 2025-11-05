"""Dialog to manage USDB uploads."""

from __future__ import annotations

from typing import ClassVar

from PySide6.QtWidgets import QDialog, QWidget

from usdb_syncer import settings
from usdb_syncer.gui import progress, theme
from usdb_syncer.gui.forms.UsdbUploadDialog import Ui_Dialog
from usdb_syncer.gui.theme import generate_diff_css
from usdb_syncer.logger import song_logger
from usdb_syncer.usdb_scraper import submit_local_changes
from usdb_syncer.usdb_song import SongChanges, UsdbSong


def get_diff_css() -> str:
    current_theme = theme.Theme.from_settings()
    css = generate_diff_css(current_theme.diff_palette())
    return f"<style>{css}</style>"


class UsdbUploadDialog(Ui_Dialog, QDialog):
    """Dialog to manage USDB uploads."""

    _instance: ClassVar[UsdbUploadDialog | None] = None

    def __init__(
        self, parent: QWidget, songs: list[UsdbSong], song_changes: list[SongChanges]
    ) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self.resize(1200, 800)
        if ok_button := self.buttonBox.button(self.buttonBox.StandardButton.Ok):
            ok_button.setText("Submit")

        self.songs = songs
        self.song_changes = song_changes
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

        for song in self.songs:
            self.comboBox_songs.addItem(
                f"{song.song_id}: {song.artist} - {song.title} "
            )

    @classmethod
    def load(
        cls, parent: QWidget, songs: list[UsdbSong], song_changes: list[SongChanges]
    ) -> None:
        if cls._instance:
            cls._instance.songs = songs
            cls._instance.song_changes = song_changes
            cls._instance.raise_()
        else:
            cls._instance = cls(parent, songs, song_changes)
            cls._instance.show()

    def _on_song_changed(self, index: int) -> None:
        self._update_diff_view()

    def _update_diff_view(self) -> None:
        """Update the diff view based on current filter settings."""
        index = self.comboBox_songs.currentIndex()
        if index < 0:
            return

        song_change = self.song_changes[index]

        if self.checkBox_show_only_changes.isChecked():
            context = self.spinBox_context_lines.value()
            diff_remote, diff_local = song_change.builder.build_filtered_html(
                context, song_change.builder.changed_line_numbers
            )
        else:
            diff_remote, diff_local = song_change.builder.build_html()

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
            for song, changes in zip(self.songs, self.song_changes, strict=True):
                assert song.sync_meta is not None
                assert song.sync_meta.txt is not None
                assert song.sync_meta.txt.fname is not None
                submit_local_changes(
                    song.song_id,
                    song.sample_url,
                    changes.uploadable_str,
                    song.sync_meta.txt.fname,
                    song_logger(song.song_id),
                )

        num_songs = len(self.songs)
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
