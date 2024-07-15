BEGIN;

CREATE TEMPORARY TABLE session_usdb_song (
    song_id INTEGER NOT NULL,
    status INTEGER NOT NULL DEFAULT 0,
    is_playing BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (song_id),
    FOREIGN KEY (song_id) REFERENCES usdb_song (song_id) ON DELETE CASCADE
);

PRAGMA foreign_keys = ON;

COMMIT;