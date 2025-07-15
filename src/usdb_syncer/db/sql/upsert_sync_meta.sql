INSERT INTO
    sync_meta
VALUES (
    :sync_meta_id,
    :song_id,
    :lastchange,
    :path,
    :mtime,
    :meta_tags,
    :pinned
)
ON CONFLICT (sync_meta_id) DO UPDATE SET
    song_id = :song_id,
    lastchange = :lastchange,
    path = :path,
    mtime = :mtime,
    meta_tags = :meta_tags,
    pinned = :pinned