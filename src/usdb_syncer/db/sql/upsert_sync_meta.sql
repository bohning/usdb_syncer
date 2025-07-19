INSERT INTO
    sync_meta (
        sync_meta_id,
        song_id,
        usdb_mtime,
        path,
        mtime,
        meta_tags,
        pinned
    )
VALUES
    (
        :sync_meta_id,
        :song_id,
        :usdb_mtime,
        :path,
        :mtime,
        :meta_tags,
        :pinned
    ) ON CONFLICT (sync_meta_id) DO
UPDATE
SET
    song_id = :song_id,
    usdb_mtime = :usdb_mtime,
    path = :path,
    mtime = :mtime,
    meta_tags = :meta_tags,
    pinned = :pinned