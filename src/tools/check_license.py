"""Check or save the hash of the current license information of installed packages. This allows detecting when license information changes (for example, when a new dependency is added)."""
import argparse
import hashlib
import subprocess
from enum import Enum, auto
from pathlib import Path

PIP_LICENSES_CMD = [
    "pip-licenses",
    "--format json",
    "--with-authors",
    "--with-license-file",
    "--no-license-path",
    "--no-version",
    "--with-notice-file",
    "--with-system",
    "--from=mixed",
]
HASH_FILE = Path(__file__).parent / "resources/license-hash"


class OperationMode(Enum):
    CHECK = auto()
    SAVE = auto()


def main(mode: OperationMode) -> None:
    result = subprocess.run(PIP_LICENSES_CMD, capture_output=True, text=True)
    licenses = result.stdout

    license_hash = hashlib.sha256(licenses.encode("utf-8")).hexdigest()
    print(license_hash)
    match mode:
        case OperationMode.CHECK:
            if HASH_FILE.exists():
                saved_hash = HASH_FILE.read_text().strip()
                if saved_hash != license_hash:
                    print("License information changed!")
                    exit(1)
                else:
                    print("License information is up to date.")
            else:
                print("License hash file not found.")
                exit(1)
        case OperationMode.SAVE:
            HASH_FILE.write_text(license_hash)
            print("License hash saved.")


def cli_entry() -> None:
    parser = argparse.ArgumentParser(
        description="Check or save license information hash."
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["check", "save"],
        default="check",
        help="Operation mode: 'check' to verify hash, 'save' to store current hash.",
    )
    args = parser.parse_args()
    mode = OperationMode.CHECK if args.mode == "check" else OperationMode.SAVE
    main(mode)


if __name__ == "__main__":
    cli_entry()
