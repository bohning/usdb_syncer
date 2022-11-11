"""Run the app."""

import argparse

from tools import generate_pyside_files


def cli_entry() -> None:
    parser = argparse.ArgumentParser(description="UltraStar script.")
    _args = parser.parse_args()

    generate_pyside_files()

    from usdb_dl.gui.gui import main  # pylint: disable=import-outside-toplevel

    main()


if __name__ == "__main__":
    cli_entry()
