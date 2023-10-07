"""Controller for the filter tree."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from usdb_syncer.song_data import SongData

from .item import Filter, FilterItem, RootItem, VariantItem
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
