INSERT INTO
    session_usdb_song (song_id, status)
VALUES
    (:song_id, :status) ON CONFLICT (song_id) DO
UPDATE
SET
    status = :status