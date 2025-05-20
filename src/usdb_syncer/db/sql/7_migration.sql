BEGIN;

ALTER TABLE
    usdb_song
ADD
    instrumental TEXT NOT NULL DEFAULT '';

ALTER TABLE
    usdb_song
ADD
    vocals TEXT NOT NULL DEFAULT '';

COMMIT;