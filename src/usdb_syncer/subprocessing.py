"""Subprocessing utilities. Affects mainly running commands from pyinstaller bundles on Linux."""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import threading
import types
import webbrowser
from typing import TYPE_CHECKING, Any

from usdb_syncer import constants

if TYPE_CHECKING:
    from collections.abc import Iterator

APPLY_CLEAN_ENV = constants.IS_BUNDLE and sys.platform == "linux"

BAD_ENVS = ["LD_LIBRARY_PATH", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"]


def run_clean(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    """Run a command with a cleaned environment."""
    kwargs.pop("env", None)
    return subprocess.run(command, env=get_env_clean(), **kwargs)


def popen_clean(command: list[str], **kwargs: Any) -> subprocess.Popen:
    """Run a command with a cleaned environment."""
    kwargs.pop("env", None)
    return subprocess.Popen(command, env=get_env_clean(), **kwargs)


environ_lock = threading.Lock()


@contextlib.contextmanager
def unsafe_clean() -> Iterator[None]:
    """Temporarily set a cleaned environment for subprocess calls. Uses a lock for thread safety. Use sparingly."""
    if not APPLY_CLEAN_ENV:
        yield
        return
    environ_lock.acquire()
    original_env = get_env()
    safe_env = get_env_clean()
    os.environ.clear()
    os.environ.update(safe_env)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original_env)
        environ_lock.release()


def patch_webbrowser_subprocess() -> None:
    """Patch the `webbrowser` module to use `run_clean` for subprocess calls."""
    if not APPLY_CLEAN_ENV:
        return

    proxy_subprocess = types.ModuleType("proxy_subprocess")
    proxy_subprocess.__dict__.update(subprocess.__dict__)
    proxy_subprocess.run = run_clean  # type: ignore[assignment, attr-defined]
    proxy_subprocess.Popen = popen_clean  # type: ignore[assignment, attr-defined]
    webbrowser.subprocess = proxy_subprocess  # type: ignore[attr-defined]


def get_env() -> dict[str, str]:
    """Get a copy of the current environment variables."""
    return os.environ.copy()


def get_env_clean() -> dict[str, str]:
    """Get a cleaned copy of the current environment variables."""
    env = get_env()
    if not APPLY_CLEAN_ENV:
        return env
    for bad_env in BAD_ENVS:
        if orig_bad_env := env.get(f"{bad_env}_ORIG", None):
            env[bad_env] = orig_bad_env
        else:
            # If bad env is not set, remove
            env.pop(bad_env, None)
    return env
