BEGIN;

CREATE TABLE discord_notification (
    song_id INTEGER NOT NULL,
    resource TEXT NOT NULL,
    PRIMARY KEY (song_id, resource),
    FOREIGN KEY (song_id) REFERENCES usdb_song (song_id) ON DELETE CASCADE
);

END;