"""Generate NOTICE.txt file from licenses.json.

This script reads dependency license information from licenses.json and generates
a (hopefully) legally compliant NOTICE.txt file that lists all third-party dependencies
with their copyright notices and license information.

The full license texts are bundled in a separate 'licenses' folder alongside
NOTICE.txt.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Required, TypedDict

BUNDLE_DIR = (Path(__file__).parent.parent.parent / "bundle").resolve()
NOTICE_FILE_ROOT = Path("NOTICE.txt")
NOTICE_FILE_DATA = (
    Path(__file__).parent.parent / "usdb_syncer" / "gui" / "resources" / "text" / "NOTICE"
)  # This file is bundled with the syncer so that we can display it in the GUI.
LICENSE_JSON = BUNDLE_DIR / "resources" / "licenses.json"
LICENSES_DIR = BUNDLE_DIR / "licenses"
TEXTS_DIR = BUNDLE_DIR / "resources" / "texts"


class LicenseEntry(TypedDict, total=False):
    """Type definition for license entries in licenses.json."""

    name: Required[str]
    license: Required[str]
    copyright: Required[str]
    notice_text: str
    license_files: list[str]


def load_licenses() -> list[LicenseEntry]:
    """Load license data from licenses.json."""
    with LICENSE_JSON.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_notice_text(notice_text_name: str) -> str:
    """Load notice text from the texts directory."""
    text_file = TEXTS_DIR / notice_text_name
    if text_file.exists():
        return text_file.read_text(encoding="utf-8").strip()
    return ""


def get_license_file_references(entry: LicenseEntry) -> list[str]:
    """Get list of license files for an entry."""
    return entry.get("license_files", [])


def generate_notice_content(licenses: list[LicenseEntry]) -> str:
    """Generate the content for NOTICE.txt."""
    lines: list[str] = []

    lines.append("=" * 78)
    lines.append("THIRD-PARTY SOFTWARE NOTICES AND INFORMATION")
    lines.append("=" * 78)
    lines.append("")
    lines.append("usdb_syncer includes third-party components with separate copyright")
    lines.append(
        "notices and license terms. Your use of these components is subject to"
    )
    lines.append("the terms and conditions of the respective licenses.")
    lines.append("")
    lines.append(
        "The full text of applicable licenses can be found in the 'licenses' folder"
    )
    lines.append("distributed with usdb_syncer.")
    lines.append("")
    lines.append(f"Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    lines.append("")

    referenced_licenses: set[str] = set()

    sorted_licenses = sorted(licenses, key=lambda x: x["name"].lower())  # Sort by name

    for entry in sorted_licenses:
        name = entry["name"]
        license_type = entry["license"]
        copyright_notice = entry["copyright"]
        notice_text_name = entry.get("notice_text", "")
        license_files = get_license_file_references(entry)

        referenced_licenses.update(license_files)

        lines.append("-" * 78)
        lines.append(f"{name}")
        lines.append("-" * 78)
        lines.append("")
        lines.append(f"License: {license_type}")
        lines.append(f"{copyright_notice}")
        lines.append("")

        if notice_text_name:
            notice_text = load_notice_text(notice_text_name)
            if notice_text:
                lines.append(notice_text)
                lines.append("")

        if license_files:
            lines.append(f"View the full license text: {', '.join(license_files)}")
            lines.append("")

    lines.append("=" * 78)
    lines.append("LICENSE FILES")
    lines.append("=" * 78)
    lines.append("")
    lines.append("The following license files should be included with the distribution:")
    lines.append("")

    if LICENSES_DIR.exists():
        license_files_on_disk = sorted(
            f.name for f in LICENSES_DIR.iterdir() if f.is_file()
        )
        for license_file in license_files_on_disk:
            lines.append(f"  - {license_file}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Generate NOTICE.txt file."""
    print(f"Loading licenses from {LICENSE_JSON}")
    licenses = load_licenses()
    print(f"Found {len(licenses)} license entries")

    print("Generating NOTICE.txt content...")
    content = generate_notice_content(licenses)

    NOTICE_FILE_DATA.write_text(content, encoding="utf-8")

    content = "This file is generated automatically. Do not edit.\n\n" + content

    NOTICE_FILE_ROOT.write_text(content, encoding="utf-8")

    print(f"Sucess! Total dependencies: {len(licenses)}")


if __name__ == "__main__":
    main()
