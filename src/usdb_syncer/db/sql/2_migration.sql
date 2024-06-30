BEGIN;

CREATE TABLE usdb_song_genre (
    genre TEXT NOT NULL,
    song_id INTEGER NOT NULL,
    PRIMARY KEY (genre, song_id),
    FOREIGN KEY (song_id) REFERENCES usdb_song (song_id) ON DELETE CASCADE
);

WITH RECURSIVE split_genres AS (
    SELECT
        song_id,
        TRIM(SUBSTR(genre, 1, INSTR(genre || ',', ',') - 1)) AS genre,
        SUBSTR(genre, INSTR(genre || ',', ',') + 1) AS rest
    FROM
        usdb_song
    UNION
    ALL
    SELECT
        song_id,
        TRIM(SUBSTR(rest, 1, INSTR(rest || ',', ',') - 1)) AS genre,
        SUBSTR(rest, INSTR(rest || ',', ',') + 1) AS rest
    FROM
        split_genres
    WHERE
        rest != ''
)
INSERT INTO
    usdb_song_genre (genre, song_id)
SELECT
    genre,
    song_id
FROM
    split_genres
WHERE
    genre != '';

CREATE TABLE usdb_song_creator (
    creator TEXT NOT NULL,
    song_id INTEGER NOT NULL,
    PRIMARY KEY (creator, song_id),
    FOREIGN KEY (song_id) REFERENCES usdb_song (song_id) ON DELETE CASCADE
);

WITH RECURSIVE split_creators AS (
    SELECT
        song_id,
        TRIM(
            SUBSTR(creator, 1, INSTR(creator || ',', ',') - 1)
        ) AS creator,
        SUBSTR(creator, INSTR(creator || ',', ',') + 1) AS rest
    FROM
        usdb_song
    UNION
    ALL
    SELECT
        song_id,
        TRIM(SUBSTR(rest, 1, INSTR(rest || ',', ',') - 1)) AS creator,
        SUBSTR(rest, INSTR(rest || ',', ',') + 1) AS rest
    FROM
        split_creators
    WHERE
        rest != ''
)
INSERT INTO
    usdb_song_creator (creator, song_id)
SELECT
    creator,
    song_id
FROM
    split_creators
WHERE
    creator != '';

COMMIT;