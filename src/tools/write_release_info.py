"""Replaces version and commit placeholders in constants.py."""

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def main(path: Path, version: str, commit_hash: str) -> None:
    logger.info(f"Rewriting file {path}")
    old = path.read_text(encoding="utf8")
    new = old.replace('VERSION = "dev"', f'VERSION = "{version}"').replace(
        'COMMIT_HASH = "dev"', f'COMMIT_HASH = "{commit_hash}"'
    )
    path.write_text(new, encoding="utf8", newline="\n")
    logger.info(f"New content:\n{path.read_text(encoding='utf8')}")


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
    logging.basicConfig(
        level=logging.DEBUG,
        style="{",
        format="{asctime} [{levelname}] {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    cli_entry()
