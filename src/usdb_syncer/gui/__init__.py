"""Contains all GUI components."""

from __future__ import annotations

import logging
import shutil
import sys
from importlib import resources as importlib_resources
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

import usdb_syncer
from usdb_syncer import (
    constants,
    data,
    db,
    errors,
    logger,
    settings,
    song_routines,
    utils,
)
from usdb_syncer import sync_meta as sync_meta
from usdb_syncer import usdb_song as usdb_song
from usdb_syncer.gui import events, hooks, progress, theme
from usdb_syncer.gui.fonts import get_version_font

if TYPE_CHECKING:
    from pathlib import Path

    # only import from gui after pyside file generation
    from usdb_syncer.gui.mw import MainWindow


SCHEMA_ERROR_MESSAGE = (
    "Your database cannot be read with this version of USDB Syncer! Either upgrade to a"
    f" more recent release, or remove the file at '{utils.AppPaths.db}' and restart to "
    "create a new database."
)


def run_gui() -> None:
    from usdb_syncer.gui.mw import MainWindow

    mw = MainWindow()
    mw_logger = _TextEditLogger(mw)
    mw_logger.setFormatter(logger.GUI_FORMATTER)
    logger.add_root_handler(mw_logger)
    mw.label_update_hint.setVisible(False)
    if not constants.IS_SOURCE:
        if version := utils.newer_version_available():
            mw.label_update_hint.setText(
                mw.label_update_hint.text().replace("VERSION", version)
            )
            mw.label_update_hint.setVisible(True)
            mw.label_update_hint.setOpenExternalLinks(True)
    else:
        logger.logger.info("Running in dev mode, skipping update check.")
    try:
        _load_main_window(mw)
    except errors.UnknownSchemaError:
        QtWidgets.QMessageBox.critical(mw, "Version conflict", SCHEMA_ERROR_MESSAGE)
        sys.exit(1)
    _maybe_copy_licenses()
    hooks.MainWindowDidLoad.call(mw)


def run_preview(txt: Path) -> bool:
    from usdb_syncer.gui.previewer import Previewer

    theme.Theme.from_settings().apply()
    return Previewer.load_txt(txt)


def _load_main_window(mw: MainWindow) -> None:
    splash = SplashScreen()
    splash.show()
    folder = settings.get_song_dir()
    db.connect(utils.AppPaths.db)
    with db.transaction():
        db.delete_session_data()

    def on_done(_result: None) -> None:
        splash.progress.reset("Setting up GUI.")
        mw.tree.populate()
        if default_search := settings.SavedSearch.get_default():
            events.SavedSearchRestored(default_search.search).post()
            logger.logger.info(f"Applied default search '{default_search.name}'.")
        mw.table.search_songs()
        mw.setWindowTitle(f"USDB Syncer ({usdb_syncer.__version__})")
        mw.show()
        logger.logger.info("Application successfully loaded.")
        theme.Theme.from_settings().apply()
        splash.finish(mw)

    progress.run_background_task(
        splash.progress,
        lambda p: song_routines.load_available_songs_and_sync_meta(folder, False, p),
        on_done=on_done,
    )


class SplashScreen(QtWidgets.QSplashScreen):
    """Splash screen shown during app startup."""

    def __init__(self) -> None:
        canvas = QtGui.QPixmap(":/splash/splash.png")
        painter = QtGui.QPainter(canvas)
        painter.setPen(QtGui.QColor(0, 174, 239))  # light blue
        font = get_version_font() or QtGui.QFont()
        font.setPixelSize(20)
        painter.setFont(font)
        painter.drawText(
            0,
            0,
            428,
            150,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            usdb_syncer.__version__,
        )
        painter.end()
        super().__init__(canvas)
        self.progress = utils.ProgressProxy("Loading data.")
        self._timer = QtCore.QTimer(self, singleShot=False, interval=100)
        self._timer.timeout.connect(self._show_message)
        self._timer.start()

    def _show_message(self) -> None:
        self.showMessage(self.progress.label(), color=Qt.GlobalColor.gray)

    def finish(self, w: QtWidgets.QWidget) -> None:
        self._timer.stop()
        self._timer.deleteLater()
        super().finish(w)
        self.deleteLater()


def init_app() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName("bohning")
    app.setApplicationName("usdb_syncer")
    app.setWindowIcon(QtGui.QIcon(":/app/appicon_128x128.png"))
    return app


def _maybe_copy_licenses() -> None:
    if not constants.IS_BUNDLE:
        return

    license_hash = (
        (importlib_resources.files(data) / "license-hash")
        .read_text(encoding="utf-8")
        .strip()
    )
    if utils.AppPaths.license_hash.exists():
        existing_hash = utils.AppPaths.license_hash.read_text(encoding="utf-8").strip()
        if existing_hash == license_hash:
            return
    logger.logger.debug("Copying license files because hash changed.")
    utils.AppPaths.license_hash.write_text(license_hash, encoding="utf-8")

    for child in utils.AppPaths.licenses.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            child.unlink(missing_ok=True)
    shutil.copytree(
        str(importlib_resources.files(data) / "licenses/"),
        utils.AppPaths.licenses,
        dirs_exist_ok=True,
    )


def handle_qt_log(mode: int, _: Any, message: str) -> None:
    """Log Qt messages to the main logger."""
    logger.logger.debug(f"Qt log message with mode {mode}: {message}")


class _LogSignal(QtCore.QObject):
    """Signal used by the logger."""

    message_level_time = QtCore.Signal(str, int, float)


class _TextEditLogger(logging.Handler):
    """Handler that logs to the GUI in a thread-safe manner."""

    def __init__(self, mw: MainWindow) -> None:
        super().__init__()
        self.signals = _LogSignal()
        self.signals.message_level_time.connect(mw.log_to_text_edit)

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        self.signals.message_level_time.emit(message, record.levelno, record.created)
