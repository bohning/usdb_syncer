import itertools
import os
import socket
from typing import ClassVar

import flask
import werkzeug.serving
from PySide6 import QtCore, QtGui, QtWidgets

from usdb_syncer import db, utils
from usdb_syncer.usdb_song import UsdbSong

QR_URL = os.getenv("QR_URL")
SONGFOLDER = os.getenv("SONGFOLDER")
SONG_DB = os.getenv("SONG_DB")
ULTRASTAR_DB = os.getenv("ULTRASTAR_DB")


# Update the handle_song_request function
def handle_song_request(request: flask.Request):
    search = db.SearchBuilder()
    search.statuses = [db.DownloadStatus.OUTDATED, db.DownloadStatus.SYNCHRONIZED]
    if artist_filter := request.args.get("artist_filter"):
        search.artists.append(artist_filter)
    if song_filter := request.args.get("song_filter"):
        search.artists.append(song_filter)
    match request.args.get("sort_by", "artist"):
        case "artist":
            search.order = db.SongOrder.ARTIST
        case "title":
            search.order = db.SongOrder.TITLE
        case "year":
            search.order = db.SongOrder.YEAR
    limit = int(request.args.get("limit", 1000))
    offset = int(request.args.get("offset", 0))

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
    def index():
        songs = handle_song_request(flask.request)
        artist_filter = flask.request.args.get("artist_filter", default="")
        song_filter = flask.request.args.get("song_filter", default="")
        sort_by = flask.request.args.get("sort_by", "artist")  # Default sort by artist
        # get local ip
        return flask.render_template(
            "index.html",
            songs=songs,
            artist_filter=artist_filter,
            song_filter=song_filter,
            sort_by=sort_by,
        )

    @app.route("/api/songs")
    def api_songs():
        songs = handle_song_request(flask.request)

        return {"songs": songs}

    @app.route("/api/mp3")
    def api_mp3():
        # this holds the relative path to the mp3 file
        mp3_path = flask.request.args.get("mp3_path")
        print(mp3_path)
        # concat the song path to the song folder
        mp3_path = os.path.join(SONGFOLDER, mp3_path)
        print(mp3_path)
        # prevent path traversal
        # return the song from the os
        return flask.send_file(mp3_path, mimetype="audio/mp3")

    @app.before_request
    def before_request():
        db.connect(utils.AppPaths.db)

    @app.teardown_request
    def teardown_request(exception=None):
        db.close()

    return app


class _WebserverThread(QtCore.QThread):
    def __init__(self, server: werkzeug.serving.BaseWSGIServer) -> None:
        super().__init__()
        self.server = server

    def run(self):
        self.server.serve_forever()


class _WebserverManager:
    _server: ClassVar[werkzeug.serving.BaseWSGIServer | None] = None
    _thread: ClassVar[QtCore.QThread | None] = None
    host: ClassVar[str] = ""
    port: ClassVar[int] = 0

    @classmethod
    def start(cls, host: str, port: int):
        if cls._server:
            return
        cls.host = host
        cls.port = port
        app = create_app()
        cls._server = werkzeug.serving.make_server(host, port, app)
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


def start(host="127.0.0.1", port=5000):
    _WebserverManager.start(host, port)


def stop() -> None:
    _WebserverManager.stop()
