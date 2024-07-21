"""Controller for the filter tree."""

from __future__ import annotations

import copy
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
        if isinstance(item.data, SavedSearch):
            for filt in self._model.root.children:
                for changed in filt.set_checked_children(item.data.search):
                    self._model.emit_item_changed(changed)
            events.SavedSearchRestored(item.data.search).post()
        else:
            for changed in item.toggle_checked(keyboard_modifiers().ctrl):
                self._model.emit_item_changed(changed)

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
            actions = [
                QtGui.QAction("Update with current search", self.view),
                QtGui.QAction("Delete", self.view),
            ]
            actions[0].triggered.connect(self._update_saved_search)
            actions[1].triggered.connect(self._delete_saved_search)
        else:
            return
        menu = QtWidgets.QMenu()
        menu.addActions(actions)
        menu.exec(QtGui.QCursor.pos())

    def _delete_saved_search(self) -> None:
        self._model.delete_saved_search(
            self._proxy_model.mapToSource(self.view.currentIndex())
        )

    def _update_saved_search(self) -> None:
        item = self._model.item_for_index(
            self._proxy_model.mapToSource(self.view.currentIndex())
        )
        if not isinstance(item.data, SavedSearch):
            return
        with db.transaction():
            self._search.upsert(item.data.name)
        item.data.search = copy.deepcopy(self._search)

    def _add_saved_search(self) -> None:
        name = first_name = "My search"
        i = 0
        while db.get_saved_search(name):
            i += 1
            name = f"{first_name} ({i})"
        with db.transaction():
            self._search.upsert(name)
        data = SavedSearch(name, self._search)
        index = self._proxy_model.mapFromSource(self._model.insert_saved_search(data))
        self.view.setCurrentIndex(index)
        self.view.edit(index)
