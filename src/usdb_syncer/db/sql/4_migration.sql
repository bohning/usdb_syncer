BEGIN;

CREATE TABLE saved_search (
    name TEXT PRIMARY KEY,
    search JSONB NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT false
);

COMMIT;