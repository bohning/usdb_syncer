"""Uses uic and rcc to generate Python files from ui and qrc files."""

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    for path in Path("src/usdb_syncer/gui/forms").glob("*.ui"):
        out_path = path.with_suffix(".py")
        subprocess.run(["pyside6-uic", str(path), "-o", str(out_path)], check=True)
    for path in Path("src/usdb_syncer/gui/resources/qt").glob("*.qrc"):
        out_path = path.with_suffix(".py")
        subprocess.run(["pyside6-rcc", str(path), "-o", str(out_path)], check=True)


def cli_entry() -> None:
    parser = argparse.ArgumentParser(description="uic and rcc wrapper.")
    _args = parser.parse_args()
    main()


if __name__ == "__main__":
    cli_entry()
