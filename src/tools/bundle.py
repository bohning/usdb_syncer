import argparse
import shutil
import subprocess
from enum import Enum
from pathlib import Path
from typing import assert_never


class OS(Enum):
    WINDOWS_PORTABLE = "Windows-portable"
    WINDOWS_INSTALL = "Windows-install"
    LINUX = "Linux"
    MACOS_ARM64 = "macOS-arm64"
    MACOS_X64 = "macOS-x64"


def bundle(platform: OS, version: str, with_songlist: bool = False) -> None:
    """Bundle the project for the given platform."""
    print("Bundling the project...")
    # fmt: off
    args: list[str] = [
        "--exclude-module", "_tkinter",
        "--add-data", "licenses:usdb_syncer/data/licenses",
        "--add-data", "src/usdb_syncer/db/sql:usdb_syncer/db/sql",
        "--add-data", "src/usdb_syncer/gui/resources/fonts:usdb_syncer/gui/resources/fonts",  # noqa: E501
        "--add-data", "src/usdb_syncer/gui/resources/styles:usdb_syncer/gui/resources/styles",  # noqa: E501
        "--add-data", "src/usdb_syncer/gui/resources/audio:usdb_syncer/gui/resources/audio",  # noqa: E501
        "--add-data", "src/usdb_syncer/gui/resources/text:usdb_syncer/gui/resources/text",  # noqa: E501
        "--add-data", "src/usdb_syncer/webserver/static:usdb_syncer/webserver/static",
        "--add-data", "src/usdb_syncer/webserver/templates:usdb_syncer/webserver/templates",  # noqa: E501
    ]
    # fmt: on
    if with_songlist:
        args.extend(["--add-data", "artifacts/song_list.json:usdb_syncer/data"])

    match platform:
        case OS.WINDOWS_PORTABLE:
            args.extend([
                "--onefile",
                "--icon",
                "src/usdb_syncer/gui/resources/qt/appicon_128x128.png",
            ])
        case OS.WINDOWS_INSTALL:
            args.extend([
                "--icon",
                "src/usdb_syncer/gui/resources/qt/appicon_128x128.png",
            ])
        case OS.MACOS_ARM64 | OS.MACOS_X64:
            args.extend([
                "--windowed",
                "--icon",
                "src/usdb_syncer/gui/resources/qt/appicon_128x128.png",
            ])
        case OS.LINUX:
            args.extend(["--onefile"])
        case _:
            assert_never(platform)
    try:
        subprocess.run(
            [
                "pyinstaller",
                "-n",
                f"USDB_Syncer-{version}-{platform.value}",
                *args,
                "src/usdb_syncer/gui/__init__.py",
            ],
            check=True,
        )
    except FileNotFoundError as e:
        e.add_note("hint: make sure pyinstaller is available")
        raise
    print("Executable(s) built successfully!")
    print("Starting platform-specific bundling...")

    match platform:
        case OS.WINDOWS_INSTALL:
            build_win_installer(version)
        case OS.MACOS_ARM64 | OS.MACOS_X64:
            build_mac_pkg(version, platform)
        case OS.WINDOWS_PORTABLE | OS.LINUX:
            pass
        case _:
            assert_never(platform)
    print("Bundling completed!")


def build_win_installer(version: str) -> None:
    """Build the Windows installer using Inno Setup."""
    root_dir = Path.cwd()
    iss_file = root_dir / "installer" / "wininstaller.iss"
    try:
        subprocess.run(
            ["iscc", f"/DVersion={version}", f"/DSourceDir={root_dir}", str(iss_file)],
            check=True,
        )
    except FileNotFoundError as e:
        e.add_note("hint: make sure Inno Setup Compiler (iscc) is available")
        raise
    shutil.move(
        root_dir / "installer" / "Output" / f"USDB_Syncer-{version}-Windows-Setup.exe",
        root_dir / "dist" / f"USDB_Syncer-{version}-Windows-Setup.exe",
    )
    print("Windows installer built successfully!")


def build_mac_pkg(version: str, target: OS) -> None:
    """Build macOS dmg using create-dmg (must be installed)."""
    assert target in {OS.MACOS_ARM64, OS.MACOS_X64}
    name = f"USDB_Syncer-{version}-{target.value}"
    try:
        # fmt: off
        subprocess.run(
            [
            "create-dmg",
            "--volname", "USDB Syncer",
            "--volicon", "src/usdb_syncer/gui/resources/qt/appicon_128x128.png",
            "--window-pos", "200", "120",
            "--window-size", "600", "300",
            "--icon-size", "128",
            "--text-size", "14",
            "--icon", f"{name}.app", "175", "120",
            "--hide-extension", f"{name}.app",
            "--app-drop-link", "425", "120",
            "--hdiutil-quiet",
            "--no-internet-enable",
            f"dist/{name}.dmg",
            f"dist/{name}.app",
            ],
            check=True)
        # fmt: on
    except FileNotFoundError as e:
        e.add_note("hint: make sure create-dmg is available")
        raise
    print("DMG built successfully!")


def cli_entry() -> None:
    parser = argparse.ArgumentParser(description="Bundle the project.")
    parser.add_argument(
        "platform",
        type=str,
        choices=[os.value for os in OS],
        help="Target platform for bundling. Note that this will not cross-compile. It "
        "should be set to the current platform.",
    )
    parser.add_argument(
        "--version",
        "-v",
        type=str,
        required=False,
        help="Version string. If not set, uses syncer's current version.",
    )
    parser.add_argument(
        "--with-songlist",
        action="store_true",
        default=False,
        help="Include the song list in the bundle.",
    )
    args = parser.parse_args()
    if not args.version:
        import usdb_syncer

        args.version = usdb_syncer.__version__
    bundle(OS(args.platform), args.version, args.with_songlist)


if __name__ == "__main__":
    cli_entry()
