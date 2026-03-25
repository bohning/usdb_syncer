"""Stem Separation."""

from __future__ import annotations

from pathlib import Path
from threading import Semaphore
from typing import Any

from .client import JsonRpcClient

SPEC_VERSION = "1"


class SeparationManager:
    """Manages stem separation."""

    _instance: SeparationManager | None = None
    _command: list[str] | None = None
    _max_concurrent: int = 2

    def __init__(self, command: list[str], max_concurrent: int) -> None:
        self.client = JsonRpcClient(command)
        self.client.start()
        self._semaphore = Semaphore(max_concurrent)
        version = self.client.request("get_spec_version")
        if version != SPEC_VERSION:
            self.client.kill()
            msg = f"Unsupported separation manager version: {version}. Expected {SPEC_VERSION}"
            raise ValueError(msg)

    @classmethod
    def set_command(cls, command: list[str]) -> bool:
        """Set separation manager command.

        True on success, False if manager is running.
        """
        if cls._instance is not None:
            return False
        cls._command = command
        return True

    @classmethod
    def get_instance(cls) -> SeparationManager:
        """Get separation manager instance."""
        if cls._instance is None:
            if cls._command is None:
                msg = "No separation manager command set. Call set_command() first."
                raise RuntimeError(msg)
            cls._instance = SeparationManager(cls._command, cls._max_concurrent)
        return cls._instance

    def _request(self, method: str, params: dict | list | None = None) -> Any:
        if method in ("get_name", "get_version", "get_available_models"):
            return self.client.request(method, params)
        with self._semaphore:
            return self.client.request(method, params)

    def exit(self) -> None:
        """Stop separation manager."""
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

    def get_available_models(self) -> list[str]:
        """Get the models the separation provider supports."""
        return self._request("get_available_models")

    def split(
        self, input_file: Path, output_dir: Path, model: str
    ) -> tuple[Path, Path]:
        """Split a file into vocals and instrumental."""
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
