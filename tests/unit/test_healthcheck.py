import contextlib
from collections.abc import Generator
from io import StringIO

import pytest

from usdb_syncer import gui


def test_healthcheck_warning_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextlib.contextmanager
    def fake_redirect_stderr(handler: StringIO) -> Generator[None]:
        handler.write("634985763094: [WARNING] test warning\n")
        with contextlib.suppress(Exception):
            yield

    monkeypatch.setattr(gui.contextlib, "redirect_stderr", fake_redirect_stderr)

    assert gui._run_healthcheck() == 2


def test_healthcheck_error_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextlib.contextmanager
    def fake_redirect_stderr(handler: StringIO) -> Generator[None]:
        handler.write("634985763094: [ERROR] test error\n")
        with contextlib.suppress(Exception):
            yield

    monkeypatch.setattr(gui.contextlib, "redirect_stderr", fake_redirect_stderr)

    assert gui._run_healthcheck() == 2


def test_healthcheck_critical_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextlib.contextmanager
    def fake_redirect_stderr(handler: StringIO) -> Generator[None]:
        handler.write("634985763094: [CRITICAL] test critical\n")
        with contextlib.suppress(Exception):
            yield

    monkeypatch.setattr(gui.contextlib, "redirect_stderr", fake_redirect_stderr)

    assert gui._run_healthcheck() == 2


def test_healthcheck_no_warning_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextlib.contextmanager
    def fake_redirect_stderr(handler: StringIO) -> Generator[None]:
        handler.write("3457634o9w7 [INFO] all good\n")
        with contextlib.suppress(Exception):
            yield

    monkeypatch.setattr(gui.contextlib, "redirect_stderr", fake_redirect_stderr)

    assert gui._run_healthcheck() == 0
