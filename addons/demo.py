"""Demo add-on that makes a beep sound when the first song download has finished."""

import winsound

from usdb_syncer import hooks, usdb_song
from usdb_syncer.gui.mw import MainWindow


def on_window_loaded(main_window: MainWindow) -> None:
    """Add a button to the tools menu."""
    main_window.menu_tools.addAction("Beep", lambda: winsound.Beep(1000, 500))

def on_download_finished(song: usdb_song.UsdbSong) -> None:
    """Make a beep sound for the first finished download only."""
    winsound.Beep(1000, 500)
    hooks.SongLoaderDidFinish.unsubscribe(on_download_finished)


# this will be executed when the app is started
hooks.MainWindowDidLoad.subscribe(on_window_loaded)
hooks.SongLoaderDidFinish.subscribe(on_download_finished)
