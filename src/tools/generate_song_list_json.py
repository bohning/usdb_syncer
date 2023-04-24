"""Build a JSON file with all available songs from USDB."""

import argparse
from pathlib import Path

from PySide6.QtWidgets import QApplication

from usdb_syncer import settings, song_list_fetcher


def main(target: Path, user: str, password: str) -> None:
    # required for settings to work
    app = QApplication()
    app.setOrganizationName("bohning")
    app.setApplicationName("usdb_syncer")
    settings.set_usdb_auth(user, password)
    songs = song_list_fetcher.get_available_songs(force_reload=True)
    song_list_fetcher.dump_available_songs(songs, target)


def cli_entry() -> None:
    parser = argparse.ArgumentParser(
        description="Fetches all songs from USDB and stores them in a JSON file."
    )
    parser.add_argument("--target", "-t", help="where to store the output file")
    parser.add_argument("--user", "-u", help="a USDB username")
    parser.add_argument("--password", "-p", help="the USDB user's password")
    args = parser.parse_args()
    main(Path(args.target), args.user, args.password)


if __name__ == "__main__":
    cli_entry()
