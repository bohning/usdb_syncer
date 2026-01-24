BEGIN;

-- Clean up leeches due to missing foreign key enforcement

DELETE FROM usdb_song_creator WHERE song_id NOT IN (SELECT song_id FROM usdb_song);
DELETE FROM usdb_song_genre WHERE song_id NOT IN (SELECT song_id FROM usdb_song);
DELETE FROM usdb_song_language WHERE song_id NOT IN (SELECT song_id FROM usdb_song);
DELETE FROM discord_notification WHERE song_id NOT IN (SELECT song_id FROM usdb_song);
DELETE FROM sync_meta WHERE song_id NOT IN (SELECT song_id FROM usdb_song);
DELETE FROM custom_meta_data WHERE sync_meta_id NOT IN (SELECT sync_meta_id FROM sync_meta);
DELETE FROM resource_file WHERE sync_meta_id NOT IN (SELECT sync_meta_id FROM sync_meta);

-- Migrate rating column from INTEGER to REAL to support half-star ratings
-- SQLite has limited ALTER TABLE support, so the table needs to be recreated

CREATE TABLE usdb_song_temp AS
SELECT
    song_id,
    artist,
    title,
    language,
    edition,
    golden_notes,
    CAST(rating AS REAL) rating,
    views,
    year,
    genre,
    creator,
    tags,
    sample_url,
    usdb_mtime
FROM
    usdb_song;

DROP TABLE usdb_song;

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

INSERT INTO usdb_song SELECT * FROM usdb_song_temp;

DROP TABLE usdb_song_temp;

COMMIT;
