INSERT INTO
    custom_meta_data
VALUES
    (:sync_meta_id, :key, :value) ON CONFLICT (sync_meta_id, key) DO
UPDATE
SET
    value = :value