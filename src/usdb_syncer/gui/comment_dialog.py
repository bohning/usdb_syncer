"""Dialog to post a comment on one or multiple songs."""

from PySide6.QtWidgets import QDialog, QWidget

from usdb_syncer.gui.forms.CommentDialog import Ui_Dialog
from usdb_syncer.usdb_scraper import post_song_comment
from usdb_syncer.usdb_song import UsdbSong


class CommentDialog(Ui_Dialog, QDialog):
    """Dialog to post a comment on one or multiple songs."""

    def __init__(self, parent: QWidget, selected_song: UsdbSong) -> None:
        super().__init__(parent=parent)
        self._parent = parent
        self.setupUi(self)
        self._selected_song = selected_song
        self.combobox_rating.addItem("Neutral", "neutral")
        self.combobox_rating.addItem("Positive", "positiv")
        self.combobox_rating.addItem("Negative", "negativ")

    def accept(self) -> None:
        song_id = self._selected_song.song_id
        text = self.text_edit_comment.toPlainText()
        rating = self.combobox_rating.currentData()
        post_song_comment(song_id, text, rating)
        super().accept()
