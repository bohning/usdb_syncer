BEGIN;

-- Migrate rating column from INTEGER to REAL to support half-star ratings
-- SQLite has limited ALTER TABLE support, so the table needs to be recreated

ALTER TABLE usdb_song RENAME TO usdb_song_old;

CREATE TABLE usdb_song (
    song_id INTEGER NOT NULL,
    artist TEXT NOT NULL,
    title TEXT NOT NULL,
    language TEXT NOT NULL,
    edition TEXT NOT NULL,
    golden_notes BOOLEAN NOT NULL,
    rating REAL NOT NULL,
    views INTEGER NOT NULL,
    year INTEGER,
    genre TEXT NOT NULL,
    creator TEXT NOT NULL,
    tags TEXT NOT NULL,
    sample_url TEXT NOT NULL DEFAULT '',
    usdb_mtime INTEGER NOT NULL,
    PRIMARY KEY (song_id)
);

INSERT INTO usdb_song
SELECT
    song_id,
    artist,
    title,
    language,
    edition,
    golden_notes,
    CAST(rating AS REAL),
    views,
    year,
    genre,
    creator,
    tags,
    sample_url,
    usdb_mtime
FROM usdb_song_old;

DROP TABLE usdb_song_old;

COMMIT;
