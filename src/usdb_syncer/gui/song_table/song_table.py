"""Controller for the song table."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from functools import partial
from typing import TYPE_CHECKING, Any

import send2trash
from PySide6 import QtCore, QtMultimedia, QtWidgets
from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtGui import QAction, QCursor, QKeySequence, QShortcut

from usdb_syncer import SongId, db, events, media_player, settings, sync_meta
from usdb_syncer.gui import ffmpeg_dialog
from usdb_syncer.gui.custom_data_dialog import CustomDataDialog
from usdb_syncer.gui.progress import run_with_progress
from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.gui.song_table.table_model import TableModel
from usdb_syncer.logger import song_logger
from usdb_syncer.song_loader import DownloadManager
from usdb_syncer.usdb_song import DownloadStatus, UsdbSong

if TYPE_CHECKING:
    from usdb_syncer.gui.mw import MainWindow


DEFAULT_COLUMN_WIDTH = 300


class SongTable:
    """Controller for the song table."""

    _search = db.SearchBuilder()
    _playing_song: UsdbSong | None = None
    _next_playing_song: UsdbSong | None = None

    def __init__(self, mw: MainWindow) -> None:
        self.mw = mw
        self._model = TableModel(mw)
        self._view = mw.table_view
        self._media_player = media_player.media_player()
        self._media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._media_player.errorChanged.connect(self._on_playback_error_changed)
        self._setup_view()
        self._header().sortIndicatorChanged.connect(self._on_sort_order_changed)
        mw.table_view.selectionModel().currentChanged.connect(
            self._on_current_song_changed
        )
        events.SongChanged.subscribe(self._on_song_changed)
        self._setup_search_timer()
        events.TreeFilterChanged.subscribe(self._on_tree_filter_changed)
        events.TextFilterChanged.subscribe(self._on_text_filter_changed)
        events.SavedSearchRestored.subscribe(self._on_saved_search_restored)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self._view).activated.connect(
            self._on_space
        )

    def _on_playback_state_changed(
        self, state: QtMultimedia.QMediaPlayer.PlaybackState
    ) -> None:
        if state == QtMultimedia.QMediaPlayer.PlaybackState.PlayingState:
            assert self._next_playing_song
            self._playing_song = song = self._next_playing_song
            self._next_playing_song = None
            song.is_playing = True
        else:
            assert self._playing_song
            song = self._playing_song
            self._playing_song = None
            song.is_playing = False
        with db.transaction():
            song.upsert()
        events.SongChanged(song.song_id).post()

    def _on_playback_error_changed(self) -> None:
        if not self._media_player.error().value or self._next_playing_song is None:
            return
        logger = song_logger(self._next_playing_song.song_id)
        source = self._media_player.source().url()
        logger.error(f"Failed to play back source: {source}")
        logger.debug(self._media_player.errorString())

    def _on_space(self) -> None:
        if song := self.current_song():
            self._play_or_stop_sample(song)

    def _header(self) -> QtWidgets.QHeaderView:
        return self._view.horizontalHeader()

    def reset(self) -> None:
        self._model.reset()

    def begin_reset(self) -> None:
        self._model.beginResetModel()

    def end_reset(self) -> None:
        self._model.endResetModel()

    def download_selection(self) -> None:
        self._download(self._selected_rows())

    def _download(self, rows: Iterable[int]) -> None:
        ffmpeg_dialog.check_ffmpeg(
            self.mw,
            lambda: run_with_progress(
                "Initializing downloads ...", partial(self._download_inner, rows)
            ),
        )

    def _download_inner(self, rows: Iterable[int]) -> None:
        to_download: list[UsdbSong] = []
        for song_id in self._model.ids_for_rows(rows):
            song = UsdbSong.get(song_id)
            assert song
            if song.sync_meta and song.sync_meta.pinned:
                song_logger(song.song_id).info("Not downloading song as it is pinned.")
                continue
            if song.status.can_be_downloaded():
                song.status = DownloadStatus.PENDING
                with db.transaction():
                    song.upsert()
                events.SongChanged(song.song_id).post()
                to_download.append(song)
        if to_download:
            events.DownloadsRequested(len(to_download)).post()
            DownloadManager.download(to_download)

    def abort_selected_downloads(self) -> None:
        ids = self._model.ids_for_rows(self._selected_rows())
        run_with_progress("Aborting downloads ...", lambda: DownloadManager.abort(ids))

    def _setup_view(self) -> None:
        state = settings.get_table_view_header_state()
        self._view.setModel(self._model)
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._view.customContextMenuRequested.connect(
            lambda: self.mw.menu_songs.exec(QCursor.pos())
        )
        self._view.doubleClicked.connect(lambda idx: self._download([idx.row()]))
        self._view.clicked.connect(self._on_click)
        header = self._header()
        existing_state = False
        if not state.isEmpty():
            header.restoreState(state)
            if header.count() != max(Column) + 1:
                header.reset()
            else:
                existing_state = True
                self._search.order = Column(header.sortIndicatorSection()).song_order()
                self._search.descending = bool(header.sortIndicatorOrder().value)
        for column in Column:
            if size := column.fixed_size():
                header.setSectionResizeMode(
                    column, QtWidgets.QHeaderView.ResizeMode.Fixed
                )
                header.resizeSection(column, size)
            # setting a (default) width on the last, stretching column seems to cause
            # issues, so we set it manually on the other columns
            elif column is not max(Column):
                if not existing_state:
                    header.resizeSection(column, DEFAULT_COLUMN_WIDTH)
                header.setSectionResizeMode(
                    column, QtWidgets.QHeaderView.ResizeMode.Interactive
                )

    def build_custom_data_menu(self) -> None:
        if not (song := self.current_song()) or not song.sync_meta:
            return

        def update(key: str, value: str | None) -> None:
            if not song.sync_meta:
                return
            song.sync_meta.custom_data.set(key, value)
            with db.transaction():
                song.upsert()
            events.SongChanged(song.song_id).post()

        def run_custom_data_dialog(key: str | None = None) -> None:
            CustomDataDialog(self.mw, update, key).open()

        self.mw.menu_custom_data.clear()
        _add_action("New ...", self.mw.menu_custom_data, run_custom_data_dialog)
        self.mw.menu_custom_data.addSeparator()
        for key, value in song.sync_meta.custom_data.items():
            key_menu = QtWidgets.QMenu(key, self.mw.menu_custom_data)
            self.mw.menu_custom_data.addMenu(key_menu)
            _add_action("New ...", key_menu, partial(run_custom_data_dialog, key))
            key_menu.addSeparator()
            _add_action(value, key_menu, partial(update, key, None), checked=True)
            for option in sync_meta.CustomData.value_options(key):
                if option != value:
                    _add_action(
                        option, key_menu, partial(update, key, option), checked=False
                    )

    def _on_click(self, index: QtCore.QModelIndex) -> None:
        if index.column() == Column.SAMPLE_URL.value and (
            song := UsdbSong.get(self._model.ids_for_indices([index])[0])
        ):
            self._play_or_stop_sample(song)

    def _play_or_stop_sample(self, song: UsdbSong) -> None:
        if self._playing_song and song.song_id == self._playing_song.song_id:
            # second play() in a row is a stop()
            self._media_player.stop()
            return
        position = 0
        if song.sync_meta and song.sync_meta.audio:
            path = song.sync_meta.path.parent / song.sync_meta.audio.fname
            url = path.absolute().as_posix()
            if song.sync_meta.meta_tags.preview:
                position = int(song.sync_meta.meta_tags.preview * 1000)
        elif song.sample_url:
            url = song.sample_url
        else:
            return
        self._next_playing_song = song
        self._media_player.setSource(url)
        self._media_player.setPosition(position)
        self._media_player.play()

    def save_state(self) -> None:
        settings.set_table_view_header_state(
            self.mw.table_view.horizontalHeader().saveState()
        )

    # actions

    def _on_song_changed(self, event: events.SongChanged) -> None:
        if event.song_id == self.current_song_id():
            self._on_current_song_changed()

    def _on_current_song_changed(self) -> None:
        song = self.current_song()
        for action in self.mw.menu_songs.actions():
            action.setEnabled(bool(song))
        if not song:
            return
        for action in (
            self.mw.action_open_song_folder,
            self.mw.menu_open_song_in,
            self.mw.action_open_song_in_karedi,
            self.mw.action_open_song_in_performous,
            self.mw.action_open_song_in_ultrastar_manager,
            self.mw.action_open_song_in_usdx,
            self.mw.action_open_song_in_vocaluxe,
            self.mw.action_open_song_in_yass_reloaded,
            self.mw.action_delete,
            self.mw.action_pin,
            self.mw.menu_custom_data,
        ):
            action.setEnabled(song.is_local())
        self.mw.action_open_song_in_karedi.setVisible(
            settings.get_app_path(settings.SupportedApps.KAREDI) is not None
        )
        self.mw.action_open_song_in_performous.setVisible(
            settings.get_app_path(settings.SupportedApps.PERFORMOUS) is not None
        )
        self.mw.action_open_song_in_ultrastar_manager.setVisible(
            settings.get_app_path(settings.SupportedApps.ULTRASTAR_MANAGER) is not None
        )
        self.mw.action_open_song_in_usdx.setVisible(
            settings.get_app_path(settings.SupportedApps.USDX) is not None
        )
        self.mw.action_open_song_in_vocaluxe.setVisible(
            settings.get_app_path(settings.SupportedApps.VOCALUXE) is not None
        )
        self.mw.action_open_song_in_yass_reloaded.setVisible(
            settings.get_app_path(settings.SupportedApps.YASS_RELOADED) is not None
        )
        self.mw.action_pin.setChecked(song.is_pinned())
        self.mw.action_songs_abort.setEnabled(song.status.can_be_aborted())

    def delete_selected_songs(self) -> None:
        with db.transaction():
            for song in self.selected_songs():
                if not song.sync_meta:
                    continue
                logger = song_logger(song.song_id)
                if song.is_pinned():
                    logger.info("Not trashing song folder as it is pinned.")
                    continue
                if song.sync_meta.path.exists():
                    send2trash.send2trash(song.sync_meta.path.parent)
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

    # selection model

    def current_song_id(self) -> SongId | None:
        if (idx := self._view.selectionModel().currentIndex()).isValid():
            if ids := self._model.ids_for_indices([idx]):
                return ids[0]
        return None

    def current_song(self) -> UsdbSong | None:
        if (song_id := self.current_song_id()) is not None:
            return UsdbSong.get(song_id)
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

    def set_selection_to_indices(self, rows: Iterable[QtCore.QModelIndex]) -> None:
        selection = QtCore.QItemSelection()
        for row in rows:
            selection.select(row, row)
        self._view.selectionModel().select(
            selection,
            QItemSelectionModel.SelectionFlag.Rows
            | QItemSelectionModel.SelectionFlag.ClearAndSelect,
        )

    # sorting and filtering

    def connect_row_count_changed(self, func: Callable[[int, int], None]) -> None:
        """Calls `func` with the new table row and selection counts."""

        def wrapped(*_: Any) -> None:
            func(
                self._model.rowCount(), len(self._view.selectionModel().selectedRows())
            )

        self._model.modelReset.connect(wrapped)
        self._model.rowsInserted.connect(wrapped)
        self._model.rowsRemoved.connect(wrapped)
        self._view.selectionModel().selectionChanged.connect(wrapped)

    def _setup_search_timer(self) -> None:
        self._search_timer = QtCore.QTimer(self.mw)
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

    def _on_saved_search_restored(self, event: events.SavedSearchRestored) -> None:
        self._search.order = event.search.order
        self._search.descending = event.search.descending
        self._search.text = event.search.text
        self._header().setSortIndicator(
            Column.from_song_order(event.search.order),
            (
                Qt.SortOrder.DescendingOrder
                if event.search.descending
                else Qt.SortOrder.AscendingOrder
            ),
        )
        self.search_songs(100)

    def _on_text_filter_changed(self, event: events.TextFilterChanged) -> None:
        self._search.text = event.search
        self.search_songs(400)

    def _on_sort_order_changed(self, section: int, order: Qt.SortOrder) -> None:
        self._search.order = Column(section).song_order()
        self._search.descending = bool(order.value)
        events.SearchOrderChanged(self._search.order, self._search.descending).post()
        self.search_songs()


def _add_action(
    name: str,
    menu: QtWidgets.QMenu,
    slot: Callable[[], None],
    checked: bool | None = None,
) -> None:
    action = QAction(name, menu)
    if checked is not None:
        action.setCheckable(True)
        action.setChecked(checked)
    action.triggered.connect(slot)
    menu.addAction(action)
