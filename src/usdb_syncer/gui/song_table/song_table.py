"""Controller for the song table."""

from __future__ import annotations

import logging
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
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QHeaderView, QLabel, QMenu, QProgressBar, QTableView

from usdb_syncer import SongId, db, settings, signals
from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.gui.song_table.table_model import TableModel
from usdb_syncer.logger import get_logger

# from usdb_syncer.song_list_fetcher import find_local_files
from usdb_syncer.song_loader import DownloadErrorReason, DownloadResult, download_songs
from usdb_syncer.song_txt import SongTxt

# from usdb_syncer.db.models import DownloadStatus, LocalSong, UsdbSong
from usdb_syncer.usdb_song import DownloadStatus, UsdbSong
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

    _search = db.SearchBuilder()

    def __init__(self, mw: MainWindow) -> None:
        self.mw = mw
        self._model = TableModel(mw)
        self.table_view = mw.table_view
        self._setup_view(mw.table_view, settings.get_table_view_header_state())
        mw.table_view.selectionModel().currentChanged.connect(
            self._on_current_song_changed
        )
        self._setup_search_timer()
        signals.TreeFilterChanged.subscribe(self._on_search_changed)
        self._signals = SongSignals()
        self._signals.started.connect(self._on_download_started)
        self._signals.finished.connect(self._on_download_finished)
        self._progress = Progress(mw.bar_download_progress, mw.label_download_progress)

    def reset(self) -> None:
        self._model.reset()

    # def resync_song_data(self) -> None:
    #     local_files = find_local_files()
    #     self._model.songs = tuple(
    #         song.with_local_files(local_files.get(song.data.song_id, LocalFiles()))
    #         for song in self._model.songs
    #     )
    #     self._model.reset()

    def download_selection(self) -> None:
        self._download(self._selected_rows())

    def _download(self, rows: Iterable[int]) -> None:
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
                to_download.append(song)
                self._model.song_changed(song.song_id)
        if to_download:
            self._progress.start(len(to_download))
            download_songs(
                to_download, self._signals.started.emit, self._signals.finished.emit
            )

    def _setup_view(self, view: QTableView, state: QByteArray) -> None:
        view.setModel(self._model)
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        view.customContextMenuRequested.connect(self._context_menu)
        view.doubleClicked.connect(lambda idx: self._download([idx.row()]))
        header = view.horizontalHeader()
        if not state.isEmpty():
            header.restoreState(state)
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

    def _on_download_started(self, song_id: SongId) -> None:
        if (song := UsdbSong.get(song_id)) is None:
            logger = get_logger(__file__, song_id)
            logger.error("Unknown id. Ignoring download start signal.")
            return
        song.status = DownloadStatus.DOWNLOADING
        self._model.song_changed(song_id)

    def _on_download_finished(self, result: DownloadResult) -> None:
        self._progress.finish(1)
        logger = get_logger(__file__, result.song_id)
        if result.error is not None:
            if (song := UsdbSong.get(result.song_id)) is None:
                logger.error("Unknown id. Ignoring download finish signal.")
                return
            if result.error is DownloadErrorReason.NOT_FOUND:
                # db.delete_usdb_song(song)
                logger.info("Song is not on USDB anymore.")
            else:
                song.status = DownloadStatus.FAILED
                self._model.song_changed(result.song_id)
        elif result.data:
            result.data.upsert()
            self._model.song_changed(result.song_id)
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
            action.setEnabled(song.is_local())
        self.mw.action_pin.setChecked(song.is_pinned())

    def delete_selected_songs(self) -> None:
        for song in self.selected_songs():
            if not song.sync_meta:
                continue
            logger = get_logger(__file__, song.song_id)
            if song.is_pinned():
                logger.info("Not trashing song folder as it is pinned.")
                continue
            send2trash.send2trash(song.sync_meta.path)
            db.delete_sync_meta(song.sync_meta.sync_meta_id)
            self._model.song_changed(song.song_id)
            logger.debug("Trashed song folder.")

    def set_pin_selected_songs(self, pin: bool) -> None:
        for song in self.selected_songs():
            if not song.sync_meta or song.sync_meta.pinned == pin:
                continue
            song.sync_meta.pinned = pin
            song.sync_meta.synchronize_to_file()
            db.commit()
            self._model.song_changed(song.song_id)

    ### selection model

    def current_song(self) -> UsdbSong | None:
        if (idx := self.table_view.selectionModel().currentIndex()).isValid():
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
        return (idx.row() for idx in self.table_view.selectionModel().selectedRows())

    # TODO
    # def select_local_songs(self, directory: Path) -> None:
    #     song_map: defaultdict[tuple[str, str], list[int]] = defaultdict(list)
    #     for row, song in enumerate(self._model.songs):
    #         song_map[fuzzy_key(song.data)].append(row)
    #     matched_rows: set[int] = set()
    #     for path in directory.glob("**/*.txt"):
    #         if txt := try_parse_txt(path):
    #             name = txt.headers.artist_title_str()
    #             if matches := song_map[fuzzy_key(txt.headers)]:
    #                 plural = "es" if len(matches) > 1 else ""
    #                 _logger.info(f"{len(matches)} match{plural} for '{name}'.")
    #                 matched_rows.update(matches)
    #             else:
    #                 _logger.warning(f"No matches for '{name}'.")
    #     self.set_selection_to_indices(
    #         self._proxy_model.target_indices(
    #             self._model.index(row, 0) for row in matched_rows
    #         )
    #     )
    #     _logger.info(f"Selected {len(matched_rows)} songs.")

    def set_selection_to_song_ids(self, select_song_ids: list[SongId]) -> None:
        self.set_selection_to_indices(self._model.indices_for_ids(select_song_ids))

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
            func(self._model.rowCount())

        self._model.modelReset.connect(wrapped)
        self._model.rowsInserted.connect(wrapped)
        self._model.rowsRemoved.connect(wrapped)

    def set_text_filter(self, text: str) -> None:
        # TODO
        pass

    def _setup_search_timer(self) -> None:
        self._search_timer = QTimer(self.mw)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(600)
        self._search_timer.timeout.connect(self.search_songs)

    def search_songs(self) -> None:
        self._model.set_songs(db.search_usdb_songs(self._search))

    def _on_search_changed(self, search: db.SearchBuilder) -> None:
        self._search = search
        self._search_timer.start()


def try_parse_txt(path: Path) -> SongTxt | None:
    if contents := try_read_unknown_encoding(path):
        return SongTxt.try_parse(contents, _err_logger)
    return None
