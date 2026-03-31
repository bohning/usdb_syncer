"""Stem Separation."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from usdb_syncer import logger

from .client import JsonRpcClient

SPEC_VERSION = "1"


class _ResizableSemaphore:
    """A semaphore that can be resized at runtime.

    This allows us to limit the number of concurrent separation operations, and to update that limit globally at runtime when the user changes it in the settings.
    """

    def __init__(self, max_count: int) -> None:
        self._cond = threading.Condition(threading.Lock())
        self._max = max_count
        self._value = max_count

    def acquire(self) -> None:
        with self._cond:
            while self._value <= 0:
                self._cond.wait()
            self._value -= 1

    def release(self) -> None:
        with self._cond:
            if self._value < self._max:
                self._value += 1
            self._cond.notify()

    def resize(self, new_max: int) -> None:
        with self._cond:
            delta = new_max - self._max
            self._max = new_max
            self._value += delta
            if delta > 0:
                self._cond.notify_all()

    def __enter__(self) -> _ResizableSemaphore:
        self.acquire()
        return self

    def __exit__(self, *args: object) -> None:
        self.release()


# A global seemed the simplest way to enforce the limit everywhere. Should only be accessed in this module
_semaphore = _ResizableSemaphore(1)


def set_max_concurrent(n: int) -> None:
    """Update the global concurrency limit for split operations."""
    _semaphore.resize(n)


class SeparationManager:
    """Manages stem separation."""

    def __init__(
        self, command: list[str], logger: logger.Logger = logger.logger.logger
    ) -> None:
        self.logger = logger
        self.logger.debug("Creating new separation manager.")
        self.client = JsonRpcClient(command)
        self.client.start()
        version = self.client.request("get_spec_version")
        if version != SPEC_VERSION:
            self.client.kill()
            msg = f"Unsupported separation manager version: {version}. Expected {SPEC_VERSION}"
            raise ValueError(msg)

    def close(self) -> None:
        """Kill the subprocess."""
        self.client.kill()

    def _request(self, method: str, params: dict | list | None = None) -> Any:
        if method in ("get_name", "get_version", "get_available_models"):
            return self.client.request(method, params)
        with _semaphore:
            self.logger.debug(f"Acquired semaphore for {method}.")
            return self.client.request(method, params)

    def exit(self) -> None:
        """Request stop of separation provider."""
        self._request("exit")

    def get_name(self) -> str:
        """Get name of separation provider."""
        return self._request("get_name")

    def get_version(self) -> str:
        """Get version of separation provider."""
        return self._request("get_version")

    def is_gpu_accelerated(self) -> bool:
        """Check if separation is GPU accelerated."""
        return self._request("is_gpu_accelerated")

    def get_available_models(self) -> dict[str, str]:
        """Get the models the separation provider supports."""
        return self._request("get_available_models")

    def split(
        self, input_file: Path, output_dir: Path, model: str
    ) -> tuple[Path, Path]:
        """Split a file into vocals and instrumental."""
        self.logger.debug(f"Splitting {input_file} into vocals and instrumental.")
        out = self._request(
            "split",
            {
                "input_file": str(input_file),
                "output_dir": str(output_dir),
                "model": model,
            },
        )
        return Path(output_dir, out["output_vocals"]), Path(
            output_dir, out["output_instrumental"]
        )
