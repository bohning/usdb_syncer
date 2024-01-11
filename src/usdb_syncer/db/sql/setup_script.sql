BEGIN;

CREATE TABLE meta (
    id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    ctime REAL NOT NULL,
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
    PRIMARY KEY (song_id)
);

CREATE TABLE sync_meta (
    sync_meta_id INTEGER NOT NULL,
    song_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    mtime REAL NOT NULL,
    meta_tags TEXT NOT NULL,
    pinned BOOLEAN NOT NULL,
    PRIMARY KEY (sync_meta_id),
    UNIQUE (path),
    FOREIGN KEY(song_id) REFERENCES usdb_song (song_id)
);

CREATE TABLE resource_file (
    sync_meta_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    fname TEXT NOT NULL,
    mtime REAL NOT NULL,
    resource TEXT NOT NULL,
    PRIMARY KEY (sync_meta_id, kind),
    FOREIGN KEY(sync_meta_id) REFERENCES sync_meta (sync_meta_id) ON DELETE CASCADE
);

COMMIT;