"""Run the app."""

import argparse
import cProfile
import logging
import subprocess
import sys
import traceback
from types import TracebackType
from typing import Any, Callable

from tools import generate_pyside_files
from usdb_syncer.utils import AppPaths


class Args:
    """Command line args for the USDB Syncer."""

    profile = False


def _excepthook(
    error_type: type[BaseException], error: BaseException, tb_type: TracebackType | None
) -> Any:
    text = "    ".join(traceback.format_exception(error_type, error, tb_type)).strip()
    logging.error(f"Uncaught exception:\n    {text}")


def _parse_args() -> Args:
    parser = argparse.ArgumentParser(
        description="An app to download and synchronize UltraStar songs."
    )
    parser.add_argument(
        "-p", "--profile", action="store_true", help="Write profiling data on exit."
    )
    return parser.parse_args(namespace=Args())


def _with_profile(func: Callable[[], None]) -> None:
    print("Running with profiling enabled.")
    profiler = cProfile.Profile()
    profiler.enable()
    func()
    profiler.disable()
    profiler.dump_stats(AppPaths.profile)
    subprocess.call(["snakeviz", AppPaths.profile])


def cli_entry(run_tools: bool = True) -> None:
    sys.excepthook = _excepthook
    args = _parse_args()
    AppPaths.make_dirs()
    if run_tools:
        generate_pyside_files()

    from usdb_syncer.gui.mw import main  # pylint: disable=import-outside-toplevel

    if args.profile:
        _with_profile(main)
    else:
        main()


if __name__ == "__main__":
    # run by the executable where PySide binaries are not available
    cli_entry(run_tools=False)
