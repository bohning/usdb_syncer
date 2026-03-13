"""Command line arguments."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import attrs

import usdb_syncer
from usdb_syncer import constants, db, settings


@attrs.define
class CliArgs:
    """Command line arguments."""

    log_level: str = "INFO"

    reset_settings: bool = False
    subcommand: str = ""

    # Settings
    songpath: Path | None = None

    # Development
    profile: bool = False
    skip_pyside: bool = not constants.IS_SOURCE
    trace_sql: bool = False
    healthcheck: bool = False

    # preview
    txt: Path | None = None

    # webserver
    host: str | None = None
    port: int | None = None
    title: str | None = None

    @classmethod
    def parse(cls) -> CliArgs:
        parser = ArgumentParser(description="USDB Syncer")
        parser.add_argument(
            "--version", action="version", version=usdb_syncer.__version__
        )
        parser.add_argument(
            "--log-level",
            type=str.upper,
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Set the log level for stderr logging. Default is info.",
        )
        parser.add_argument(
            "--reset-settings",
            action="store_true",
            help="Reset all settings to default.",
        )

        setting_overrides = parser.add_argument_group(
            "settings", "Provide temporary overrides for settings."
        )
        setting_overrides.add_argument(
            "--songpath", type=Path, help="path to the song folder"
        )

        dev_options = parser.add_argument_group("development", "Development options.")
        dev_options.add_argument(
            "--trace-sql", action="store_true", help="Trace SQL statements."
        )
        dev_options.add_argument(
            "--profile", action="store_true", help="Run with profiling."
        )
        dev_options.add_argument(
            "--healthcheck", action="store_true", help="Run healthcheck and exit."
        )
        if constants.IS_SOURCE:
            dev_options.add_argument(
                "--skip-pyside",
                action="store_true",
                help="Skip PySide file generation.",
            )

        subcommands = parser.add_subparsers(
            title="subcommands", description="Subcommands.", dest="subcommand"
        )
        preview = subcommands.add_parser("preview", help="Show preview for song txt.")
        preview.add_argument("txt", type=Path, help="Path to the song txt file.")

        serve = subcommands.add_parser(
            "serve", help="Launch webserver with local songs."
        )
        serve.add_argument(
            "--host",
            type=int,
            help="Host for the webservice. Default is the device's public IP address. "
            "Use 127.0.0.1 (localhost) to not be accessible by other devices "
            "on the local network.",
        )
        serve.add_argument(
            "--port",
            type=int,
            help="Port the webservice will bind to. Defaults to a random free port.",
        )
        serve.add_argument("--title", help="Title displayed at the top of the page.")

        return parser.parse_args(namespace=cls())

    def apply(self) -> None:
        if self.healthcheck:
            # Import here to avoid circular imports.
            from usdb_syncer.main import run_healthcheck

            sys.exit(run_healthcheck())
        if self.reset_settings:
            settings.reset()
        if self.songpath:
            settings.set_song_dir(self.songpath.resolve(), temp=True)
        if constants.IS_SOURCE and not self.skip_pyside:
            import tools.generate_pyside_files  # pylint: disable=import-outside-toplevel

            tools.generate_pyside_files.main()
        db.set_trace_sql(self.trace_sql)
