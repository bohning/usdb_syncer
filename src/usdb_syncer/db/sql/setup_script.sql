BEGIN;

CREATE TABLE meta (
    id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    ctime INTEGER NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE usdb_song (
    song_id INTEGER NOT NULL,
    artist TEXT NOT NULL,
    title TEXT NOT NULL,
    language TEXT NOT NULL,
    edition TEXT NOT NULL,
    golden_notes BOOLEAN NOT NULL,
    rating INTEGER NOT NULL,
    views INTEGER NOT NULL,
    year INTEGER,
    genre TEXT NOT NULL,
    creator TEXT NOT NULL,
    tags TEXT NOT NULL,
    PRIMARY KEY (song_id)
);

CREATE TABLE usdb_song_language (
    language TEXT NOT NULL,
    song_id INTEGER NOT NULL,
    PRIMARY KEY (language, song_id),
    FOREIGN KEY (song_id) REFERENCES usdb_song (song_id) ON DELETE CASCADE
);

CREATE TABLE sync_meta (
    sync_meta_id INTEGER NOT NULL,
    song_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    mtime INTEGER NOT NULL,
    meta_tags TEXT NOT NULL,
    pinned BOOLEAN NOT NULL,
    PRIMARY KEY (sync_meta_id),
    -- necessary for the active_sync_meta foreign key
    UNIQUE (song_id, sync_meta_id),
    UNIQUE (path),
    FOREIGN KEY (song_id) REFERENCES usdb_song (song_id) ON DELETE CASCADE
);

CREATE TABLE resource_file (
    sync_meta_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    fname TEXT NOT NULL,
    mtime INTEGER NOT NULL,
    resource TEXT NOT NULL,
    PRIMARY KEY (sync_meta_id, kind),
    FOREIGN KEY (sync_meta_id) REFERENCES sync_meta (sync_meta_id) ON DELETE CASCADE
);

CREATE TABLE active_sync_meta (
    song_id INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    sync_meta_id INTEGER NOT NULL,
    PRIMARY KEY (song_id, rank),
    FOREIGN KEY (song_id, sync_meta_id) REFERENCES sync_meta (song_id, sync_meta_id) ON DELETE CASCADE
);

-- external content of the fts table
CREATE VIEW fts_usdb_song_view AS
SELECT
    song_id,
    printf('%05d', song_id) padded_song_id,
    artist,
    title,
    language,
    edition,
    year,
    genre,
    creator,
    tags
FROM
    usdb_song;

CREATE VIRTUAL TABLE fts_usdb_song USING fts5 (
    song_id,
    padded_song_id,
    artist,
    title,
    language,
    edition,
    year,
    genre,
    creator,
    tags,
    content = fts_usdb_song_view,
    content_rowid = song_id,
    prefix = '1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20'
);

CREATE TRIGGER fts_usdb_song_insert
AFTER
INSERT
    ON usdb_song BEGIN
INSERT INTO
    fts_usdb_song (
        rowid,
        song_id,
        padded_song_id,
        artist,
        title,
        language,
        edition,
        year,
        genre,
        creator,
        tags
    )
VALUES
    (
        new.song_id,
        new.song_id,
        printf('%05d', new.song_id),
        new.artist,
        new.title,
        new.language,
        new.edition,
        new.year,
        new.genre,
        new.creator,
        new.tags
    );

END;

CREATE TRIGGER fts_usdb_song_update BEFORE
UPDATE
    ON usdb_song BEGIN
UPDATE
    fts_usdb_song
SET
    rowid = new.song_id,
    song_id = new.song_id,
    padded_song_id = printf('%05d', new.song_id),
    artist = new.artist,
    title = new.title,
    language = new.language,
    edition = new.edition,
    year = new.year,
    genre = new.genre,
    creator = new.creator,
    tags = new.tags
WHERE
    rowid = old.song_id;

END;

CREATE TRIGGER fts_usdb_song_delete
AFTER
    DELETE ON usdb_song BEGIN
DELETE FROM
    fts_usdb_song
WHERE
    rowid = old.song_id;

END;

COMMIT;