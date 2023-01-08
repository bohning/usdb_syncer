"""Run the app."""

import argparse
import logging
import sys
import traceback
from types import TracebackType
from typing import Any

from tools import generate_pyside_files


def excepthook(
    error_type: type[BaseException], error: BaseException, tb_type: TracebackType | None
) -> Any:
    text = "    ".join(traceback.format_exception(error_type, error, tb_type)).strip()
    logging.error(f"Uncaught exception:\n    {text}")


def cli_entry(run_tools: bool = True) -> None:
    sys.excepthook = excepthook

    parser = argparse.ArgumentParser(description="UltraStar script.")
    _args = parser.parse_args()

    if run_tools:
        generate_pyside_files()

    from usdb_syncer.gui.mw import main  # pylint: disable=import-outside-toplevel

    main()


if __name__ == "__main__":
    # run by the executable where PySide binaries are not available
    cli_entry(run_tools=False)
