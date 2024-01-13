"""Controller for the filter tree."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QModelIndex, Qt

from usdb_syncer import db, events
from usdb_syncer.gui.utils import keyboard_modifiers

from .item import Filter, FilterItem, RootItem, VariantItem
from .model import TreeModel, TreeProxyModel

if TYPE_CHECKING:
    from usdb_syncer.gui.mw import MainWindow


class FilterTree:
    """Controller for the filter tree."""

    def __init__(self, mw: MainWindow) -> None:
        self.mw = mw
        self.view = mw.search_view
        self.root = RootItem()
        self.root.set_children(FilterItem(data=f, parent=self.root) for f in Filter)
        self._model = TreeModel(mw, self.root)
        self._proxy_model = TreeProxyModel(self.view, self._model)
        self.view.setHeaderHidden(True)
        self.view.setModel(self._proxy_model)
        self.view.clicked.connect(self._on_click)
        self._model.dataChanged.connect(self._on_data_changed)
        # mw.line_edit_search_filters.textChanged.connect(self._proxy_model.set_filter)

    def populate(self) -> None:
        for item in self.root.children:
            item.set_children(
                VariantItem(data=var, parent=item) for var in item.data.variants()
            )

    def _on_click(self, index: QModelIndex) -> None:
        item = self._model.item_for_index(self._proxy_model.mapToSource(index))
        for changed in item.toggle_checked(keyboard_modifiers().ctrl):
            idx = self._model.index_for_item(changed)
            self._model.dataChanged.emit(idx, idx, [Qt.ItemDataRole.CheckStateRole])

    def connect_filter_changed(self, func: Callable[[], None]) -> None:
        self._model.dataChanged.connect(func)

    def _on_data_changed(self) -> None:
        search = db.SearchBuilder()
        for filt in self.root.children:
            filt.build_search(search)
        events.TreeFilterChanged(search).post()
