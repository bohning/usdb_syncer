"""Controller for the filter tree."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Callable, Iterable

from PySide6.QtCore import QModelIndex, Qt

from usdb_syncer.gui.utils import keyboard_modifiers
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
from .model import TreeModel, TreeProxyModel

if TYPE_CHECKING:
    from usdb_syncer.gui.mw import MainWindow


class FilterTree:
    """Controller for the filter tree."""

    def __init__(self, mw: MainWindow) -> None:
        self.mw = mw
        self.view = mw.search_view
        self._build_tree()
        self._model = TreeModel(mw, self.root)
        self._proxy_model = TreeProxyModel(self.view, self._model)
        self.view.setHeaderHidden(True)
        self.view.setModel(self._proxy_model)
        self.view.clicked.connect(self._on_click)
        mw.line_edit_search_filters.textChanged.connect(self._proxy_model.set_filter)

    def _build_tree(self) -> None:
        self.root = RootItem()
        for filt in Filter:
            item = FilterItem(data=filt, parent=self.root)
            self.root.add_child(item)
            item.set_children(
                VariantItem(data=variant, parent=item)
                for variant in filt.static_variants()
            )

    def _on_click(self, index: QModelIndex) -> None:
        item = self._model.item_for_index(self._proxy_model.mapToSource(index))
        for changed in item.toggle_checked(keyboard_modifiers().ctrl):
            idx = self._model.index_for_item(changed)
            self._model.dataChanged.emit(idx, idx, [Qt.ItemDataRole.CheckStateRole])

    def accepts_song(self, song: SongData) -> bool:
        return all(filt.accepts_song(song) for filt in self.root.children)

    def connect_filter_changed(self, func: Callable[[], None]) -> None:
        self._model.dataChanged.connect(func)

    def set_artists(self, artists: Iterable[str]) -> None:
        self._set_variants(
            Filter.ARTIST,
            (SongArtistMatch(a, c) for a, c in sorted(Counter(artists).items())),
        )

    def set_titles(self, titles: Iterable[str]) -> None:
        self._set_variants(
            Filter.TITLE,
            (SongTitleMatch(t, c) for t, c in sorted(Counter(titles).items())),
        )

    def set_editions(self, editions: Iterable[str]) -> None:
        self._set_variants(
            Filter.EDITION,
            (SongEditionMatch(e, c) for e, c in sorted(Counter(editions).items())),
        )

    def set_languages(self, languages: Iterable[str]) -> None:
        self._set_variants(
            Filter.LANGUAGE,
            (SongLanguageMatch(l, c) for l, c in sorted(Counter(languages).items())),
        )

    def _set_variants(self, filt: Filter, variants: Iterable[SongMatch]) -> None:
        self._model.beginResetModel()
        item = self.root.children[filt.value]
        item.set_children(VariantItem(data=var, parent=item) for var in variants)
        self._model.dataChanged.emit(self.root, self.root)
        self._model.endResetModel()
