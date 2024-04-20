INSERT INTO
    active_sync_meta (song_id, sync_meta_id, rank)
SELECT
    song_id,
    sync_meta_id,
    rank
FROM
    (
        SELECT
            song_id,
            sync_meta_id,
            ROW_NUMBER() OVER (
                PARTITION BY song_id
                ORDER BY
                    path ASC
            ) AS rank
        FROM
            sync_meta
        WHERE
            path GLOB :folder || '/*'
            AND song_id = :song_id
    )