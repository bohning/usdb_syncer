"""Run the app."""

import argparse

from tools import generate_pyside_files


def cli_entry(run_tools: bool = True) -> None:
    parser = argparse.ArgumentParser(description="UltraStar script.")
    _args = parser.parse_args()

    if run_tools:
        generate_pyside_files()

    from usdb_syncer.gui.gui import main  # pylint: disable=import-outside-toplevel

    main()


if __name__ == "__main__":
    # run by the executable where PySide binaries are not available
    cli_entry(run_tools=True)
