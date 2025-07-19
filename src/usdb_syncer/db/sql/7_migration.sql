BEGIN;

CREATE TABLE session_usdb_song (
    song_id INTEGER NOT NULL,
    status INTEGER,
    is_playing BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (song_id),
    FOREIGN KEY (song_id) REFERENCES usdb_song (song_id) ON DELETE CASCADE
);

DELETE FROM
    usdb_song;

DELETE FROM
    sync_meta;

ALTER TABLE
    usdb_song
ADD
    usdb_mtime INTEGER NOT NULL;

ALTER TABLE
    sync_meta
ADD
    usdb_mtime INTEGER NOT NULL;

COMMIT;