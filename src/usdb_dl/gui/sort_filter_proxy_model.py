"""Proxy model for sorting and filtering data of a source model."""

from PySide6.QtCore import (
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSortFilterProxyModel,
)

from usdb_dl.gui.table_model import CustomRole, TableSongMeta

QIndex = QModelIndex | QPersistentModelIndex


class SortFilterProxyModel(QSortFilterProxyModel):
    """Proxy model for sorting and filtering data of a source model."""

    def __init__(self, parent: QObject) -> None:
        self._text_filter: list[str] = []
        self._artist_filter = ""
        self._title_filter = ""
        self._language_filter = ""
        self._edition_filter = ""
        self._golden_notes_filter: bool | None = None
        self._rating_filter = (0, False)
        self._views_filter = 0
        super().__init__(parent)

    def set_text_filter(self, text: str) -> None:
        self._text_filter = text.lower().split()
        self.invalidate()

    def set_artist_filter(self, artist: str) -> None:
        self._artist_filter = artist
        self.invalidate()

    def set_title_filter(self, title: str) -> None:
        self._title_filter = title
        self.invalidate()

    def set_language_filter(self, language: str) -> None:
        self._language_filter = language
        self.invalidate()

    def set_edition_filter(self, edition: str) -> None:
        self._edition_filter = edition
        self.invalidate()

    def set_golden_notes_filter(self, golden_notes: bool | None) -> None:
        self._golden_notes_filter = golden_notes
        self.invalidate()

    def set_rating_filter(self, rating: int, exact: bool) -> None:
        self._rating_filter = (rating, exact)
        self.invalidate()

    def set_views_filter(self, min_views: int) -> None:
        self._views_filter = min_views
        self.invalidate()

    def filterAcceptsRow(self, source_row: int, source_parent: QIndex) -> bool:
        model = self.sourceModel()
        idx = model.index(source_row, 0, source_parent)
        song: TableSongMeta = model.data(idx, CustomRole.ALL_DATA)
        if self._artist_filter not in ("", song.data.artist):
            return False
        if self._title_filter not in ("", song.data.title):
            return False
        if self._language_filter not in ("", song.data.language):
            return False
        if self._edition_filter not in ("", song.data.edition):
            return False
        if self._golden_notes_filter not in (None, song.data.golden_notes):
            return False
        if (
            song.data.rating < self._rating_filter[0]
            or self._rating_filter[1]
            and song.data.rating > self._rating_filter[0]
        ):
            return False
        if song.data.views < self._views_filter:
            return False
        return all(w in song.searchable_text for w in self._text_filter)
