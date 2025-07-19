INSERT INTO
    resource_file(
        sync_meta_id,
        kind,
        fname,
        mtime,
        resource
    )
VALUES
    (
        :sync_meta_id,
        :kind,
        :fname,
        :mtime,
        :resource
    ) ON CONFLICT (sync_meta_id, kind) DO
UPDATE
SET
    fname = :fname,
    mtime = :mtime,
    resource = :resource