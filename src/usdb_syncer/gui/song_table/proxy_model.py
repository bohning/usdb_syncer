"""Proxy model for sorting and filtering data of a source model."""

from typing import Iterable, Iterator

from PySide6.QtCore import (
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    QTimer,
)

from usdb_syncer.gui.song_table.table_model import CustomRole
from usdb_syncer.song_data import SongData, fuzz_text

QIndex = QModelIndex | QPersistentModelIndex


class ProxyModel(QSortFilterProxyModel):
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

        self._filter_invalidation_timer = QTimer(parent)
        self._filter_invalidation_timer.setSingleShot(True)
        self._filter_invalidation_timer.setInterval(200)
        self._filter_invalidation_timer.timeout.connect(  # type:ignore
            self.invalidateRowsFilter
        )

        super().__init__(parent)

    def source_rows(self, subset: list[QModelIndex] | None = None) -> list[int]:
        """Returns the source rows of the provided or all rows in the model."""
        indices = subset or (self.index(row, 0) for row in range(self.rowCount()))
        return [row for idx in indices if (row := self.mapToSource(idx).row()) != -1]

    def target_indices(self, sources: Iterable[QModelIndex]) -> Iterator[QModelIndex]:
        return (self.mapFromSource(idx) for idx in sources)

    def set_text_filter(self, text: str) -> None:
        self._text_filter = fuzz_text(text).split()
        self._filter_invalidation_timer.start()

    def set_artist_filter(self, artist: str) -> None:
        self._artist_filter = artist
        self._filter_invalidation_timer.start()

    def set_title_filter(self, title: str) -> None:
        self._title_filter = title
        self._filter_invalidation_timer.start()

    def set_language_filter(self, language: str) -> None:
        self._language_filter = language
        self._filter_invalidation_timer.start()

    def set_edition_filter(self, edition: str) -> None:
        self._edition_filter = edition
        self._filter_invalidation_timer.start()

    def set_golden_notes_filter(self, golden_notes: bool | None) -> None:
        self._golden_notes_filter = golden_notes
        self._filter_invalidation_timer.start()

    def set_rating_filter(self, rating: int, exact: bool) -> None:
        self._rating_filter = (rating, exact)
        self._filter_invalidation_timer.start()

    def set_views_filter(self, min_views: int) -> None:
        self._views_filter = min_views
        self._filter_invalidation_timer.start()

    def filterAcceptsRow(self, source_row: int, source_parent: QIndex) -> bool:
        model = self.sourceModel()
        idx = model.index(source_row, 0, source_parent)
        return self._filter_accepts_song(model.data(idx, CustomRole.ALL_DATA))

    def _filter_accepts_song(self, song: SongData) -> bool:
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
        return all(word in song.fuzzy_text for word in self._text_filter)
