"""Contains all GUI components."""

from __future__ import annotations

import cProfile
import logging
import os
import subprocess
import sys
import traceback
from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable

import pkg_resources
import requests
from packaging import version
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

import tools
from usdb_syncer import (
    addons,
    constants,
    db,
    errors,
    events,
    logger,
    settings,
    song_routines,
    sync_meta,
    usdb_song,
    utils,
)

if TYPE_CHECKING:
    # only import from gui after pyside file generation
    from usdb_syncer.gui.mw import MainWindow


SCHEMA_ERROR_MESSAGE = (
    "Your database cannot be read with this version of USDB Syncer! Either upgrade to a"
    f" more recent release, or remove the file at '{utils.AppPaths.db}' and restart to "
    "create a new database."
)


def main() -> None:
    sys.excepthook = _excepthook
    utils.AppPaths.make_dirs()
    if not utils.is_bundle():
        tools.generate_pyside_files()

    if os.environ.get("PROFILE"):
        _with_profile(_run)
    else:
        _run()


def _run() -> None:
    from usdb_syncer.gui.mw import MainWindow  # pylint: disable=import-outside-toplevel

    app = _init_app()
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
    mw = MainWindow()
    logger.configure_logging(
        logging.FileHandler(utils.AppPaths.log, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
        _TextEditLogger(mw),
    )
    if utils.is_bundle():
        check_for_update()
    else:
        logging.info("Running in dev mode, skipping update check.")
    try:
        _load_main_window(mw)
    except errors.UnknownSchemaError:
        QtWidgets.QMessageBox.critical(mw, "Version conflict", SCHEMA_ERROR_MESSAGE)
        return
    addons.load_all()
    app.exec()


def get_latest_version() -> str | None:
    url = "https://api.github.com/repos/bohning/usdb_syncer/releases/latest"
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
        return response.json()["tag_name"]
    return None


def get_installed_version() -> str | None:
    try:
        return pkg_resources.get_distribution("usdb_syncer").version
    except pkg_resources.DistributionNotFound:
        return None


def check_for_update() -> None:
    latest_version = get_latest_version()
    installed_version = get_installed_version()

    if latest_version and installed_version:
        if version.parse(installed_version) < version.parse(latest_version):
            logging.warning(
                f"USDB Syncer {latest_version} is available! "
                f"(You have {installed_version}). Please download the latest release "
                "from https://github.com/bohning/usdb_syncer/releases/latest."
            )
        else:
            logging.info(f"You are running the latest Syncer version {latest_version}.")
    else:
        logging.info("Could not determine the latest version.")


def _excepthook(
    error_type: type[BaseException], error: BaseException, tb_type: TracebackType | None
) -> Any:
    text = "    ".join(traceback.format_exception(error_type, error, tb_type)).strip()
    logging.error(f"Uncaught exception:\n    {text}")


def _with_profile(func: Callable[[], None]) -> None:
    print("Running with profiling enabled.")
    profiler = cProfile.Profile()
    profiler.enable()
    func()
    profiler.disable()
    profiler.dump_stats(utils.AppPaths.profile)
    subprocess.call(["snakeviz", utils.AppPaths.profile])


def _load_main_window(mw: MainWindow) -> None:
    splash = _generate_splashscreen()
    splash.show()
    QtWidgets.QApplication.processEvents()
    splash.showMessage("Loading song database ...", color=Qt.GlobalColor.gray)
    folder = settings.get_song_dir()
    db.connect(utils.AppPaths.db)
    with db.transaction():
        song_routines.load_available_songs(force_reload=False)
        song_routines.synchronize_sync_meta_folder(folder)
        sync_meta.SyncMeta.reset_active(folder)
        usdb_song.UsdbSong.clear_cache()
        default_search = db.SavedSearch.get_default()
    mw.tree.populate()
    if default_search:
        events.SavedSearchRestored(default_search.search).post()
        logging.info(f"Applied default search '{default_search.name}'.")
    mw.table.search_songs()
    splash.showMessage("Song database successfully loaded.", color=Qt.GlobalColor.gray)
    if utils.is_bundle():
        mw.setWindowTitle(f"USDB Syncer ({get_installed_version()})")
    else:
        mw.setWindowTitle(f"USDB Syncer ({constants.VERSION})")
    mw.show()
    logging.info("Application successfully loaded.")
    splash.finish(mw)


def _generate_splashscreen() -> QtWidgets.QSplashScreen:
    canvas = QtGui.QPixmap(":/splash/splash.png")
    painter = QtGui.QPainter(canvas)
    painter.setPen(QtGui.QColor(0, 174, 239))  # light blue
    font = QtGui.QFont()
    font.setFamily("Kozuka Gothic Pro")
    font.setPointSize(24)
    painter.setFont(font)
    painter.drawText(
        0,
        0,
        428,
        140,
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        constants.VERSION,
    )
    font.setPointSize(12)
    painter.setFont(font)
    painter.drawText(
        0,
        0,
        428,
        155,
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        constants.SHORT_COMMIT_HASH,
    )
    painter.end()
    return QtWidgets.QSplashScreen(canvas)


def _init_app() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName("bohning")
    app.setApplicationName("usdb_syncer")
    app.setWindowIcon(QtGui.QIcon(":/app/appicon_128x128.png"))
    return app


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


if __name__ == "__main__":
    main()
