INSERT INTO
    resource_file(
        sync_meta_id,
        kind,
        fname,
        mtime,
        status,
        resource
    )
VALUES
    (
        :sync_meta_id,
        :kind,
        :fname,
        :mtime,
        :status,
        :resource
    ) ON CONFLICT (sync_meta_id, kind) DO
UPDATE
SET
    fname = :fname,
    mtime = :mtime,
    status = :status,
    resource = :resource