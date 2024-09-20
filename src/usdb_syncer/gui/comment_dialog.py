"""Dialog to post a comment on one or multiple songs."""

from PySide6.QtWidgets import QDialog, QWidget

from usdb_syncer.gui.forms.CommentDialog import Ui_Dialog
from usdb_syncer.usdb_scraper import RequestMethod, get_usdb_page
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
        payload = {
            "text": self.text_edit_comment.toPlainText(),
            "stars": self.combobox_rating.currentData(),
        }

        get_usdb_page(
            "index.php",
            RequestMethod.POST,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            params={
                "link": "detail",
                "id": str(int(self._selected_song.song_id)),
                "comment": str(1),
            },
            payload=payload,
        )
        super().accept()
