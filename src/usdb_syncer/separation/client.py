"""JSON-RPC 2.0 client.

json is line delimited.
"""

import concurrent.futures
import contextlib
import itertools
import json
import subprocess
import threading
from typing import Any

from usdb_syncer import subprocessing
from usdb_syncer.errors import CommunicationError, JsonRpcError


class JsonRpcClient:
    """A JSON-RPC 2.0 client.

    The advantage of this over a package is that we can handle spec specific stuff right here (like using line-delimited json). json-rpc is a very simple protocol.
    """

    def __init__(self, command: list[str]) -> None:
        self.command = command
        self._process: subprocess.Popen | None = None
        self._id_generator = itertools.count(1)
        self._pending: dict[int, concurrent.futures.Future] = {}
        self._pending_lock = threading.Lock()
        self._write_lock = threading.Lock()

    def start(self) -> None:
        """Begin the mainloop in the background."""
        self._process = subprocess.Popen(
            self.command,
            env=subprocessing.get_env_clean(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()

    def _handle_response(self, response: dict[str, Any]) -> None:
        if "id" not in response:
            return
        with self._pending_lock:
            if response["id"] not in self._pending:
                return
            future = self._pending[response["id"]]

        if not future.done():
            if "error" in response:
                error = response["error"]
                future.set_exception(
                    JsonRpcError(
                        error.get("code", 0),
                        error.get("message", "Unknown error"),
                        error.get("data"),
                    )
                )
            else:
                future.set_result(response.get("result"))

    def _read_loop(self) -> None:
        if not self._process or not self._process.stdout:
            return

        for line in self._process.stdout:
            if not line:
                break
            with contextlib.suppress(json.JSONDecodeError):
                self._handle_response(json.loads(line))

        # process has died or closed stdout
        with self._pending_lock:
            pending = list(self._pending.values())

        for future in pending:
            if not future.done():
                msg = "Process terminated"
                future.set_exception(CommunicationError(msg))

    def request(self, method: str, params: dict | list | None = None) -> Any:
        if not self._process or not self._process.stdin:
            msg = "Client not started"
            raise CommunicationError(msg)

        with self._pending_lock:
            request_id = next(self._id_generator)
            future: concurrent.futures.Future = concurrent.futures.Future()
            self._pending[request_id] = future

        try:
            payload = {"jsonrpc": "2.0", "method": method, "id": request_id}
            if params is not None:
                payload["params"] = params

            data = json.dumps(payload) + "\n"
            with self._write_lock:
                self._process.stdin.write(data.encode("utf-8"))
                self._process.stdin.flush()

            return future.result()
        finally:
            with self._pending_lock:
                self._pending.pop(request_id, None)

    def kill(self) -> None:
        if self._process:
            self._process.kill()
            self._process = None
