BEGIN;

ALTER TABLE
    resource_file
ADD
    status TEXT NOT NULL;

COMMIT;