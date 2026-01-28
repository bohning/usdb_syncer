SELECT
    sync_meta.sync_meta_id,
    sync_meta.song_id,
    sync_meta.usdb_mtime,
    sync_meta.path,
    sync_meta.mtime,
    sync_meta.meta_tags,
    sync_meta.pinned,
    txt.fname,
    txt.mtime,
    txt.resource,
    txt.status,
    audio.fname,
    audio.mtime,
    audio.resource,
    audio.status,
    instrumental.fname,
    instrumental.mtime,
    instrumental.resource,
    instrumental.status,
    vocals.fname,
    vocals.mtime,
    vocals.resource,
    vocals.status,
    video.fname,
    video.mtime,
    video.resource,
    video.status,
    cover.fname,
    cover.mtime,
    cover.resource,
    cover.status,
    background.fname,
    background.mtime,
    background.resource,
    background.status
FROM
    sync_meta
    LEFT JOIN resource_file AS txt ON txt.kind = 'txt'
    AND sync_meta.sync_meta_id = txt.sync_meta_id
    LEFT JOIN resource_file AS audio ON audio.kind = 'audio'
    AND sync_meta.sync_meta_id = audio.sync_meta_id
    LEFT JOIN resource_file AS instrumental ON instrumental.kind = 'instrumental'
    AND sync_meta.sync_meta_id = instrumental.sync_meta_id
    LEFT JOIN resource_file AS vocals ON vocals.kind = 'vocals'
    AND sync_meta.sync_meta_id = vocals.sync_meta_id
    LEFT JOIN resource_file AS video ON video.kind = 'video'
    AND sync_meta.sync_meta_id = video.sync_meta_id
    LEFT JOIN resource_file AS cover ON cover.kind = 'cover'
    AND sync_meta.sync_meta_id = cover.sync_meta_id
    LEFT JOIN resource_file AS background ON background.kind = 'background'
    AND sync_meta.sync_meta_id = background.sync_meta_id