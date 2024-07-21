"""Controller for the filter tree."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QModelIndex, Qt

from usdb_syncer import db, events
from usdb_syncer.gui.gui_utils import keyboard_modifiers

from .item import Filter, SavedSearch
from .model import TreeModel, TreeProxyModel

if TYPE_CHECKING:
    from usdb_syncer.gui.mw import MainWindow


class FilterTree:
    """Controller for the filter tree."""

    _search = db.SearchBuilder()

    def __init__(self, mw: MainWindow) -> None:
        self.mw = mw
        self.view = mw.search_view
        self._model = TreeModel(mw)
        self._proxy_model = TreeProxyModel(self.view, self._model)
        self.view.setHeaderHidden(True)
        self.view.setModel(self._proxy_model)
        self.view.clicked.connect(self._on_click)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._context_menu)
        self._model.dataChanged.connect(self._on_data_changed)
        mw.line_edit_search_filters.textChanged.connect(self._proxy_model.set_filter)

    def populate(self) -> None:
        self._model.populate()

    def _on_click(self, index: QModelIndex) -> None:
        item = self._model.item_for_index(self._proxy_model.mapToSource(index))
        for changed in item.toggle_checked(keyboard_modifiers().ctrl):
            idx = self._model.index_for_item(changed)
            self._model.dataChanged.emit(idx, idx, [Qt.ItemDataRole.CheckStateRole])

    def connect_filter_changed(self, func: Callable[[], None]) -> None:
        self._model.dataChanged.connect(func)

    def _on_data_changed(self) -> None:
        self._search = db.SearchBuilder()
        for filt in self._model.root.children:
            filt.build_search(self._search)
        events.TreeFilterChanged(self._search).post()

    def _context_menu(self, _pos: QtCore.QPoint) -> None:
        item = self._model.item_for_index(
            self._proxy_model.mapToSource(self.view.currentIndex())
        )
        if item.data == Filter.SAVED:
            actions = [QtGui.QAction("Save current search", self.view)]
            actions[0].triggered.connect(self._add_saved_search)
        elif isinstance(item.data, SavedSearch):
            actions = []
        else:
            return
        menu = QtWidgets.QMenu()
        menu.addActions(actions)
        menu.exec(QtGui.QCursor.pos())

    def _add_saved_search(self) -> None:
        data = SavedSearch("", self._search)
        index = self._proxy_model.mapFromSource(self._model.insert_saved_search(data))
        self.view.setCurrentIndex(index)
        self.view.edit(index)
