"""Controller for the song table."""

from __future__ import annotations

import contextlib
import time
from functools import partial
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import QItemSelectionModel, Qt, QUrl
from PySide6.QtGui import QAction, QCursor
from PySide6.QtMultimedia import QMediaPlayer

from usdb_syncer import SongId, db, events, media_player, settings, sync_meta, utils
from usdb_syncer.custom_data import CustomData
from usdb_syncer.gui import events as gui_events
from usdb_syncer.gui import external_deps_dialog, previewer
from usdb_syncer.gui.custom_data_dialog import CustomDataDialog
from usdb_syncer.gui.progress import run_with_progress
from usdb_syncer.gui.song_table.column import MINIMUM_COLUMN_WIDTH, Column
from usdb_syncer.gui.song_table.table_model import TableModel
from usdb_syncer.logger import song_logger
from usdb_syncer.song_loader import DownloadManager
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.usdb_song import DownloadStatus, UsdbSong

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator
    from pathlib import Path

    from usdb_syncer.gui.mw import MainWindow


DEFAULT_COLUMN_WIDTH = 300


class SongTable:
    """Controller for the song table."""

    _search = db.SearchBuilder()
    _playing_song_id: SongId | None = None
    _next_playing_song_id: SongId | None = None

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
        self._setup_row_count_change()
        self._set_app_actions_visible()
        events.PreferencesChanged.subscribe(lambda _: self._set_app_actions_visible())
        events.SongChanged.subscribe(self._on_song_changed)
        self._setup_search_timer()
        gui_events.TreeFilterChanged.subscribe(self._on_tree_filter_changed)
        gui_events.TextFilterChanged.subscribe(self._on_text_filter_changed)
        gui_events.SavedSearchRestored.subscribe(self._on_saved_search_restored)

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        play = state == QMediaPlayer.PlaybackState.PlayingState
        if play:
            assert self._next_playing_song_id is not None
            if not (song := UsdbSong.get(self._next_playing_song_id)):
                return
            self._playing_song_id = self._next_playing_song_id
            self._next_playing_song_id = None
        else:
            assert self._playing_song_id is not None
            if not (song := UsdbSong.get(self._playing_song_id)):
                self._playing_song_id = None
                return
            self._playing_song_id = None
        with db.transaction():
            song.set_playing(play)
        events.SongChanged(song.song_id).post()

    def _on_playback_error_changed(self) -> None:
        if not self._media_player.error().value or self._next_playing_song_id is None:
            return
        logger = song_logger(self._next_playing_song_id)
        source = self._media_player.source().url()
        logger.error(f"Failed to play back source: {source}")
        logger.debug(self._media_player.errorString())

    def on_play_or_stop_sample(self) -> None:
        if song := self.current_song():
            self._play_or_stop_sample(song)

    def stop_playing_local_song(self, song: UsdbSong) -> None:
        if (
            song.song_id == self._playing_song_id
            and song.sync_meta
            and song.sync_meta.audio
        ):
            self._media_player.stop()

    def _header(self) -> QtWidgets.QHeaderView:
        return self._view.horizontalHeader()

    def reset(self) -> None:
        self._model.reset()

    def begin_reset(self) -> None:
        self._model.beginResetModel()

    def end_reset(self) -> None:
        self._model.endResetModel()

    def _on_double_click(self, idx: QtCore.QModelIndex) -> None:
        if not (song_id := self._model.ids_for_indices([idx])) or not (
            song := UsdbSong.get(song_id[0])
        ):
            return

        column = Column(idx.column())
        if (
            (sync_meta := song.sync_meta)
            and (file_path := self.file_path(sync_meta, column))
            and file_path.is_file()
        ):
            utils.open_path_or_file(file_path)
            return

        self._download([idx.row()])

    def file_path(self, sync_meta: sync_meta.SyncMeta, column: Column) -> Path | None:
        match column:
            case Column.TXT:
                return sync_meta.txt_path()
            case Column.AUDIO:
                return sync_meta.audio_path()
            case Column.VIDEO:
                return sync_meta.video_path()
            case Column.COVER:
                return sync_meta.cover_path()
            case Column.BACKGROUND:
                return sync_meta.background_path()
            case _:
                return None

    def download_selection(self) -> None:
        self._download(self._selected_rows())

    def _download(self, rows: Iterable[int]) -> None:
        external_deps_dialog.check_external_deps(
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
                self.stop_playing_local_song(song)
                previewer.Previewer.close_song(song.song_id)
                with db.transaction():
                    song.set_status(DownloadStatus.PENDING)
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
        self._view.doubleClicked.connect(lambda idx: self._on_double_click(idx))
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

        header.setSectionsMovable(True)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(MINIMUM_COLUMN_WIDTH)
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        header.setHighlightSections(False)

        for column in Column:
            if size := column.fixed_size():
                header.resizeSection(column, size)
            elif not existing_state:
                header.resizeSection(column, DEFAULT_COLUMN_WIDTH)

    def build_custom_data_menu(self) -> None:
        if not (song := self.current_song()) or not song.sync_meta:
            return
        if not (selected := [s for s in self.selected_songs() if s.sync_meta]):
            return

        def run_custom_data_dialog(key: str | None = None) -> None:
            CustomDataDialog(
                self.mw, partial(_update_custom_data, selected), key
            ).open()

        self.mw.menu_custom_data.clear()
        _add_action("New ...", self.mw.menu_custom_data, run_custom_data_dialog)
        self.mw.menu_custom_data.addSeparator()
        for key in sorted(CustomData.key_options()):
            value = song.sync_meta.custom_data.get(key)
            key_menu = QtWidgets.QMenu(key, self.mw.menu_custom_data)
            if value is not None:
                key_menu.menuAction().setCheckable(True)
                key_menu.menuAction().setChecked(True)
            self.mw.menu_custom_data.addMenu(key_menu)
            _add_action("New ...", key_menu, partial(run_custom_data_dialog, key))
            key_menu.addSeparator()
            for option in sorted(sync_meta.CustomData.value_options(key)):
                checked = option == value
                slot = partial(
                    _update_custom_data, selected, key, None if checked else option
                )
                _add_action(option, key_menu, slot, checked=checked)

    def _on_click(self, index: QtCore.QModelIndex) -> None:
        if index.column() == Column.SAMPLE_URL.value and (
            song := UsdbSong.get(self._model.ids_for_indices([index])[0])
        ):
            self._play_or_stop_sample(song)

    def _play_or_stop_sample(self, song: UsdbSong) -> None:
        if self._playing_song_id == song.song_id:
            # second play() in a row is a stop()
            self._media_player.stop()
            return
        position = 0
        if (sync_meta := song.sync_meta) and (path := sync_meta.audio_path()):
            url = QUrl.fromLocalFile(str(path.absolute()))
            if sync_meta.meta_tags.preview:
                position = int(sync_meta.meta_tags.preview * 1000)
            elif (txt_path := sync_meta.txt_path()) and (
                txt := SongTxt.try_from_file(txt_path, song_logger(song.song_id))
            ):
                if medley_start := txt.headers.medleystartbeat:
                    position = int(
                        txt.headers.gap + txt.headers.bpm.beats_to_ms(medley_start)
                    )
                elif start := txt.headers.start:
                    position = int(start * 1000)
        elif song.sample_url:
            url = QUrl(song.sample_url)
        else:
            return

        self._next_playing_song_id = song.song_id

        self._media_player.mediaStatusChanged.connect(
            lambda status: self._on_media_loaded(status, position)
        )

        self._media_player.setSource(url)
        self._media_player.play()

    def _on_media_loaded(self, status: QMediaPlayer.MediaStatus, position: int) -> None:
        """Call when media status changes.

        Sets position once media is loaded.
        """
        if status in [
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ]:
            self._media_player.setPosition(position)
            with contextlib.suppress(RuntimeError):
                self._media_player.mediaStatusChanged.disconnect()

    def save_state(self) -> None:
        settings.set_table_view_header_state(
            self.mw.table_view.horizontalHeader().saveState()
        )

    # actions

    def _on_song_changed(self, event: events.SongChanged) -> None:
        if event.song_id == self.current_song_id():
            self._on_current_song_changed()

    def _on_current_song_changed(self) -> None:
        gui_events.CurrentSongChanged(self.current_song()).post()

    def _set_app_actions_visible(self) -> None:
        for action, app in (
            (self.mw.action_open_song_in_karedi, settings.SupportedApps.KAREDI),
            (self.mw.action_open_song_in_performous, settings.SupportedApps.PERFORMOUS),
            (
                self.mw.action_open_song_in_tune_perfect,
                settings.SupportedApps.TUNE_PERFECT,
            ),
            (
                self.mw.action_open_song_in_ultrastar_manager,
                settings.SupportedApps.ULTRASTAR_MANAGER,
            ),
            (self.mw.action_open_song_in_usdx, settings.SupportedApps.USDX),
            (self.mw.action_open_song_in_vocaluxe, settings.SupportedApps.VOCALUXE),
            (
                self.mw.action_open_song_in_yass_reloaded,
                settings.SupportedApps.YASS_RELOADED,
            ),
        ):
            action.setVisible(settings.get_app_path(app) is not None)

    def delete_selected_songs(self) -> None:
        for song in self.selected_songs():
            if not song.sync_meta:
                continue
            logger = song_logger(song.song_id)
            if song.is_pinned():
                logger.info("Not trashing song folder as it is pinned.")
                continue
            self.stop_playing_local_song(song)
            previewer.Previewer.close_song(song.song_id)
            retries = 5
            while song.sync_meta.path.exists():
                try:
                    utils.trash_or_delete_path(song.sync_meta.path.parent)
                except (OSError, FileNotFoundError):
                    retries -= 1
                    if retries <= 0:
                        raise
                    time.sleep(0.1)
                    continue
                break
            with db.transaction():
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
        if (idx := self._view.selectionModel().currentIndex()).isValid() and (
            ids := self._model.ids_for_indices([idx])
        ):
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

    def _on_row_counts_changed(self, *_: Any) -> None:
        gui_events.RowCountChanged(
            rows=self._model.rowCount(),
            selected=len(self._view.selectionModel().selectedRows()),
        ).post()

    def _setup_row_count_change(self) -> None:
        self._model.modelReset.connect(self._on_row_counts_changed)
        self._model.rowsInserted.connect(self._on_row_counts_changed)
        self._model.rowsRemoved.connect(self._on_row_counts_changed)
        self._view.selectionModel().selectionChanged.connect(
            self._on_row_counts_changed
        )

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

    def _on_tree_filter_changed(self, event: gui_events.TreeFilterChanged) -> None:
        event.search.order = self._search.order
        event.search.descending = self._search.descending
        event.search.text = self._search.text
        self._search = event.search
        self.search_songs(100)

    def _on_saved_search_restored(self, event: gui_events.SavedSearchRestored) -> None:
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

    def _on_text_filter_changed(self, event: gui_events.TextFilterChanged) -> None:
        self._search.text = event.search
        self.search_songs(400)

    def _on_sort_order_changed(self, section: int, order: Qt.SortOrder) -> None:
        self._search.order = Column(section).song_order()
        self._search.descending = bool(order.value)
        gui_events.SearchOrderChanged(
            self._search.order, self._search.descending
        ).post()
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


def _update_custom_data(songs: list[UsdbSong], key: str, value: str | None) -> None:
    for song in songs:
        if song.sync_meta:
            song.sync_meta.custom_data.set(key, value)
    with db.transaction():
        UsdbSong.upsert_many(songs)
    for song in songs:
        events.SongChanged(song.song_id).post()
