BEGIN;

CREATE TABLE image_dimensions (
    sync_meta_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('cover', 'background')),
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    PRIMARY KEY (sync_meta_id, kind),
    FOREIGN KEY (sync_meta_id, kind)
        REFERENCES resource_file (sync_meta_id, kind)
        ON DELETE CASCADE
);

COMMIT;
