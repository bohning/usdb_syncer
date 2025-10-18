"""Manager of the main window's status bar."""

from PySide6 import QtGui, QtWidgets

from usdb_syncer import db, events
from usdb_syncer.gui import events as gui_events
from usdb_syncer.gui import icons
from usdb_syncer.gui.usdb_login_dialog import UsdbLoginDialog


class StatusBar:
    """Manager of the main window's status bar."""

    _user: str | None = None

    def __init__(self, statusbar: QtWidgets.QStatusBar) -> None:
        self._statusbar = statusbar
        self._usdb_button = QtWidgets.QPushButton(statusbar)
        self._usdb_button.setFlat(True)
        self._usdb_button.clicked.connect(lambda: UsdbLoginDialog.load(statusbar))
        self._usdb_button.setCursor(QtGui.Qt.CursorShape.PointingHandCursor)
        self._set_usdb()
        self._statusbar.addPermanentWidget(self._usdb_button)
        self._selection_label = QtWidgets.QLabel(statusbar)
        self._statusbar.addWidget(self._selection_label)
        gui_events.ThemeChanged.subscribe(self._set_usdb)
        events.LoggedInToUSDB.subscribe(self._on_usdb_login)
        gui_events.RowCountChanged.subscribe(self._on_count_changed)

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
