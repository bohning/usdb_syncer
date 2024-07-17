INSERT INTO
    session_usdb_song (song_id, status, is_playing)
VALUES
    (:song_id, :status, :is_playing) ON CONFLICT (song_id) DO
UPDATE
SET
    status = :status,
    is_playing = :is_playing