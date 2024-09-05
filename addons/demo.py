"""Demo add-on that makes a beep sound when the first song download has finished."""

import winsound

from usdb_syncer import hooks, usdb_song


def on_download_finished(song: usdb_song.UsdbSong) -> None:
    """Make a beep sound for the first finished download only."""
    winsound.Beep(1000, 500)
    hooks.SongLoaderDidFinish.unsubscribe(on_download_finished)


# this will be executed when the app is started
hooks.SongLoaderDidFinish.subscribe(on_download_finished)
