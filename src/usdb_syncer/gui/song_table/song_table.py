"""Controller for the song table."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator

import send2trash
from PySide6 import QtWidgets
from PySide6.QtCore import (
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QPoint,
    Qt,
    QTimer,
)
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QHeaderView, QMenu

from usdb_syncer import SongId, db, events, settings
from usdb_syncer.gui import ffmpeg_dialog
from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.gui.song_table.table_model import TableModel
from usdb_syncer.logger import get_logger
from usdb_syncer.song_loader import DownloadManager
from usdb_syncer.usdb_song import DownloadStatus, UsdbSong

if TYPE_CHECKING:
    from usdb_syncer.gui.mw import MainWindow

_logger = logging.getLogger(__file__)

DEFAULT_COLUMN_WIDTH = 300


class SongTable:
    """Controller for the song table."""

    _search = db.SearchBuilder()

    def __init__(self, mw: MainWindow) -> None:
        self.mw = mw
        self._model = TableModel(mw)
        self._view = mw.table_view
        self._setup_view()
        self._header().sortIndicatorChanged.connect(self._on_sort_order_changed)
        mw.table_view.selectionModel().currentChanged.connect(
            self._on_current_song_changed
        )
        self._setup_search_timer()
        events.TreeFilterChanged.subscribe(self._on_tree_filter_changed)
        events.TextFilterChanged.subscribe(self._on_text_filter_changed)

    def _header(self) -> QtWidgets.QHeaderView:
        return self._view.horizontalHeader()

    def reset(self) -> None:
        self._model.reset()

    def download_selection(self) -> None:
        self._download(self._selected_rows())

    def _download(self, rows: Iterable[int]) -> None:
        ffmpeg_dialog.check_ffmpeg(self.mw, partial(self._download_inner, rows))

    def _download_inner(self, rows: Iterable[int]) -> None:
        to_download: list[UsdbSong] = []
        for song_id in self._model.ids_for_rows(rows):
            song = UsdbSong.get(song_id)
            assert song
            if song.sync_meta and song.sync_meta.pinned:
                get_logger(__file__, song.song_id).info(
                    "Not downloading song as it is pinned."
                )
                continue
            if song.status.can_be_downloaded():
                song.status = DownloadStatus.PENDING
                events.SongChanged(song.song_id).post()
                to_download.append(song)
        if to_download:
            events.DownloadsRequested(len(to_download)).post()
            DownloadManager.download(to_download)

    def abort_selected_downloads(self) -> None:
        DownloadManager.abort(self._model.ids_for_rows(self._selected_rows()))

    def _setup_view(self) -> None:
        state = settings.get_table_view_header_state()
        self._view.setModel(self._model)
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._context_menu)
        self._view.doubleClicked.connect(lambda idx: self._download([idx.row()]))
        header = self._header()
        if not state.isEmpty():
            header.restoreState(state)
            self._search.order = Column(header.sortIndicatorSection()).song_order()
            self._search.descending = bool(header.sortIndicatorOrder())
        for column in Column:
            if size := column.fixed_size():
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
                header.resizeSection(column, size)
            # setting a (default) width on the last, stretching column seems to cause
            # issues, so we set it manually on the other columns
            elif column is not max(Column):
                if state.isEmpty():
                    header.resizeSection(column, DEFAULT_COLUMN_WIDTH)
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)

    def _context_menu(self, _pos: QPoint) -> None:
        menu = QMenu()
        for action in self.mw.menu_songs.actions():
            menu.addAction(action)
        menu.exec(QCursor.pos())

    def save_state(self) -> None:
        settings.set_table_view_header_state(
            self.mw.table_view.horizontalHeader().saveState()
        )

    ### actions

    def _on_current_song_changed(self) -> None:
        song = self.current_song()
        for action in self.mw.menu_songs.actions():
            action.setEnabled(bool(song))
        if not song:
            return
        for action in (
            self.mw.action_open_song_folder,
            self.mw.action_delete,
            self.mw.action_pin,
        ):
            action.setEnabled(song.is_local())
        self.mw.action_pin.setChecked(song.is_pinned())
        self.mw.action_songs_abort.setEnabled(song.status.can_be_aborted())

    def delete_selected_songs(self) -> None:
        with db.transaction():
            for song in self.selected_songs():
                if not song.sync_meta:
                    continue
                logger = get_logger(__file__, song.song_id)
                if song.is_pinned():
                    logger.info("Not trashing song folder as it is pinned.")
                    continue
                if song.sync_meta.path.exists():
                    send2trash.send2trash(song.sync_meta.path)
                song.remove_sync_meta()
                events.SongChanged(song.song_id)
                logger.debug("Trashed song folder.")

    def set_pin_selected_songs(self, pin: bool) -> None:
        for song in self.selected_songs():
            if not song.sync_meta or song.sync_meta.pinned == pin:
                continue
            song.sync_meta.pinned = pin
            song.sync_meta.synchronize_to_file()
            with db.transaction():
                song.sync_meta.upsert()
            events.SongChanged(song.song_id)

    ### selection model

    def current_song(self) -> UsdbSong | None:
        if (idx := self._view.selectionModel().currentIndex()).isValid():
            if ids := self._model.ids_for_indices([idx]):
                return UsdbSong.get(ids[0])
        return None

    def selected_songs(self) -> Iterator[UsdbSong]:
        return (
            song
            for song_id in self._model.ids_for_rows(self._selected_rows())
            if (song := UsdbSong.get(song_id))
        )

    def _selected_rows(self) -> Iterable[int]:
        return (idx.row() for idx in self._view.selectionModel().selectedRows())

    def set_selection_to_song_ids(self, select_song_ids: Iterable[SongId]) -> None:
        self.set_selection_to_indices(self._model.indices_for_ids(select_song_ids))

    def set_selection_to_indices(self, rows: Iterable[QModelIndex]) -> None:
        selection = QItemSelection()
        for row in rows:
            selection.select(row, row)
        self._view.selectionModel().select(
            selection,
            QItemSelectionModel.SelectionFlag.Rows
            | QItemSelectionModel.SelectionFlag.ClearAndSelect,
        )

    ### sorting and filtering

    def connect_row_count_changed(self, func: Callable[[int], None]) -> None:
        """Calls `func` with the new row count."""

        def wrapped(*_: Any) -> None:
            func(self._model.rowCount())

        self._model.modelReset.connect(wrapped)
        self._model.rowsInserted.connect(wrapped)
        self._model.rowsRemoved.connect(wrapped)

    def _setup_search_timer(self) -> None:
        self._search_timer = QTimer(self.mw)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.search_songs)

    def search_songs(self, msec_delay: int = 0) -> None:
        self._search_timer.stop()
        if msec_delay:
            self._search_timer.setInterval(msec_delay)
            self._search_timer.start()
        else:
            self._model.set_songs(db.search_usdb_songs(self._search))
            self._on_current_song_changed()

    def _on_tree_filter_changed(self, event: events.TreeFilterChanged) -> None:
        event.search.order = self._search.order
        event.search.descending = self._search.descending
        event.search.text = self._search.text
        self._search = event.search
        self.search_songs(100)

    def _on_text_filter_changed(self, event: events.TextFilterChanged) -> None:
        self._search.text = event.search
        self.search_songs(400)

    def _on_sort_order_changed(self, section: int, order: Qt.SortOrder) -> None:
        self._search.order = Column(section).song_order()
        self._search.descending = bool(order.value)
        self.search_songs()
