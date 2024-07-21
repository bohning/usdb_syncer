BEGIN;

CREATE TABLE saved_search (
    name TEXT PRIMARY KEY,
    search JSONB NOT NULL
);

COMMIT;