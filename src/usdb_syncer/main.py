"""Main entrypoint for USDB Syncer."""

from __future__ import annotations

import contextlib
import io
import logging
import subprocess
import sys
import time
import traceback
from typing import TYPE_CHECKING, Any

from usdb_syncer import addons, db, logger, utils
from usdb_syncer.cli import CliArgs
from usdb_syncer.webserver import webserver

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import TracebackType


NOGIL_ERROR_MESSAGE = (
    "USDB Syncer does not support running without the GIL. "
    "Please use a build of Python with GIL support enabled."
)


def main() -> None:
    sys.excepthook = _excepthook
    if not getattr(sys, "_is_gil_enabled", lambda: True)():
        print(NOGIL_ERROR_MESSAGE)
        sys.exit(1)

    args = CliArgs.parse()
    args.apply()
    addons.load_all()
    utils.AppPaths.make_dirs()
    configure_logging(stderr_level=args.log_level)

    if args.subcommand == "serve":
        _run_webserver(host=args.host, port=args.port, title=args.title)
        return

    # Defer GUI imports
    from PySide6.QtCore import Qt, qInstallMessageHandler

    from usdb_syncer.gui import handle_qt_log, init_app, run_gui, run_preview

    qInstallMessageHandler(handle_qt_log)
    app = init_app()
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)

    def run_main() -> None:
        run_gui()
        app.exec()

    match args.subcommand:
        case "preview":
            if args.txt and run_preview(args.txt):
                app.exec()
        case _:
            with _with_profile(enabled=args.profile):
                run_main()


def configure_logging(stderr_level: logger.LOGLEVEL = logging.DEBUG) -> None:
    handlers: list[logging.Handler] = [
        logging.FileHandler(utils.AppPaths.log, encoding="utf-8"),
        logger.StderrHandler(level=stderr_level),
    ]
    logger.configure_logging(*handlers, formatter=logger.DEBUG_FORMATTER)


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


@contextlib.contextmanager
def _with_profile(enabled: bool = False) -> Generator[None, None, None]:
    if not enabled:
        yield
        return
    import cProfile

    logger.logger.debug("Running with profiling enabled.")
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        yield
    finally:
        profiler.disable()
        profiler.dump_stats(utils.AppPaths.profile)
        subprocess.call(["snakeviz", utils.AppPaths.profile])


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


def run_healthcheck() -> int:
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

            from usdb_syncer.gui.pdf import _ensure_fonts_registered

            _ensure_fonts_registered()

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
