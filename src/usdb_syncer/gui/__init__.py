"""Contains all GUI components."""

from __future__ import annotations

import contextlib
import io
import logging
import shutil
import subprocess
import sys
import time
import traceback
from argparse import ArgumentParser
from importlib import resources as importlib_resources
from pathlib import Path
from typing import TYPE_CHECKING, Any

import attrs
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, qInstallMessageHandler

import usdb_syncer
from usdb_syncer import (
    addons,
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
from usdb_syncer.gui import events, hooks, theme
from usdb_syncer.webserver import webserver

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    # only import from gui after pyside file generation
    from usdb_syncer.gui.mw import MainWindow


SCHEMA_ERROR_MESSAGE = (
    "Your database cannot be read with this version of USDB Syncer! Either upgrade to a"
    f" more recent release, or remove the file at '{utils.AppPaths.db}' and restart to "
    "create a new database."
)
NOGIL_ERROR_MESSAGE = (
    "USDB Syncer does not support running without the GIL. "
    "Please use a build of Python with GIL support enabled."
)


@attrs.define
class CliArgs:
    """Command line arguments."""

    log_level: str = "INFO"

    reset_settings: bool = False
    subcommand: str = ""

    # Settings
    songpath: Path | None = None

    # Development
    profile: bool = False
    skip_pyside: bool = not constants.IS_SOURCE
    trace_sql: bool = False
    healthcheck: bool = False

    # preview
    txt: Path | None = None

    # webserver
    host: str | None = None
    port: int | None = None
    title: str | None = None

    @classmethod
    def parse(cls) -> CliArgs:
        parser = ArgumentParser(description="USDB Syncer")
        parser.add_argument(
            "--version", action="version", version=usdb_syncer.__version__
        )
        parser.add_argument(
            "--log-level",
            type=str.upper,
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Set the log level for stdout logging. Default is info.",
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
        dev_options.add_argument(
            "--healthcheck", action="store_true", help="Run healthcheck and exit."
        )
        if constants.IS_SOURCE:
            dev_options.add_argument(
                "--skip-pyside",
                action="store_true",
                help="Skip PySide file generation.",
            )

        subcommands = parser.add_subparsers(
            title="subcommands", description="Subcommands.", dest="subcommand"
        )
        preview = subcommands.add_parser("preview", help="Show preview for song txt.")
        preview.add_argument("txt", type=Path, help="Path to the song txt file.")

        serve = subcommands.add_parser(
            "serve", help="Launch webserver with local songs."
        )
        serve.add_argument(
            "--host",
            type=int,
            help="Host for the webservice. Default is the device's public IP address. "
            "Use 127.0.0.1 (localhost) to not be accessible by other devices "
            "on the local network.",
        )
        serve.add_argument(
            "--port",
            type=int,
            help="Port the webservice will bind to. Defaults to a random free port.",
        )
        serve.add_argument("--title", help="Title displayed at the top of the page.")

        return parser.parse_args(namespace=cls())

    def apply(self) -> None:
        if self.healthcheck:
            sys.exit(_run_healthcheck())
        if self.reset_settings:
            settings.reset()
        if self.songpath:
            settings.set_song_dir(self.songpath.resolve(), temp=True)
        if constants.IS_SOURCE and not self.skip_pyside:
            import tools.generate_pyside_files  # pylint: disable=import-outside-toplevel

            tools.generate_pyside_files.main()
        db.set_trace_sql(self.trace_sql)


def main() -> None:
    sys.excepthook = _excepthook
    if hasattr(sys, "_is_gil_enabled") and sys._is_gil_enabled() is False:  # type: ignore[attr-defined]
        print(NOGIL_ERROR_MESSAGE)
        sys.exit(1)
    qInstallMessageHandler(handle_qt_log)
    args = CliArgs.parse()
    args.apply()
    addons.load_all()
    utils.AppPaths.make_dirs()
    configure_logging(stdout_level=args.log_level)
    app = _init_app()
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)

    def run_main() -> None:
        _run_main()
        app.exec()

    match args.subcommand:
        case "preview":
            if args.txt and _run_preview(args.txt):
                app.exec()
        case "serve":
            _run_webserver(host=args.host, port=args.port, title=args.title)
        case _:
            if args.profile:
                _with_profile(run_main)
            else:
                run_main()


def configure_logging(stdout_level: logger.LOGLEVEL = logging.DEBUG) -> None:
    handlers: list[logging.Handler] = [
        logging.FileHandler(utils.AppPaths.log, encoding="utf-8"),
        logger.StdoutHandler(level=stdout_level),
    ]
    logger.configure_logging(*handlers)


def _run_main() -> None:
    from usdb_syncer.gui.mw import MainWindow

    mw = MainWindow()
    logger.add_root_handler(_TextEditLogger(mw))
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
        return
    _maybe_copy_licenses()
    hooks.MainWindowDidLoad.call(mw)


def _run_preview(txt: Path) -> bool:
    from usdb_syncer.gui.previewer import Previewer

    theme.Theme.from_settings().apply()
    return Previewer.load_txt(txt)


def _run_webserver(
    host: str | None = None, port: int | None = None, title: str | None = None
) -> None:
    webserver.start(host=host, port=port, title=title)
    logger.logger.info("Webserver is running in headless mode. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        webserver.stop()


def _excepthook(
    error_type: type[BaseException], error: BaseException, tb_type: TracebackType | None
) -> Any:
    text = "    ".join(traceback.format_exception(error_type, error, tb_type)).strip()
    logger.logger.error(f"Uncaught exception:\n    {text}")


def _with_profile(func: Callable[[], None]) -> None:
    import cProfile

    logger.logger.debug("Running with profiling enabled.")
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
        db.delete_session_data()
    song_routines.load_available_songs_and_sync_meta(folder, False)
    mw.tree.populate()
    if default_search := db.SavedSearch.get_default():
        events.SavedSearchRestored(default_search.search).post()
        logger.logger.info(f"Applied default search '{default_search.name}'.")
    mw.table.search_songs()
    splash.showMessage("Song database successfully loaded.", color=Qt.GlobalColor.gray)
    mw.setWindowTitle(f"USDB Syncer ({usdb_syncer.__version__})")
    mw.show()
    logger.logger.info("Application successfully loaded.")
    theme.Theme.from_settings().apply()
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


class StderrHandler(io.StringIO):
    """Handler for stderr that also prints to the original stderr."""

    def __init__(self) -> None:
        super().__init__()
        self._original_stderr = sys.stderr

    def write(self, s: str) -> int:
        self._original_stderr.write(s)
        return super().write(s)

    def flush(self) -> None:
        self._original_stderr.flush()
        super().flush()


def _run_healthcheck() -> int:
    """Run a healthcheck and return exit code."""
    handler = StderrHandler()
    try:
        with contextlib.redirect_stderr(handler):
            # import sounddevice properly
            from usdb_syncer.gui import previewer  # noqa: F401

            # gui modules check
            from usdb_syncer.gui.mw import MainWindow  # noqa: F401

            # database check
            db.connect(":memory:")

            # resources check
            from usdb_syncer.gui.resources.text import NOTICE

            NOTICE.read_text(encoding="utf-8")

            # sounddevice check
            import sounddevice

            sounddevice.query_devices()

    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        print(f"USDB Syncer healthcheck: failed: {e}")
        return 1
    handler.seek(0)
    for line in handler:
        if "[ERROR]" in line or "[WARNING]" in line or "[CRITICAL]" in line:
            print(f"USDB Syncer healthcheck: failed with error log: {line}")
            return 2
    print("USDB Syncer healthcheck: No problems found.")
    return 0


def handle_qt_log(mode: int, _, message: str) -> None:
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


if __name__ == "__main__":
    main()
