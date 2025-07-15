BEGIN;

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