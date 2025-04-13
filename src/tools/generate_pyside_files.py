"""Uses uic and rcc to generate Python files from ui and qrc files."""

import argparse
import glob
import subprocess


def main() -> None:
    for path in glob.glob("src/usdb_syncer/gui/forms/*.ui"):
        out_path = path.removesuffix("ui") + "py"
        subprocess.run(["pyside6-uic", path, "-o", out_path], check=True)
    for path in glob.glob("src/usdb_syncer/gui/resources/qt/*.qrc"):
        out_path = path.removesuffix("qrc") + "py"
        subprocess.run(["pyside6-rcc", path, "-o", out_path], check=True)


def cli_entry() -> None:
    parser = argparse.ArgumentParser(description="uic and rcc wrapper.")
    _args = parser.parse_args()
    main()


if __name__ == "__main__":
    cli_entry()
