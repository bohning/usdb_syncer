BEGIN;

-- 1. Create the new table with the updated schema
CREATE TABLE resource_file_new (
    sync_meta_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    fname TEXT,
    mtime INTEGER,
    resource TEXT,
    status TEXT NOT NULL,
    PRIMARY KEY (sync_meta_id, kind),
    FOREIGN KEY (sync_meta_id) REFERENCES sync_meta (sync_meta_id) ON DELETE CASCADE
);

-- 2. Copy existing data (initialize status to 'success' or 'unknown')
INSERT INTO resource_file_new (sync_meta_id, kind, fname, mtime, resource, status)
SELECT sync_meta_id, kind, fname, mtime, resource, 'success' FROM resource_file;

-- 3. Drop the old table and rename the new one
DROP TABLE resource_file;
ALTER TABLE resource_file_new RENAME TO resource_file;

COMMIT;