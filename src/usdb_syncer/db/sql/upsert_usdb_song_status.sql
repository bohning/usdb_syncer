INSERT INTO
    usdb_song_status
VALUES
    (:song_id, :status) ON CONFLICT (song_id) DO
UPDATE
SET
    status = :status