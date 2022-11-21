"""Proxy model for sorting and filtering data of a source model."""

from PySide6.QtCore import (
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSortFilterProxyModel,
)

from usdb_dl.gui.table_model import CustomRole

QIndex = QModelIndex | QPersistentModelIndex


class SortFilterProxyModel(QSortFilterProxyModel):
    """Proxy model for sorting and filtering data of a source model."""

    def __init__(self, parent: QObject) -> None:
        self._text_filter: list[str] = []
        super().__init__(parent)

    def set_text_filter(self, text: str) -> None:
        self._text_filter = text.lower().split()
        self.invalidate()

    def filterAcceptsRow(self, source_row: int, source_parent: QIndex) -> bool:
        model = self.sourceModel()
        idx = model.index(source_row, 0, source_parent)
        data = model.data(idx, CustomRole.SEARCHABLE_TEXT)
        return all(w in data for w in self._text_filter)
