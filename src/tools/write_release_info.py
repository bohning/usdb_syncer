"""Replaces version and commit placeholders in constants.py."""

import argparse
from pathlib import Path


def main(path: Path, version: str, commit_hash: str) -> None:
    print(f"Rewriting file {path}")
    old = path.read_text(encoding="utf8")
    new = old.replace('VERSION = "dev"', f'VERSION = "{version}"').replace(
        'COMMIT_HASH = "dev"', f'COMMIT_HASH = "{commit_hash}"'
    )
    path.write_text(new, encoding="utf8", newline="\n")
    print(f"New content:\n{path.read_text(encoding='utf8')}")


def cli_entry() -> None:
    parser = argparse.ArgumentParser(
        description="Replaces version and commit placeholders in constants.py."
    )
    parser.add_argument("--path", "-p", help="the file with the variables to replace")
    parser.add_argument("--version", "-v")
    parser.add_argument("--commit", "-c", help="commit hash")
    args = parser.parse_args()
    main(Path(args.path), args.version, args.commit)


if __name__ == "__main__":
    cli_entry()
