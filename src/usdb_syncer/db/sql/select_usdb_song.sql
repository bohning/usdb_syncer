SELECT
    usdb_song.song_id,
    usdb_song.artist,
    usdb_song.title,
    usdb_song.language,
    usdb_song.edition,
    usdb_song.golden_notes,
    usdb_song.rating,
    usdb_song.views,
    usdb_song.sample_url,
    usdb_song.year,
    usdb_song.genre,
    usdb_song.creator,
    usdb_song.tags,
    coalesce(session_usdb_song.status, 0),
    coalesce(session_usdb_song.is_playing, false),
    sync_meta.sync_meta_id,
    sync_meta.song_id,
    sync_meta.path,
    sync_meta.mtime,
    sync_meta.meta_tags,
    sync_meta.pinned,
    txt.fname,
    txt.mtime,
    txt.resource,
    audio.fname,
    audio.mtime,
    audio.resource,
    video.fname,
    video.mtime,
    video.resource,
    cover.fname,
    cover.mtime,
    cover.resource,
    background.fname,
    background.mtime,
    background.resource
FROM
    usdb_song
    LEFT JOIN session_usdb_song ON usdb_song.song_id = session_usdb_song.song_id
    LEFT JOIN active_sync_meta ON usdb_song.song_id = active_sync_meta.song_id
    AND active_sync_meta.rank = 1
    LEFT JOIN sync_meta ON sync_meta.sync_meta_id = active_sync_meta.sync_meta_id
    AND usdb_song.song_id = sync_meta.song_id
    LEFT JOIN resource_file AS txt ON txt.kind = 'txt'
    AND sync_meta.sync_meta_id = txt.sync_meta_id
    LEFT JOIN resource_file AS audio ON audio.kind = 'audio'
    AND sync_meta.sync_meta_id = audio.sync_meta_id
    LEFT JOIN resource_file AS video ON video.kind = 'video'
    AND sync_meta.sync_meta_id = video.sync_meta_id
    LEFT JOIN resource_file AS cover ON cover.kind = 'cover'
    AND sync_meta.sync_meta_id = cover.sync_meta_id
    LEFT JOIN resource_file AS background ON background.kind = 'background'
    AND sync_meta.sync_meta_id = background.sync_meta_id