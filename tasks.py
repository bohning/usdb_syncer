import pathlib
from typing import Literal, assert_never

from invoke import Context, task


@task
def clean(ctx: Context) -> None:
    print("Removing spec file...")
    try:
        pathlib.Path("__init__.spec").unlink()
    except FileNotFoundError:
        pass


@task(clean)
def bundle(
    ctx: Context,
    platform: Literal["Windows", "Linux", "macOS-arm64", "macOS-x64"],
    name: str,
    songlist: bool = False,
) -> None:
    print("Bundling the project...")
    # ruff: disable[E501]
    default_args: list[str] = [
        "--exclude-module _tkinter",
        "--add-data licenses:usdb_syncer/data/licenses",
        "--add-data src/usdb_syncer/db/sql:usdb_syncer/db/sql",
        "--add-data src/usdb_syncer/gui/resources/fonts:usdb_syncer/gui/resources/fonts",
        "--add-data src/usdb_syncer/gui/resources/styles:usdb_syncer/gui/resources/styles",
        "--add-data src/usdb_syncer/gui/resources/audio:usdb_syncer/gui/resources/audio",
        "--add-data src/usdb_syncer/gui/resources/text:usdb_syncer/gui/resources/text",
        "--add-data src/usdb_syncer/webserver/static:usdb_syncer/webserver/static",
        "--add-data src/usdb_syncer/webserver/templates:usdb_syncer/webserver/templates",
    ]
    # ruff: enable[E501]
    if songlist:
        default_args.append("--add-data 'artifacts/song_list.json:usdb_syncer/data'")

    match platform:
        case "Windows":
            args = [arg.replace(":", ";") for arg in default_args]
            args.append("--onefile")
            args.append("--icon src/usdb_syncer/gui/resources/qt/appicon_128x128.png")
        case "macOS-x64" | "macOS-arm64":
            args = default_args
            args.append("--windowed")
            args.append("--icon src/usdb_syncer/gui/resources/qt/appicon_128x128.png")
        case "Linux":
            args = default_args
            args.append("--onefile")
        case _:
            assert_never(platform)
    ctx.run(
        f"pyinstaller -n USDB_Syncer-{name}-{platform} {' '.join(args)} "
        "src/usdb_syncer/gui/__init__.py"
    )
