"""
Check or save the hash of the current license information of dependencies.

This script parses uv.lock to get all dependencies, then queries PyPI for
license information. This allows detecting when license information changes
(for example, when a new dependency is added or a license changes).
"""

import argparse
import hashlib
import json
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, assert_never

import requests

HASH_FILE = Path(__file__).parent / "resources/license-hash"
UV_LOCK_FILE = Path(__file__).parents[2] / "uv.lock"
PYPI_JSON_URL = "https://pypi.org/pypi/{name}/{version}/json"
MAX_WORKERS = 50


class OperationMode(Enum):
    CHECK = auto()
    SAVE = auto()
    SAVE_OVERRIDE = auto()


@dataclass
class PackageInfo:
    """License-relevant information for a package."""

    name: str
    license: str | None
    license_expression: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "license": self.license,
            "license_expression": self.license_expression,
        }


def parse_uv_lock(lock_file: Path) -> list[tuple[str, str]]:
    """Parse uv.lock file and return list of (name, version) tuples."""
    if not lock_file.exists():
        print(f"Error: uv.lock file not found at {lock_file}")
        sys.exit(1)

    with lock_file.open("rb") as f:
        lock_data = tomllib.load(f)

    packages: list[tuple[str, str]] = []
    for package in lock_data.get("package", []):
        name = package.get("name")
        version = package.get("version")
        if name and version:
            packages.append((name, version))

    return sorted(packages, key=lambda x: x[0].lower())


def fetch_pypi_info(name: str, version: str) -> PackageInfo | None:
    """Fetch license information from PyPI for a specific package version."""
    url = PYPI_JSON_URL.format(name=name, version=version)
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        info = data.get("info", {})

        return PackageInfo(
            name=name,
            license=info.get("license"),
            license_expression=info.get("license_expression"),
        )
    except requests.RequestException as e:
        print(f"Warning: Failed to fetch info for {name}=={version}: {e}")
        return None


def collect_license_info(packages: list[tuple[str, str]]) -> list[dict[str, Any]]:
    """Collect license information for all packages concurrently."""
    results: dict[tuple[str, str], dict[str, Any]] = {}

    def fetch_and_store(pkg: tuple[str, str]) -> tuple[tuple[str, str], dict[str, Any]]:
        name, version = pkg
        info = fetch_pypi_info(name, version)
        if info:
            return (pkg, info.to_dict())
        # Include minimal info even if fetch fails to detect changes
        return (
            pkg,
            {
                "name": name,
                "license": None,
                "license_expression": None,
                "fetch_failed": True,
            },
        )

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_and_store, pkg): pkg for pkg in packages}
        for future in as_completed(futures):
            pkg, data = future.result()
            results[pkg] = data

    return [results[pkg] for pkg in packages]


def compute_hash(license_info: list[dict[str, Any]]) -> str:
    """Compute SHA256 hash of the license information."""
    # Sort to ensure consistent ordering
    json_str = json.dumps(license_info, sort_keys=True, indent=2)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def main(mode: OperationMode) -> None:
    HASH_FILE.touch(exist_ok=True)
    packages = parse_uv_lock(UV_LOCK_FILE)
    print(f"Found {len(packages)} packages in uv.lock")

    license_info = collect_license_info(packages)
    license_hash = compute_hash(license_info)

    print(f"\nHash: {license_hash}")

    saved_hash = HASH_FILE.read_text(encoding="utf-8").strip()

    match mode:
        case OperationMode.CHECK:
            if saved_hash != license_hash:
                print("License information changed!")
                sys.exit(1)
            else:
                print("License information is up to date.")
        case OperationMode.SAVE:
            if saved_hash == license_hash:
                print("License information hash is already up to date.")
                return

            print(
                "Change in license information detected. Only save the hash if you have"
                " reviewed the changes and updated the NOTICE as needed."
            )
            i = input("Proceed? [y/n]: ").strip().lower()
            if i != "y":
                print("Aborting.")
                return

            HASH_FILE.write_text(license_hash)
            print("License hash saved.")
        case OperationMode.SAVE_OVERRIDE:
            HASH_FILE.write_text(license_hash)
            print("License hash saved (override).")
        case _:
            assert_never(mode)


def cli_entry() -> None:
    parser = argparse.ArgumentParser(
        description="Check or save license information hash based on uv.lock and PyPI."
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["check", "save"],
        default="check",
        help="Operation mode: 'check' to verify hash, 'save' to store current hash.",
    )
    parser.add_argument(
        "--override",
        action="store_true",
        help="If set with --mode save, saves the hash without confirmation.",
    )
    args = parser.parse_args()
    mode = OperationMode.CHECK if args.mode == "check" else OperationMode.SAVE
    if args.override and mode == OperationMode.SAVE:
        mode = OperationMode.SAVE_OVERRIDE
    main(mode)


if __name__ == "__main__":
    cli_entry()
