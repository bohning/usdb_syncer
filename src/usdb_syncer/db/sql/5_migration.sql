BEGIN;

CREATE TABLE custom_meta_data (
    sync_meta_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (sync_meta_id, key),
    FOREIGN KEY (sync_meta_id) REFERENCES sync_meta (sync_meta_id) ON DELETE CASCADE
);

END;