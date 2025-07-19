INSERT INTO
    usdb_song (
        song_id,
        usdb_mtime,
        artist,
        title,
        language,
        edition,
        golden_notes,
        rating,
        views,
        sample_url,
        year,
        genre,
        creator,
        tags
    )
VALUES
    (
        :song_id,
        :usdb_mtime,
        :artist,
        :title,
        :language,
        :edition,
        :golden_notes,
        :rating,
        :views,
        :sample_url,
        :year,
        :genre,
        :creator,
        :tags
    ) ON CONFLICT (song_id) DO
UPDATE
SET
    usdb_mtime = :usdb_mtime,
    artist = :artist,
    title = :title,
    language = :language,
    edition = :edition,
    golden_notes = :golden_notes,
    rating = :rating,
    views = :views,
    sample_url = :sample_url,
    year = :year,
    genre = :genre,
    creator = :creator,
    tags = :tags