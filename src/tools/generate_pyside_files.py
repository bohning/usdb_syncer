"""Uses uic and rcc to generate Python files from ui and qrc files."""

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    ui_py_files = []
    rc_py_files = []
    for path in Path("src/usdb_syncer/gui/forms").glob("*.ui"):
        out_path = path.with_suffix(".py")
        subprocess.run(["pyside6-uic", str(path), "-o", str(out_path)], check=True)
        ui_py_files.append(out_path)
    for path in Path("src/usdb_syncer/gui/resources/qt").glob("*.qrc"):
        out_path = path.with_suffix(".py")
        subprocess.run(["pyside6-rcc", str(path), "-o", str(out_path)], check=True)
        rc_py_files.append(out_path)
    _fix_resource_imports(ui_py_files, rc_py_files)


def _fix_resource_imports(ui_py_files: list[Path], rc_py_files: list[Path]) -> None:
    for rc_file in rc_py_files:
        for ui_file in ui_py_files:
            content = ui_file.read_text(encoding="utf-8")
            content = content.replace(
                f"import {rc_file.stem}_rc",
                f"from usdb_syncer.gui.resources.qt import {rc_file.stem} as "
                f"{rc_file.stem}_rc",
            )
            ui_file.write_text(content, encoding="utf-8")


def cli_entry() -> None:
    parser = argparse.ArgumentParser(description="uic and rcc wrapper.")
    _args = parser.parse_args()
    main()


if __name__ == "__main__":
    cli_entry()
