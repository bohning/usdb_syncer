"""Controller for the filter tree."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterable

from PySide6.QtCore import Qt

from usdb_syncer.song_data import SongData

from .item import (
    Filter,
    FilterItem,
    RootItem,
    SongArtistMatch,
    SongEditionMatch,
    SongLanguageMatch,
    SongMatch,
    SongTitleMatch,
    VariantItem,
)
from .model import TreeModel

if TYPE_CHECKING:
    from usdb_syncer.gui.mw import MainWindow


class FilterTree:
    """Controller for the filter tree."""

    def __init__(self, mw: MainWindow) -> None:
        self.mw = mw
        self.view = mw.search_view
        self._build_tree()
        self._model = TreeModel(mw, self.root)
        self.view.setHeaderHidden(True)
        self.view.setModel(self._model)
        self.view.clicked.connect(
            lambda idx: self._model.setData(idx, None, Qt.ItemDataRole.CheckStateRole)
        )

    def _build_tree(self) -> None:
        self.root = RootItem()
        for filt in Filter:
            item = FilterItem(data=filt, parent=self.root)
            self.root.add_child(item)
            for variant in filt.static_variants():
                item.add_child(VariantItem(data=variant, parent=item))

    def accepts_song(self, song: SongData) -> bool:
        return all(filt.accepts_song(song) for filt in self.root.children)

    def connect_filter_changed(self, func: Callable[[], None]) -> None:
        self._model.dataChanged.connect(func)

    def set_artists(self, artists: Iterable[str]) -> None:
        self._set_variants(Filter.ARTIST, (SongArtistMatch(a) for a in artists))

    def set_titles(self, titles: Iterable[str]) -> None:
        self._set_variants(Filter.TITLE, (SongTitleMatch(a) for a in titles))

    def set_editions(self, editions: Iterable[str]) -> None:
        self._set_variants(Filter.EDITION, (SongEditionMatch(a) for a in editions))

    def set_languages(self, languages: Iterable[str]) -> None:
        self._set_variants(Filter.LANGUAGE, (SongLanguageMatch(a) for a in languages))

    def _set_variants(self, filt: Filter, variants: Iterable[SongMatch]) -> None:
        item = self.root.children[filt.value]
        for variant in variants:
            item.add_child(VariantItem(data=variant, parent=item))
        self._model.dataChanged.emit(self.root, self.root)
