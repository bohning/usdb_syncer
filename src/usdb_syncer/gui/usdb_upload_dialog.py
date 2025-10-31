"""Dialog to manage USDB uploads."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QWidget

from usdb_syncer.gui import progress, theme
from usdb_syncer.gui.forms.UsdbUploadDialog import Ui_Dialog
from usdb_syncer.gui.resources import styles
from usdb_syncer.gui.theme import DiffPalette, _rgb_str
from usdb_syncer.logger import song_logger
from usdb_syncer.usdb_scraper import submit_local_changes
from usdb_syncer.usdb_song import SongChanges, UsdbSong


def _html_prefix(action: str = "", symbol: str = " ") -> str:
    class_attr = f"line-prefix {action}".strip()
    return f'<td class="line-content"><span class="{class_attr}">{symbol}</span>'


def get_diff_css() -> str:
    current_theme = theme.Theme.from_settings()
    css = generate_diff_css(current_theme.diff_palette())
    return f"<style>{css}</style>"


def generate_diff_css(palette: DiffPalette) -> str:
    """Generate diff CSS from theme palette."""

    return styles.DIFF_CSS.read_text(encoding="utf-8").format(
        lineno_text=_rgb_str(palette.lineno_text),
        lineno_border=_rgb_str(palette.lineno_border),
        equal_bg=_rgb_str(palette.equal_bg),
        equal_text=_rgb_str(palette.equal_text),
        add_bg=_rgb_str(palette.add_bg),
        add_text=_rgb_str(palette.add_text),
        del_bg=_rgb_str(palette.del_bg),
        del_text=_rgb_str(palette.del_text),
        add_inline_bg=_rgb_str(palette.add_inline_bg),
        add_inline_text=_rgb_str(palette.add_inline_text),
        del_inline_bg=_rgb_str(palette.del_inline_bg),
        del_inline_text=_rgb_str(palette.del_inline_text),
        empty_bg=_rgb_str(palette.empty_bg),
    )


class UsdbUploadDialog(Ui_Dialog, QDialog):
    """Dialog to manage USDB uploads."""

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

        self.comboBox_songs.currentIndexChanged.connect(self._on_song_changed)
        self.textBrowser_diff_remote.verticalScrollBar().valueChanged.connect(
            lambda v: self.textBrowser_diff_local.verticalScrollBar().setValue(v)
        )
        self.textBrowser_diff_local.verticalScrollBar().valueChanged.connect(
            lambda v: self.textBrowser_diff_remote.verticalScrollBar().setValue(v)
        )

        for song in self.songs:
            self.comboBox_songs.addItem(
                f"{song.song_id}: {song.artist} - {song.title} "
            )

    def _on_song_changed(self, index: int) -> None:
        css_block = get_diff_css()

        def html_template(body: str) -> str:
            return f"<html><head>{css_block}</head><body>{body}</body></html>"

        diff_remote = html_template(self.song_changes[index].diff_remote)
        diff_local = html_template(self.song_changes[index].diff_local)
        self.textBrowser_diff_remote.setHtml(diff_remote)
        self.textBrowser_diff_local.setHtml(diff_local)

    def accept(self) -> None:
        """Submit selected songs and close dialog."""

        def task() -> None:
            for song, changes in zip(self.songs, self.song_changes, strict=True):
                assert song.sync_meta is not None
                assert song.sync_meta.txt is not None
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
        super().accept()

    def reject(self) -> None:
        """Close dialog without submitting."""
        super().reject()
