"""Add-on tests."""

import sys
import tempfile
from pathlib import Path

import pytest

from usdb_syncer import addons, hooks, utils

ADD_ON = """
from usdb_syncer import hooks

def func(song):
    hooks.SongLoaderDidFinish.unsubscribe(func)

hooks.SongLoaderDidFinish.subscribe(func)
"""


# pylint: disable=protected-access
@pytest.mark.parametrize(
    "file", [Path("test_addon", "__init__.py"), Path("test_addon.py")]
)
def test_loading_add_on_package(file: Path) -> None:
    if "test_addon" in sys.modules:
        del sys.modules["test_addon"]
    with tempfile.TemporaryDirectory() as tempdir:
        utils.AppPaths.addons = Path(tempdir, "addons")
        file = utils.AppPaths.addons / file
        file.parent.mkdir(parents=True)
        file.write_text(ADD_ON, encoding="utf-8")
        addons.load_all()
        assert len(hooks.SongLoaderDidFinish._subscribers) == 1
        hooks.SongLoaderDidFinish.call({})  # type:ignore
        assert len(hooks.SongLoaderDidFinish._subscribers) == 0
