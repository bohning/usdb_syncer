BEGIN;

CREATE TABLE saved_search (
    name TEXT PRIMARY KEY,
    search JSONB NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT false,
    subscribed BOOLEAN NOT NULL DEFAULT false
);

CREATE TRIGGER saved_search_insert
AFTER
INSERT
    ON saved_search
    WHEN new.is_default BEGIN
UPDATE
    saved_search
SET
    is_default = false
WHERE
    name != new.name;

END;

CREATE TRIGGER saved_search_update
AFTER
UPDATE
    ON saved_search
    WHEN new.is_default BEGIN
UPDATE
    saved_search
SET
    is_default = false
WHERE
    name != new.name;

END;