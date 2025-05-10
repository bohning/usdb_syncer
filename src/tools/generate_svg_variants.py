"""Write SVG files into resource directory, setting the fill color.

```
python -m src.tools.generate_svg_variants ~/Downloads/*.svg --fill white
```
"""

import argparse
from pathlib import Path

import defusedxml.ElementTree

RESOURCE_DIR = Path(__file__, "../../usdb_syncer/gui/resources/qt").resolve()


def main(path: Path, fill: str) -> None:
    for svg in path.parent.glob(path.name):
        tree = defusedxml.ElementTree.parse(svg)
        root = tree.getroot()
        if root is not None:
            root.set("fill", fill)
            out_path = RESOURCE_DIR / f"{svg.stem}-{fill}.svg"
            tree.write(out_path)
            print(f"Wrote '{out_path}'.")
        else:
            print(f"Failed to parse '{svg}'.")


def cli_entry() -> None:
    parser = argparse.ArgumentParser(
        description="Write SVG files into resource directory, setting the fill color."
    )
    parser.add_argument("path", help="Path to SVG; supports wildcards in the filename.")
    parser.add_argument("--fill", "-f", help="Fill color to use.")
    args = parser.parse_args()
    main(Path(args.path), args.fill)


if __name__ == "__main__":
    cli_entry()
