INSERT INTO
    session_usdb_song (song_id, is_playing)
VALUES
    (:song_id, :is_playing) ON CONFLICT (song_id) DO
UPDATE
SET
    is_playing = :is_playing