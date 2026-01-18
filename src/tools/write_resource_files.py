"""Write resource names into source files.

```
python -m src.tools.write_resource_files
```
"""

import argparse
from pathlib import Path

RESOURCE_DIR = Path(__file__, "../../usdb_syncer/gui/resources").resolve()

_FILE_HEADER = f'''"""File was generated using `{Path(__file__).name}`."""

from importlib import resources

'''
_LINE_TEMPLATE = '{var} = resources.files(__package__) / "{fname}"\n'


def main() -> None:
    dirs = [d for d in RESOURCE_DIR.iterdir() if d.is_dir() and d.name != "qt"]
    for dir_ in dirs:
        files = [f.name for f in dir_.iterdir() if f.is_file() and f.suffix != ".py"]
        out_path = dir_ / "__init__.py"
        with (out_path).open("w", encoding="utf-8", newline="\n") as out:
            out.write(_FILE_HEADER)
            out.writelines(
                _LINE_TEMPLATE.format(var=_var_name(f), fname=f) for f in files
            )
        print(f"Wrote {len(files)} entries to '{out_path}'.")


def _var_name(fname: str) -> str:
    return fname.replace(".", "_").replace(" ", "_").replace("-", "_").upper()


def cli_entry() -> None:
    parser = argparse.ArgumentParser(
        description="Write resource names into source files."
    )
    _args = parser.parse_args()
    main()


if __name__ == "__main__":
    cli_entry()
