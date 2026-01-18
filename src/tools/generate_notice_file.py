"""Generate NOTICE.txt file from licenses.json.

This script reads dependency license information from licenses.json and generates
a (hopefully) legally compliant NOTICE.txt file that lists all third-party dependencies
with their copyright notices and license information.

The full license texts are bundled in a separate 'licenses' folder alongside
NOTICE.txt.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Required, TypedDict

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
NOTICE_FILE_ROOT = PROJECT_ROOT / "NOTICE.txt"
NOTICE_FILE_DATA = (
    PROJECT_ROOT / "src" / "usdb_syncer" / "gui" / "resources" / "text" / "NOTICE"
)  # This file is bundled with the syncer so that we can display it in the GUI.
LICENSES_DIR = PROJECT_ROOT / "licenses"
TEXTS_DIR = PROJECT_ROOT / "src" / "tools" / "resources" / "texts"
LICENSE_JSON = PROJECT_ROOT / "src" / "tools" / "resources" / "licenses.json"


class LicenseEntry(TypedDict, total=False):
    """Type definition for license entries in licenses.json."""

    name: Required[str]
    license: Required[str]
    copyright: Required[str]
    notice_text: str
    license_files: list[str]


def load_licenses() -> dict[str, list[LicenseEntry]]:
    """Load license data from licenses.json."""
    with LICENSE_JSON.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_notice_text(notice_text_name: str) -> str:
    """Load notice text from the texts directory."""
    text_file = TEXTS_DIR / notice_text_name
    if not text_file.exists():
        raise FileNotFoundError(f"Notice text file not found: {text_file}")  # noqa: TRY003
    return text_file.read_text(encoding="utf-8").strip()


def get_license_file_references(entry: LicenseEntry) -> list[str]:
    """Get list of license files for an entry."""
    return entry.get("license_files", [])


def generate_header() -> list[str]:
    """Generate the header for NOTICE.txt."""
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("THIRD-PARTY SOFTWARE NOTICES AND INFORMATION")
    lines.append("=" * 78)
    lines.append("")
    lines.append("USDB Syncer includes third-party components with separate copyright")
    lines.append(
        "notices and license terms. Your use of these components is subject to"
    )
    lines.append("the terms and conditions of the respective licenses.")
    lines.append("")
    lines.append(
        "The full text of applicable licenses can be found here: $license_dir$"
    )
    lines.append("")
    lines.append(f"Generated on: {datetime.now(UTC).strftime('%Y-%m-%d')}")
    lines.append("")
    return lines


def generate_notice_content(licenses: list[LicenseEntry], section_name: str) -> str:
    """Generate the content for a section of NOTICE.txt."""
    lines: list[str] = []

    lines.append("=" * 78)
    lines.append(f"{section_name.upper()}")
    lines.append("=" * 78)
    lines.append("")

    referenced_licenses: set[str] = set()

    sorted_licenses = sorted(licenses, key=lambda x: x["name"].lower())
    full_license_files_on_disk = sorted(
        f.name for f in LICENSES_DIR.iterdir() if f.is_file()
    )

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
            for license_file in license_files:
                if license_file not in full_license_files_on_disk:
                    raise FileNotFoundError(  # noqa: TRY003
                        f"Referenced license file '{license_file}' for '{name}' not "
                        "found in licenses directory."
                    )

            lines.append(f"View the full license text: {', '.join(license_files)}")
            lines.append("")

    # Add license files section for this category
    if referenced_licenses:
        lines.append("-" * 78)
        lines.append(f"LICENSE FILES ({section_name})")
        lines.append("-" * 78)
        lines.append("")
        lines.append(
            f"The following license files apply to the {section_name.lower()} above:"
        )
        lines.append("")
        lines.extend(
            [
                f"  - $license_dir${license_file}"
                for license_file in sorted(referenced_licenses)
            ]
        )
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Generate NOTICE.txt file."""
    print(f"Loading licenses from {LICENSE_JSON}")
    licenses = load_licenses()
    header = "\n".join(generate_header())
    code_content = generate_notice_content(licenses["code"], "Code Dependencies")
    print(f"{len(licenses['code'])} code dependencies processed.")
    assets_content = generate_notice_content(licenses["assets"], "Asset Dependencies")
    print(f"{len(licenses['assets'])} asset dependencies processed.")

    content = header + "\n" + code_content + "\n\n" + assets_content

    NOTICE_FILE_DATA.write_text(content, encoding="utf-8")

    content = content.replace("$license_dir$", "licenses/")
    NOTICE_FILE_ROOT.write_text(content, encoding="utf-8")

    total_deps = len(licenses.get("code", [])) + len(licenses.get("assets", []))
    print(f"Success! Total dependencies: {total_deps}")


if __name__ == "__main__":
    main()
