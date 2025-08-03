from __future__ import annotations

import itertools
import logging
from typing import Any, ClassVar

import attrs
import flask
import werkzeug.serving
from PySide6 import QtCore
from werkzeug.serving import WSGIRequestHandler

from usdb_syncer import SongId, db, utils
from usdb_syncer.usdb_song import UsdbSong


@attrs.define
class SongRecord:
    song_id: SongId
    artist: str
    title: str
    year: int | None
    preview_offset: float

    @classmethod
    def from_usdb_song(cls, song: UsdbSong) -> SongRecord:
        return cls(
            song_id=song.song_id,
            artist=song.artist,
            title=song.title,
            year=song.year,
            preview_offset=song.sync_meta.meta_tags.preview
            if song.sync_meta
            and song.sync_meta.meta_tags
            and song.sync_meta.meta_tags.preview
            else 0.0,
        )


def _get_songs(request: flask.Request) -> list[UsdbSong]:
    search = db.SearchBuilder()
    search.statuses = [db.DownloadStatus.OUTDATED, db.DownloadStatus.SYNCHRONIZED]
    if artist_filter := request.args.get("artist_filter"):
        search.artists.append(artist_filter)
    if song_filter := request.args.get("song_filter"):
        search.titles.append(song_filter)
    match request.args.get("sort_by", "artist"):
        case "artist":
            search.order = db.SongOrder.ARTIST
        case "title":
            search.order = db.SongOrder.TITLE
        case "year":
            search.order = db.SongOrder.YEAR
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    song_ids = db.search_usdb_songs(search)
    songs = [
        s
        for i in itertools.islice(song_ids, offset, offset + limit)
        if (s := UsdbSong.get(i))
    ]

    return songs


def create_app() -> flask.Flask:
    app = flask.Flask(__name__)

    @app.route("/")
    def index() -> str:
        songs = _get_songs(flask.request)
        artist_filter = flask.request.args.get("artist_filter", default="")
        song_filter = flask.request.args.get("song_filter", default="")
        sort_by = flask.request.args.get("sort_by", "artist")
        return flask.render_template(
            "index.html",
            songs=songs,
            artist_filter=artist_filter,
            song_filter=song_filter,
            sort_by=sort_by,
        )

    @app.route("/api/songs")
    def api_songs() -> dict:
        songs = _get_songs(flask.request)
        # Add preview offset to each song for the frontend
        songs_with_preview = []
        for song in songs:
            song_dict = {
                "song_id": song.song_id,
                "artist": song.artist,
                "title": song.title,
                "year": song.year,
                "preview_offset": song.sync_meta.meta_tags.preview
                if song.sync_meta
                and song.sync_meta.meta_tags
                and song.sync_meta.meta_tags.preview
                else 0,
            }
            songs_with_preview.append(song_dict)
        return {"songs": [attrs.asdict(SongRecord.from_usdb_song(s)) for s in songs]}

    @app.route("/api/mp3")
    def api_mp3():
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


class _WebserverManager:
    _server: ClassVar[werkzeug.serving.BaseWSGIServer | None] = None
    _thread: ClassVar[QtCore.QThread | None] = None
    host: ClassVar[str] = ""
    port: ClassVar[int] = 0

    @classmethod
    def start(cls, host: str, port: int) -> None:
        if cls._server:
            return
        cls.host = host
        cls.port = port
        app = create_app()
        cls._server = werkzeug.serving.make_server(
            host, port, app, request_handler=_CustomRequestHandler
        )
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


def start(host="127.0.0.1", port=5000) -> None:
    logging.getLogger("werkzeug").setLevel(logging.DEBUG)
    _WebserverManager.start(host, port)


def stop() -> None:
    _WebserverManager.stop()
