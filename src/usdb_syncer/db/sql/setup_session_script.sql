BEGIN;

CREATE TEMPORARY TABLE usdb_song_status (
    song_id INTEGER NOT NULL,
    status INTEGER NOT NULL,
    PRIMARY KEY (song_id),
    FOREIGN KEY (song_id) REFERENCES usdb_song (song_id) ON DELETE CASCADE
);

PRAGMA foreign_keys = ON;

COMMIT;