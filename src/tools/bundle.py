import argparse
import subprocess
from enum import Enum
from typing import assert_never


class OS(Enum):
    WINDOWS = "Windows"
    LINUX = "Linux"
    MACOS_ARM64 = "macOS-arm64"
    MACOS_X64 = "macOS-x64"


def bundle(platform: OS, name: str, with_songlist: bool = False) -> None:
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
        case OS.WINDOWS:
            args.extend([
                "--onefile",
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
                f"USDB_Syncer-{name}-{platform.value}",
                *args,
                "src/usdb_syncer/gui/__init__.py",
            ],
            check=True,
        )
    except FileNotFoundError as e:
        e.add_note("hint: make sure pyinstaller is available")
        raise


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
        "--name",
        "-n",
        type=str,
        required=True,
        help="Name of the bundle (could be a version)",
    )
    parser.add_argument(
        "--with-songlist",
        action="store_true",
        default=False,
        help="Include the song list in the bundle.",
    )
    args = parser.parse_args()
    platform = OS(args.platform)
    bundle(platform, args.name, args.with_songlist)


if __name__ == "__main__":
    cli_entry()
