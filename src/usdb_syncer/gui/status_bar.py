"""Manager of the main window's status bar."""

from PySide6.QtGui import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QStatusBar

from usdb_syncer import db, events, utils
from usdb_syncer.gui import events as gui_events
from usdb_syncer.gui import icons
from usdb_syncer.gui.external_deps_dialog import check_external_deps
from usdb_syncer.gui.usdb_login_dialog import UsdbLoginDialog


class StatusBar:
    """Manager of the main window's status bar."""

    _user: str | None = None

    def __init__(self, statusbar: QStatusBar) -> None:
        self._statusbar = statusbar
        self.set_usdb_login_status()
        self.set_ffmpeg_status()
        self.set_deno_status()
        self.set_selection_status()
        gui_events.ThemeChanged.subscribe(self._set_usdb)
        events.LoggedInToUSDB.subscribe(self._on_usdb_login)
        gui_events.RowCountChanged.subscribe(self._on_count_changed)

    def set_usdb_login_status(self) -> None:
        self._usdb_button = QPushButton(self._statusbar)
        self._usdb_button.setFlat(True)
        self._usdb_button.clicked.connect(lambda: UsdbLoginDialog.load(self._statusbar))
        self._usdb_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_usdb()
        self._statusbar.addPermanentWidget(self._usdb_button)

    def set_ffmpeg_status(self) -> None:
        self._ffmpeg_button = QPushButton(self._statusbar)
        self._ffmpeg_button.setFlat(True)
        self._ffmpeg_button.clicked.connect(
            lambda: check_external_deps(self._statusbar, lambda: None)
        )
        self._ffmpeg_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_ffmpeg()
        self._statusbar.addPermanentWidget(self._ffmpeg_button)

    def set_deno_status(self) -> None:
        self._deno_button = QPushButton(self._statusbar)
        self._deno_button.setFlat(True)
        self._deno_button.clicked.connect(
            lambda: check_external_deps(self._statusbar, lambda: None)
        )
        self._deno_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_deno()
        self._statusbar.addPermanentWidget(self._deno_button)

    def set_selection_status(self) -> None:
        self._selection_label = QLabel(self._statusbar)
        self._statusbar.addWidget(self._selection_label)

    def _on_count_changed(self, event: gui_events.RowCountChanged) -> None:
        total = db.usdb_song_count()
        self._selection_label.setText(
            f"{event.rows} out of {total} songs shown, {event.selected} selected."
        )

    def _on_usdb_login(self, event: events.LoggedInToUSDB) -> None:
        if event.user != self._user:
            self._user = event.user
            self._set_usdb()

    def _set_usdb(self, event: gui_events.ThemeChanged | None = None) -> None:
        theme = event.theme.KEY if event else None
        if self._user:
            text = f" Welcome, {self._user}!"
            icon = icons.Icon.USDB.icon(theme)
        else:
            text = " Not logged in to USDB!"
            icon = icons.Icon.ERROR.icon(theme)
        self._usdb_button.setText(text)
        self._usdb_button.setIcon(icon)

    def _set_ffmpeg(self, event: gui_events.ThemeChanged | None = None) -> None:
        theme = event.theme.KEY if event else None
        if utils.ffmpeg_is_available():
            text = ""
            icon = icons.Icon.FFMPEG.icon(theme)
            tooltip = "FFmpeg is available."
        else:
            text = "FFmpeg missing!"
            icon = icons.Icon.FFMPEG_UNAVAILABLE.icon(theme)
            tooltip = "FFmpeg is not available! Click for more info."
        self._ffmpeg_button.setText(text)
        self._ffmpeg_button.setIcon(icon)
        self._ffmpeg_button.setToolTip(tooltip)
        self._ffmpeg_button.setFixedSize(self._ffmpeg_button.sizeHint())

    def _set_deno(self, event: gui_events.ThemeChanged | None = None) -> None:
        theme = event.theme.KEY if event else None
        if utils.deno_is_available():
            text = ""
            icon = icons.Icon.DENO.icon(theme)
            tooltip = "Deno is available."
        else:
            text = "Deno missing!"
            icon = icons.Icon.DENO_UNAVAILABLE.icon(theme)
            tooltip = "Deno is not available! Click for more info."
        self._deno_button.setText(text)
        self._deno_button.setIcon(icon)
        self._deno_button.setToolTip(tooltip)
        self._deno_button.setFixedSize(self._deno_button.sizeHint())
