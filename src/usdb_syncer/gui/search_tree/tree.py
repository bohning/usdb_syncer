"""Controller for the filter tree."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import TYPE_CHECKING

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
        self._setup_actions()
        events.SearchOrderChanged.subscribe(self._on_search_order_changed)
        events.TextFilterChanged.subscribe(self._on_text_filter_changed)
        events.SavedSearchRestored.subscribe(self._restore_saved_search)

    def _setup_actions(self) -> None:
        self.mw.action_add_saved_search.triggered.connect(self._add_saved_search)
        self.mw.action_update_saved_search.triggered.connect(self._update_saved_search)
        self.mw.action_delete_saved_search.triggered.connect(self._delete_saved_search)
        self.mw.action_set_saved_search_default.triggered.connect(
            self._set_search_is_default
        )
        self.mw.action_set_saved_search_subscribed.triggered.connect(
            self._set_search_subscribed
        )

    def populate(self) -> None:
        self._model.populate()
        self.view.expand(
            self._proxy_model.mapFromSource(
                self._model.index_for_item(self._model.root.children[0])
            )
        )

    def _restore_saved_search(self, event: events.SavedSearchRestored) -> None:
        for filt in self._model.root.children:
            for changed in filt.set_checked_children(event.search):
                self._model.emit_item_changed(changed)

    def _on_click(self, index: QModelIndex) -> None:
        if not (
            item := self._model.item_for_index(self._proxy_model.mapToSource(index))
        ):
            return
        if isinstance(item.data, SavedSearch):
            events.SavedSearchRestored(item.data.search).post()
        else:
            for changed in item.toggle_checked(keyboard_modifiers().ctrl):
                self._model.emit_item_changed(changed)

    def connect_filter_changed(self, func: Callable[[], None]) -> None:
        self._model.dataChanged.connect(func)

    def _on_data_changed(self) -> None:
        self._search = db.SearchBuilder(
            order=self._search.order,
            descending=self._search.descending,
            text=self._search.text,
        )
        for filt in self._model.root.children:
            filt.build_search(self._search)
        events.TreeFilterChanged(self._search).post()

    def _context_menu(self, _pos: QtCore.QPoint) -> None:
        item = self._model.item_for_index(
            self._proxy_model.mapToSource(self.view.currentIndex())
        )
        if item and item.data == Filter.SAVED:
            actions = [self.mw.action_add_saved_search]
        elif item and isinstance(item.data, SavedSearch):
            self.mw.action_set_saved_search_default.setChecked(item.data.is_default)
            self.mw.action_set_saved_search_subscribed.setChecked(item.data.subscribed)
            actions = [
                self.mw.action_update_saved_search,
                self.mw.action_delete_saved_search,
                self.mw.action_set_saved_search_default,
                self.mw.action_set_saved_search_subscribed,
            ]
        else:
            return
        menu = QtWidgets.QMenu()
        menu.addActions(actions)
        menu.exec(QtGui.QCursor.pos())

    def _delete_saved_search(self) -> None:
        self._model.delete_saved_search(
            self._proxy_model.mapToSource(self.view.currentIndex())
        )

    def _get_current_saved_search(self) -> SavedSearch | None:
        item = self._model.item_for_index(
            self._proxy_model.mapToSource(self.view.currentIndex())
        )
        if item and isinstance(item.data, SavedSearch):
            return item.data
        return None

    def _update_saved_search(self) -> None:
        if search := self._get_current_saved_search():
            search.search = copy.deepcopy(self._search)
            with db.transaction():
                search.update()

    def _add_saved_search(self) -> None:
        index = self._proxy_model.mapFromSource(
            self._model.insert_saved_search(SavedSearch("My search", self._search))
        )
        self.view.setCurrentIndex(index)
        self.view.edit(index)

    def _set_search_is_default(self, default: bool) -> None:
        if search := self._get_current_saved_search():
            if default:
                for item in self._model.root.children[0].children:
                    if isinstance(item.data, SavedSearch) and item.data.is_default:
                        item.data.is_default = False
            search.is_default = default
            with db.transaction():
                search.update()

    def _set_search_subscribed(self, subscribe: bool) -> None:
        if search := self._get_current_saved_search():
            search.subscribed = subscribe
            with db.transaction():
                search.update()

    def _on_search_order_changed(self, event: events.SearchOrderChanged) -> None:
        self._search.descending = event.descending
        self._search.order = event.order

    def _on_text_filter_changed(self, event: events.TextFilterChanged) -> None:
        self._search.text = event.search
