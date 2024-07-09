BEGIN;

ALTER TABLE
    usdb_song
ADD
    sample_url TEXT NOT NULL DEFAULT '';

COMMIT;