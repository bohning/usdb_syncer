"""Demo add-on"""

from usdb_syncer import hooks, logger, usdb_song
from usdb_syncer.gui.mw import MainWindow


def on_window_loaded(main_window: MainWindow) -> None:
    """Add a button to the tools menu."""
    main_window.menu_tools.addAction(
        "Click Me!", lambda: logger.logger.info("Button clicked!")
    )


def on_download_finished(song: usdb_song.UsdbSong) -> None:
    """Log a message for the first finished download only."""
    logger.logger.info('Download finished: "%s"', song.title)
    hooks.SongLoaderDidFinish.unsubscribe(on_download_finished)


# this will be executed when the app is started
hooks.MainWindowDidLoad.subscribe(on_window_loaded)
hooks.SongLoaderDidFinish.subscribe(on_download_finished)
