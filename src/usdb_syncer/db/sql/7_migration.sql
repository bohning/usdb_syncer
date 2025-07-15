BEGIN;

ALTER TABLE
    usdb_song
ADD
    lastchange INTEGER NOT NULL DEFAULT 0;

ALTER TABLE
    sync_meta
ADD
    lastchange INTEGER NOT NULL DEFAULT 0;

COMMIT;