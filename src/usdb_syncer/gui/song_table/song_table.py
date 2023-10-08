"""Controller for the song table."""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator

import attrs
import send2trash
from PySide6.QtCore import (
    QByteArray,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QObject,
    QPoint,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QHeaderView, QLabel, QMenu, QProgressBar, QTableView

from usdb_syncer import SongId, settings
from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.gui.song_table.proxy_model import ProxyModel
from usdb_syncer.gui.song_table.table_model import CustomRole, TableModel
from usdb_syncer.logger import get_logger
from usdb_syncer.song_data import (
    DownloadErrorReason,
    DownloadResult,
    DownloadStatus,
    LocalFiles,
    SongData,
    fuzz_text,
)
from usdb_syncer.song_loader import DownloadInfo, download_songs
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.song_txt.headers import Headers
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.usdb_scraper import UsdbSong
from usdb_syncer.utils import try_read_unknown_encoding

if TYPE_CHECKING:
    from usdb_syncer.gui.mw import MainWindow

_logger = logging.getLogger(__file__)
_err_logger = get_logger(__file__ + "[errors]")
_err_logger.setLevel(logging.ERROR)

DEFAULT_COLUMN_WIDTH = 300


class SongSignals(QObject):
    """Signals relating to songs."""

    started = Signal(SongId)
    finished = Signal(DownloadResult)


@attrs.define
class Progress:
    """Progress bar controller."""

    _bar: QProgressBar
    _label: QLabel
    _running: int = 0
    _finished: int = 0

    def start(self, count: int) -> None:
        if self._running == self._finished:
            self._running = 0
            self._finished = 0
        self._running += count
        self._update()

    def finish(self, count: int) -> None:
        self._finished += count
        self._update()

    def _update(self) -> None:
        self._label.setText(f"{self._finished}/{self._running}")
        self._bar.setValue(int((self._finished + 1) / (self._running + 1) * 100))


class SongTable:
    """Controller for the song table."""

    def __init__(self, mw: MainWindow) -> None:
        self.mw = mw
        self._model = TableModel(mw)
        self._proxy_model = ProxyModel(mw, mw.tree)
        self.table_view = mw.table_view
        self._setup_view(
            mw.table_view, self._proxy_model, settings.get_table_view_header_state()
        )
        mw.table_view.selectionModel().currentChanged.connect(
            self._on_current_song_changed
        )
        self._signals = SongSignals()
        self._signals.started.connect(self._on_download_started)
        self._signals.finished.connect(self._on_download_finished)
        self._progress = Progress(mw.bar_download_progress, mw.label_download_progress)

    def download_selection(self) -> None:
        self._download(self._selected_rows())

    def _download(self, rows: Iterable[int]) -> None:
        to_download = []
        for row in rows:
            data = self._model.songs[row]
            if data.local_files.pinned:
                get_logger(__file__, data.data.song_id).info(
                    "Not downloading song as it is pinned."
                )
                continue
            if data.status.can_be_downloaded():
                data.status = DownloadStatus.PENDING
                to_download.append(data)
                self._model.row_changed(row)
        if to_download:
            self._progress.start(len(to_download))
            download_songs(
                map(DownloadInfo.from_song_data, to_download),
                self._signals.started.emit,
                self._signals.finished.emit,
            )

    def _setup_view(
        self, view: QTableView, model: QSortFilterProxyModel, state: QByteArray
    ) -> None:
        model.setSourceModel(self._model)
        model.setSortRole(CustomRole.SORT)
        view.setModel(model)
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        view.customContextMenuRequested.connect(self._context_menu)
        view.doubleClicked.connect(self._on_double_clicked)
        header = view.horizontalHeader()
        if not state.isEmpty():
            header.restoreState(state)
            return
        for column in Column:
            if not model.filterAcceptsColumn(column, QModelIndex()):
                continue
            if size := column.fixed_size(header, self.mw):
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
                header.resizeSection(column, size)
            # setting a (default) width on the last, stretching column seems to cause
            # issues, so we set it manually on the other columns
            elif column is not max(Column):
                header.resizeSection(column, DEFAULT_COLUMN_WIDTH)
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)

    def _context_menu(self, _pos: QPoint) -> None:
        menu = QMenu()
        for action in self.mw.menu_songs.actions():
            menu.addAction(action)
        menu.exec(QCursor.pos())

    def _on_double_clicked(self, index: QModelIndex) -> None:
        self._download([self._proxy_model.mapToSource(index).row()])

    def _on_download_started(self, song_id: SongId) -> None:
        if (row := self._model.rows.get(song_id)) is None:
            logger = get_logger(__file__, song_id)
            logger.error("Unknown id. Ignoring download start signal.")
            return
        data = self._model.songs[row]
        data.status = DownloadStatus.DOWNLOADING
        self._model.row_changed(row)

    def _on_download_finished(self, result: DownloadResult) -> None:
        self._progress.finish(1)
        logger = get_logger(__file__, result.song_id)
        if result.error is not None:
            if (row := self._model.row_for_id(result.song_id)) is None:
                logger.error("Unknown id. Ignoring download finish signal.")
                return
            if result.error is DownloadErrorReason.NOT_FOUND:
                self._model.remove_row(row)
                logger.info("Removed song from local database.")
            else:
                self._model.songs[row].status = DownloadStatus.FAILED
                self._model.row_changed(row)
        elif result.data:
            self._model.update_item(result.data)
            logger.info("All done!")

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
            action.setEnabled(bool(song.local_files.usdb_path))
        self.mw.action_pin.setChecked(song.local_files.pinned)

    def delete_selected_songs(self) -> None:
        for song in self.selected_songs():
            if not song.local_files.usdb_path:
                continue
            logger = get_logger(__file__, song.data.song_id)
            if song.local_files.pinned:
                logger.info("Not trashing song folder as it is pinned.")
                continue
            send2trash.send2trash(song.local_files.usdb_path.parent)
            song.local_files = LocalFiles()
            self._model.update_item(song)
            logger.debug("Trashed song folder.")

    def set_pin_selected_songs(self, pin: bool) -> None:
        def setter(meta: SyncMeta) -> None:
            meta.pinned = pin

        for song in self.selected_songs():
            if song.local_files.pinned == pin or not song.local_files.usdb_path:
                continue
            song.local_files.pinned = pin
            song.local_files.try_update_sync_meta(setter)
            self._model.update_item(song)

    ### selection model

    def current_song(self) -> SongData | None:
        if (idx := self.table_view.selectionModel().currentIndex()).isValid():
            if rows := self._proxy_model.source_rows([idx]):
                return self._model.songs[rows[0]]
        return None

    def selected_songs(self) -> Iterator[SongData]:
        return (self._model.songs[row] for row in self._selected_rows())

    def _selected_rows(self) -> Iterable[int]:
        return self._proxy_model.source_rows(
            self.table_view.selectionModel().selectedRows()
        )

    def select_local_songs(self, directory: Path) -> None:
        song_map: defaultdict[tuple[str, str], list[int]] = defaultdict(list)
        for row, song in enumerate(self._model.songs):
            song_map[fuzzy_key(song.data)].append(row)
        matched_rows: set[int] = set()
        for path in directory.glob("**/*.txt"):
            if txt := try_parse_txt(path):
                name = txt.headers.artist_title_str()
                if matches := song_map[fuzzy_key(txt.headers)]:
                    plural = "es" if len(matches) > 1 else ""
                    _logger.info(f"{len(matches)} match{plural} for '{name}'.")
                    matched_rows.update(matches)
                else:
                    _logger.warning(f"No matches for '{name}'.")
        self.set_selection_to_indices(
            self._proxy_model.target_indices(
                self._model.index(row, 0) for row in matched_rows
            )
        )
        _logger.info(f"Selected {len(matched_rows)} songs.")

    def set_selection_to_song_ids(self, select_song_ids: list[SongId]) -> None:
        source_indices = self._model.indices_for_ids(select_song_ids)
        self.set_selection_to_indices(self._proxy_model.target_indices(source_indices))

    def set_selection_to_indices(self, rows: Iterable[QModelIndex]) -> None:
        selection = QItemSelection()
        for row in rows:
            selection.select(row, row)
        self.table_view.selectionModel().select(
            selection,
            QItemSelectionModel.SelectionFlag.Rows
            | QItemSelectionModel.SelectionFlag.ClearAndSelect,
        )

    ### sort and filter model

    def connect_row_count_changed(self, func: Callable[[int], None]) -> None:
        """Calls `func` with the new row count."""

        def wrapped(*_: Any) -> None:
            func(self._proxy_model.rowCount())

        self._model.modelReset.connect(wrapped)
        self._proxy_model.rowsInserted.connect(wrapped)
        self._proxy_model.rowsRemoved.connect(wrapped)

    def set_text_filter(self, text: str) -> None:
        self._proxy_model.set_text_filter(text)

    ### data model

    def set_data(self, songs: tuple[SongData, ...]) -> None:
        self._model.set_data(songs)

    def get_all_data(self) -> tuple[SongData, ...]:
        return self._model.songs

    def all_local_songs(self) -> Iterator[UsdbSong]:
        return self._model.all_local_songs()

    def get_data(self, song_id: SongId) -> SongData | None:
        return self._model.item_for_id(song_id)

    def update_item(self, new: SongData) -> None:
        self._model.update_item(new)


def fuzzy_key(data: UsdbSong | Headers) -> tuple[str, str]:
    return fuzz_text(data.artist), fuzz_text(data.title)


def try_parse_txt(path: Path) -> SongTxt | None:
    if contents := try_read_unknown_encoding(path):
        return SongTxt.try_parse(contents, _err_logger)
    return None
