"""Proxy model for sorting and filtering data of a source model."""

from PySide6.QtCore import (
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    QTimer,
)

from usdb_syncer.gui.song_table.table_model import CustomRole
from usdb_syncer.notes_parser import SongTxt
from usdb_syncer.song_data import SongData, fuzz_text

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

        self._filter_invalidation_timer = QTimer(parent)
        self._filter_invalidation_timer.setSingleShot(True)
        self._filter_invalidation_timer.setInterval(200)
        self._filter_invalidation_timer.timeout.connect(  # type:ignore
            self.invalidateRowsFilter
        )

        super().__init__(parent)

    def find_rows_for_song_txts(
        self, song_txts: list[SongTxt]
    ) -> tuple[list[QModelIndex], ...]:
        comparer = FuzzyComparer(song_txts)
        model = self.sourceModel()
        for row in range(self.rowCount()):
            index = self.index(row, 0)
            data: SongData = model.data(self.mapToSource(index), CustomRole.ALL_DATA)
            comparer.check(data, index)
        return comparer.results

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
        song: SongData = model.data(idx, CustomRole.ALL_DATA)
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


class FuzzyComparer:
    """Helper to find rows matching txts."""

    results: tuple[list[QModelIndex], ...]

    def __init__(self, song_txts: list[SongTxt]) -> None:
        self._len = len(song_txts)
        self.artists = tuple(fuzz_text(txt.headers.artist) for txt in song_txts)
        self.titles = tuple(fuzz_text(txt.headers.title) for txt in song_txts)
        self.results = tuple([] for _ in range(self._len))

    def check(self, data: SongData, index: QModelIndex) -> None:
        for idx in range(self._len):
            if (
                data.fuzzy_text.artist == self.artists[idx]
                and data.fuzzy_text.title == self.titles[idx]
            ):
                self.results[idx].append(index)
