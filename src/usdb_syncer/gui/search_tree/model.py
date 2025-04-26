"""Model for the filter tree."""

from __future__ import annotations

from typing import Any, cast, overload

from PySide6.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    Qt,
    QTimer,
)
from PySide6.QtWidgets import QWidget

from usdb_syncer import db

from .item import Filter, FilterItem, RootItem, SavedSearch, TreeItem, VariantItem

QIndex = QModelIndex | QPersistentModelIndex


class TreeModel(QAbstractItemModel):
    """Model for the filter tree."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.root = RootItem()
        self.root.set_children(FilterItem(data=f, parent=self.root) for f in Filter)
        # saved searches is not checkable
        self.root.children[0].checked = None

    def item_for_index(self, idx: QIndex) -> TreeItem | None:
        if idx.isValid():
            return cast(TreeItem, idx.internalPointer())
        return None

    def index_for_item(self, item: TreeItem) -> QModelIndex:
        return self.createIndex(item.row_in_parent, 0, item)

    def emit_item_changed(self, item: TreeItem) -> None:
        idx = self.index_for_item(item)
        self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.CheckStateRole])

    # change data

    def populate(self) -> None:
        self.beginResetModel()
        for item in self.root.children:
            item.set_children(
                VariantItem(data=var, parent=item, checkable=item.checkable)
                for var in item.data.variants()
            )
        self.endResetModel()

    def set_checked(self, item: TreeItem, checked: bool) -> None:
        if checked and item.parent:
            for sibling in item.parent.children:
                sibling.checked = False

        item.checked = checked

    def insert_saved_search(self, search: SavedSearch) -> QModelIndex:
        with db.transaction():
            search.insert()
        parent = self.root.children[0]
        parent_idx = self.index_for_item(parent)
        self.beginInsertRows(parent_idx, 0, 0)
        self.root.children[0].children = (
            VariantItem(data=search, parent=parent),
            *self.root.children[0].children,
        )
        self.endInsertRows()
        return self.index(0, 0, parent_idx)

    def delete_saved_search(self, index: QModelIndex) -> None:
        item = self.item_for_index(index)
        if not item or not isinstance(item.data, SavedSearch) or not item.parent:
            return
        self.beginRemoveRows(index.parent(), index.row(), index.row())
        with db.transaction():
            item.data.delete()
        children = item.parent.children
        item.parent.children = (*children[: index.row()], *children[index.row() + 1 :])
        self.endRemoveRows()

    # QAbstractItemModel implementation

    def rowCount(self, parent: QIndex | None = None) -> int:  # noqa: N802
        if parent is None:
            parent = QModelIndex()
        if not parent.isValid():
            return len(self.root.children)
        item = cast(TreeItem, parent.internalPointer())
        return len(item.children)

    def columnCount(self, parent: QIndex | None = None) -> int:  # noqa: N802
        return 1

    def index(self, row: int, column: int, parent: QIndex | None = None) -> QModelIndex:
        if parent is None:
            parent = QModelIndex()
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if parent.isValid():
            parent_item = cast(TreeItem, parent.internalPointer())
        else:
            parent_item = self.root
        item = parent_item.children[row]
        return self.createIndex(row, column, item)

    @overload  # type: ignore
    def parent(self, child: QIndex) -> QModelIndex: ...

    @overload
    def parent(self) -> QObject: ...

    def parent(self, child: QIndex | None = None) -> QModelIndex | QObject:
        if child is None:
            return super().parent()
        if not child.isValid():
            return QModelIndex()
        child_item = cast(TreeItem, child.internalPointer())
        parent_item = child_item.parent
        if parent_item is None or parent_item is self.root:
            return QModelIndex()
        return self.createIndex(parent_item.row_in_parent, 0, parent_item)

    def data(self, index: QIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not (item := self.item_for_index(index)):
            return None

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return str(item.data)
        if role == Qt.ItemDataRole.CheckStateRole:
            return item.checked if item.checkable else None
        if role == Qt.ItemDataRole.DecorationRole:
            return item.decoration()
        return None

    def flags(self, index: QIndex) -> Qt.ItemFlag:
        if item := self.item_for_index(index):
            return item.flags()
        return Qt.ItemFlag.NoItemFlags

    def setData(self, index: QIndex, value: Any, role: int = 0) -> bool:  # noqa: N802
        if not (
            role == Qt.ItemDataRole.EditRole
            and value
            and isinstance(value, str)
            and (item := self.item_for_index(index))
            and isinstance(item.data, SavedSearch)
            and item.data.name != value
        ):
            return False
        item.data.update(new_name=value)
        return True


class TreeProxyModel(QSortFilterProxyModel):
    """Proxy model for filtering the filter tree by text."""

    def __init__(self, parent: QObject, source_model: TreeModel) -> None:
        super().__init__(parent)
        self._source = source_model
        self.setSourceModel(source_model)
        self._filter: str = ""
        self._matches: dict[Filter, set[str | int]] = {}
        self._filter_invalidation_timer = QTimer(parent)
        self._filter_invalidation_timer.setSingleShot(True)
        self._filter_invalidation_timer.setInterval(400)
        self._filter_invalidation_timer.timeout.connect(self._on_filter_changed)

    def filterAcceptsRow(  # noqa: N802
        self, source_row: int, source_parent: QIndex
    ) -> bool:
        if not self._filter or not (
            parent := self._source.item_for_index(source_parent)
        ):
            return True
        return parent.children[source_row].is_accepted(self._matches)

    def set_filter(self, text: str) -> None:
        if (new := text.strip()) != self._filter:
            self._filter = new
            self._filter_invalidation_timer.start()

    def _on_filter_changed(self) -> None:
        if self._filter:
            self._matches = {
                Filter.ARTIST: set(db.search_usdb_song_artists(self._filter)),
                Filter.TITLE: set(db.search_usdb_song_titles(self._filter)),
                Filter.EDITION: set(db.search_usdb_song_editions(self._filter)),
                Filter.LANGUAGE: set(db.search_usdb_song_languages(self._filter)),
                Filter.YEAR: set(db.search_usdb_song_years(self._filter)),
                Filter.GENRE: set(db.search_usdb_song_genres(self._filter)),
                Filter.CREATOR: set(db.search_usdb_song_creators(self._filter)),
            }
        else:
            self._matches = {}
        self.invalidateRowsFilter()
