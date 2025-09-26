from __future__ import annotations

import base64
import functools
import itertools
import logging
import os
import socket
import sys
from io import BytesIO
from typing import Any, ClassVar

import flask
import qrcode
import werkzeug.serving
from PySide6 import QtCore
from werkzeug.serving import WSGIRequestHandler

from usdb_syncer import SongId, db, errors, logger, utils
from usdb_syncer.usdb_song import UsdbSong


def _get_songs(request: flask.Request) -> list[UsdbSong]:
    builder = db.SearchBuilder()
    builder.statuses = [db.DownloadStatus.OUTDATED, db.DownloadStatus.SYNCHRONIZED]
    if search := request.args.get("search"):
        builder.text = search
    match request.args.get("sort_by", "artist"):
        case "artist":
            builder.order = db.SongOrder.ARTIST
        case "title":
            builder.order = db.SongOrder.TITLE
        case "year":
            builder.order = db.SongOrder.YEAR
    sort_order = request.args.get("sort_order", "asc")
    if sort_order == "desc":
        builder.descending = True
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    song_ids = db.search_usdb_songs(builder)
    songs = [
        s
        for i in itertools.islice(song_ids, offset, offset + limit)
        if (s := UsdbSong.get(i))
    ]

    return songs


def _index(title: str) -> str:
    songs = _get_songs(flask.request)
    search = flask.request.args.get("search", default="")
    sort_by = flask.request.args.get("sort_by", "artist")
    sort_order = flask.request.args.get("sort_order", "asc")
    offset = flask.request.args.get("offset", 0, type=int)
    if "HX-Request" in flask.request.headers:
        return flask.render_template(
            "songs_table.html",
            songs=songs,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
        )
    return flask.render_template(
        "index.html",
        title=title,
        qrcode=base64.b64encode(get_qrcode(address())).decode("utf-8"),
        songs=songs,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        offset=offset,
    )


def _api_songs() -> str:
    songs = _get_songs(flask.request)
    search = flask.request.args.get("search", default="")
    sort_by = flask.request.args.get("sort_by", "artist")
    sort_order = flask.request.args.get("sort_order", "asc")
    offset = flask.request.args.get("offset", 0, type=int)
    return flask.render_template(
        "songs_rows.html",
        songs=songs,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        offset=offset,
    )


def _api_mp3() -> flask.Response:
    song_id = flask.request.args.get("song_id", type=int)
    if not song_id:
        return flask.abort(400, "song_id parameter is required")
    song = UsdbSong.get(SongId(song_id))
    if not song:
        return flask.abort(404, "Song not found")
    audio_path = song.audio_path()
    if not audio_path or not audio_path.is_file():
        return flask.abort(404, "Audio file not found for this song")
    return flask.send_file(audio_path, mimetype="audio/mp3")


def _create_app(title: str) -> flask.Flask:
    app = flask.Flask(__name__)

    @app.route("/")
    def index() -> str:
        return _index(title)

    @app.route("/api/songs")
    def api_songs() -> str:
        return _api_songs()

    @app.route("/api/mp3")
    def api_mp3() -> flask.Response:
        return _api_mp3()

    @app.before_request
    def before_request() -> None:
        db.connect(utils.AppPaths.db)

    @app.teardown_request
    def teardown_request(exception: Any = None) -> None:
        db.close()

    return app


class _CustomRequestHandler(WSGIRequestHandler):
    def log(self, type: str, message: str, *args: Any) -> None:  # noqa: A002
        # don't log requests to info level
        super().log("debug", message, *args)


class _WebserverThread(QtCore.QThread):
    def __init__(self, server: werkzeug.serving.BaseWSGIServer) -> None:
        super().__init__()
        self.server = server

    def run(self) -> None:
        self.server.serve_forever()


DEFAULT_TITLE = "USDB Syncer Song Collection"


class _WebserverManager:
    _server: ClassVar[werkzeug.serving.BaseWSGIServer | None] = None
    _thread: ClassVar[QtCore.QThread | None] = None
    host: ClassVar[str] = ""
    port: ClassVar[int] = 0
    title: ClassVar[str] = DEFAULT_TITLE

    @classmethod
    def start(
        cls, host: str | None = None, port: int | None = None, title: str | None = None
    ) -> None:
        if cls._server:
            return
        if title:
            cls.title = title
        app = _create_app(cls.title)
        cls.host = host or get_local_ip()
        cls._validate_port(port)
        cls._server = werkzeug.serving.make_server(
            cls.host, cls.port, app, request_handler=_CustomRequestHandler
        )
        cls.port = cls._server.socket.getsockname()[1]
        cls._thread = _WebserverThread(cls._server)
        cls._thread.start()

    @classmethod
    def stop(cls) -> None:
        if cls._server:
            cls._server.shutdown()
            cls._server = None
        if cls._thread:
            cls._thread.quit()
            cls._thread.wait()
            cls._thread = None

    @classmethod
    def is_running(cls) -> bool:
        return bool(cls._server)

    @classmethod
    def _validate_port(cls, port: int | None) -> None:
        """
        Validate and return a usable TCP port.

        - If port is None, return 0 (OS auto-assign).
        - On Unix-like OS (Linux, macOS), disallow ports <1024 (privileged).
        - On Windows, all ports >=1 are allowed.
        - Ensures port <= 65535.
        - Raises PortInUseError if the chosen port is busy.
        """
        if port is None or port == 0:
            cls.port = 0  # OS auto-assign
            return

        if not (0 < port < 65536):
            raise errors.InvalidPortError(port)

        if sys.platform != "win32" and port < 1024:
            if hasattr(os, "geteuid") and os.geteuid() != 0:
                raise errors.PrivilegedPortError(port)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((cls.host, port))
            except OSError as e:
                raise errors.PortInUseError(port, cls.host) from e

        cls.port = port


def start(
    host: str | None = None, port: int | None = None, title: str | None = None
) -> None:
    logging.getLogger("werkzeug").setLevel(logging.DEBUG)
    _WebserverManager.start(host=host, port=port, title=title)
    logger.logger.info(f"Webserver is now running on {address()}")


def stop() -> None:
    _WebserverManager.stop()
    logger.logger.info("Webserver was stopped.")


def is_running() -> bool:
    return _WebserverManager.is_running()


def address() -> str:
    return f"http://{_WebserverManager.host}:{_WebserverManager.port}"


@functools.lru_cache(maxsize=1)
def get_qrcode(data: str) -> bytes:
    buf = BytesIO()
    qrcode.make(data, box_size=5, border=2).save(buf)
    return buf.getvalue()


def get_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    try:
        sock.connect(("10.255.255.255", 1))
        ip = sock.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        sock.close()
    return ip
