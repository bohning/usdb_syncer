"""Add-on tests."""

import sys
import tempfile
from pathlib import Path

import pytest

from usdb_syncer import addons, hooks, utils

ADD_ON = """
from usdb_syncer import hooks

def func(arg1, arg2):
    hooks.SampleHook.unsubscribe(func)
    return 42

hooks.SampleHook.subscribe(func)
"""


class SampleHook(hooks._Hook[[str, str], int]):
    """Sample hook for testing."""


hooks.SampleHook = SampleHook  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "file", [Path("test_addon", "__init__.py"), Path("test_addon.py")]
)
def test_loading_add_on_package(file: Path) -> None:
    if "test_addon" in sys.modules:
        del sys.modules["test_addon"]
    SampleHook._subscribers.clear()  # type: ignore[misc]
    with tempfile.TemporaryDirectory() as tempdir:
        utils.AppPaths.addons = Path(tempdir, "addons")
        file = utils.AppPaths.addons / file
        file.parent.mkdir(parents=True)
        file.write_text(ADD_ON, encoding="utf-8")
        addons.load_all()
        assert len(SampleHook._subscribers) == 1  # type: ignore[misc]
        ret = list(SampleHook.call("arg1", "arg2"))
        assert ret == [42]
        assert len(SampleHook._subscribers) == 0  # type: ignore[misc]
