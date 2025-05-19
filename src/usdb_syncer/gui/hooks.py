"""Hooks called from the GUI that add-ons can subscribe to."""

from __future__ import annotations

from typing import TYPE_CHECKING

from usdb_syncer import hooks

if TYPE_CHECKING:
    from usdb_syncer.gui.mw import MainWindow


class MainWindowDidLoad(hooks._Hook):
    """Called after the main window has loaded."""

    @classmethod
    def call(cls, main_window: MainWindow) -> None:
        super().call(main_window)
