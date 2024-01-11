INSERT INTO
    usdb_song
VALUES (
    :song_id,
    :artist,
    :title,
    :language,
    :edition,
    :golden_notes,
    :rating,
    :views
)
ON CONFLICT (song_id) DO UPDATE SET
    artist = :artist,
    title = :title,
    language = :language,
    edition = :edition,
    golden_notes = :golden_notes,
    rating = :rating,
    views = :views