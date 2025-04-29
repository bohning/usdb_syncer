"""Contains all GUI components."""

from __future__ import annotations

import cProfile
import logging
import subprocess
import sys
import traceback
from argparse import ArgumentParser
from collections.abc import Callable
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any

import attrs
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

import usdb_syncer
from usdb_syncer import (
    addons,
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
from usdb_syncer.gui import hooks, theme

if TYPE_CHECKING:
    # only import from gui after pyside file generation
    from usdb_syncer.gui.mw import MainWindow


SCHEMA_ERROR_MESSAGE = (
    "Your database cannot be read with this version of USDB Syncer! Either upgrade to a"
    f" more recent release, or remove the file at '{utils.AppPaths.db}' and restart to "
    "create a new database."
)


@attrs.define
class CliArgs:
    """Command line arguments."""

    reset_settings: bool = False

    # Settings
    songpath: Path | None = None

    # Development
    profile: bool = False
    skip_pyside: bool = not utils.IS_SOURCE
    trace_sql: bool = False

    @classmethod
    def parse(cls) -> CliArgs:
        parser = ArgumentParser(description="USDB Syncer")
        parser.add_argument(
            "--version", action="version", version=usdb_syncer.__version__
        )
        parser.add_argument(
            "--reset-settings",
            action="store_true",
            help="Reset all settings to default.",
        )

        setting_overrides = parser.add_argument_group(
            "settings", "Provide temporary overrides for settings."
        )
        setting_overrides.add_argument(
            "--songpath", type=Path, help="path to the song folder"
        )

        dev_options = parser.add_argument_group("development", "Development options.")
        dev_options.add_argument(
            "--trace-sql", action="store_true", help="Trace SQL statements."
        )
        dev_options.add_argument(
            "--profile", action="store_true", help="Run with profiling."
        )
        if utils.IS_SOURCE:
            dev_options.add_argument(
                "--skip-pyside",
                action="store_true",
                help="Skip PySide file generation.",
            )

        return parser.parse_args(namespace=cls())

    def apply(self) -> None:
        if self.reset_settings:
            settings.reset()
            print("Settings reset to default.")
        if self.songpath:
            settings.set_song_dir(self.songpath.resolve(), temp=True)
        if utils.IS_SOURCE and not self.skip_pyside:
            import tools.generate_pyside_files  # pylint: disable=import-outside-toplevel

            tools.generate_pyside_files.main()
        db.set_trace_sql(self.trace_sql)


def main() -> None:
    sys.excepthook = _excepthook
    args = CliArgs.parse()
    args.apply()
    utils.AppPaths.make_dirs()
    if args.profile:
        _with_profile(_run)
    else:
        _run()


def _run() -> None:
    from usdb_syncer.gui.mw import MainWindow

    app = _init_app()
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
    mw = MainWindow()
    logger.configure_logging(
        logging.FileHandler(utils.AppPaths.log, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
        _TextEditLogger(mw),
    )
    mw.label_update_hint.setVisible(False)
    if not utils.IS_SOURCE:
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
        return
    addons.load_all()
    hooks.MainWindowDidLoad.call(mw)
    app.exec()


def _excepthook(
    error_type: type[BaseException], error: BaseException, tb_type: TracebackType | None
) -> Any:
    text = "    ".join(traceback.format_exception(error_type, error, tb_type)).strip()
    logger.logger.error(f"Uncaught exception:\n    {text}")


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
        logger.logger.info(f"Applied default search '{default_search.name}'.")
    mw.table.search_songs()
    splash.showMessage("Song database successfully loaded.", color=Qt.GlobalColor.gray)
    mw.setWindowTitle(f"USDB Syncer ({usdb_syncer.__version__})")
    mw.show()
    logger.logger.info("Application successfully loaded.")
    theme.apply_theme(
        settings.get_theme(),
        settings.get_primary_color(),
        settings.get_colored_background(),
    )
    splash.finish(mw)


def _generate_splashscreen() -> QtWidgets.QSplashScreen:
    canvas = QtGui.QPixmap(":/splash/splash.png")
    painter = QtGui.QPainter(canvas)
    painter.setPen(QtGui.QColor(0, 174, 239))  # light blue
    font = QtGui.QFont()
    font.setFamily("Kozuka Gothic Pro")
    font.setPointSize(20)
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
