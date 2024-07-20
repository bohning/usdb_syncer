<!-- 0.8.0 -->

# Changes

## Fixes

## Features

- The download path can now be customized using a dedicated template syntax (see
  _Settings_). The template must contain at least two components, which are separated
  using slashes. The last component specifies the filename, excluding its extension.
  Example: `:year: / :artist: / :title: / song` will store files like
  `1975/Queen/Bohemian Rhapsody/song.txt` and so on.

<!-- 0.7.0 -->

# Changes

## Fixes

- Fixed xcb and wayland not being bundled, which prevented the app to run on Linux.

## Features

- USDB has expanded their song list to include the audio sample URL. By pressing space or
  clicking the play icon you can play back this sample.
  If the song is locally available, the local file is played instead
  (starting at #PREVIEW if it is set).

<!-- 0.6.0 -->

# Changes

## Fixes

- Fixed the app hanging on startup for some users with large collections on macOS.
- Added detection and handling of moved meta files on startup or song folder change.
- Downloading artist or title changes for existing songs no longer causes an error.
- Fixed special characters causing issues on macOS in certain cases.
- Errors in background tasks are propagated to the main window instead of causing the
  progress dialog to hang.

## Features

- USDB has expanded their song list to include year, genre and creator. These fields are
  now populated without fully downloading a song, and respective filters were added.

<!-- 0.5.0 -->

# Changes

## Features

- Added an SQLite database.
  - Vastly improved performance for loading, searching etc.
  - Meta files are still being used, but are upgraded with a unique ID. Therefore,
    initially launching the new release may take some time.
  - SQLite's FTS5 is used for searching, which works slightly different than the
    previous approach.
- The download status column now shows the last sync time.
- Files are downloaded into temporary folders first for better clean-up, especially if
  the download fails.
- Downloads may be aborted or paused.
- Support Ogg/Opus (.opus) audio format.
- Parse song tags from USDB comments (like "#TAGS:Love Songs, Movie, 80s").

<!-- 0.4.0 -->

# Changes

## Fixes

- Don't fail download if mp3/m4a tags cannot be written.
- Fixed cover and background change detection.
- Let users resize all text-based columns, as width is not calculated correctly on Linux and macOS.
- Enable running the app even without keyring backend available (usually the case on Linux).
- Initializing the database with very many files works now.

## Features

- Removed batch view.
- Reorganized filters in a tree.
  - Songs can be filtered by download status.
  - Filters can be searched.
  - Multiple variants of the same filter can be active at the same time (select with ctrl+click).
- Added several actions for downloaded songs:
  - Delete (move to recycle bin)
  - Pin (prevent updates to local files)
- Added tooltips for some more involved actions.
- Support Vimeo IDs and shortening Amazon URLs in the meta tags dialog.
- Show number of songs per artist, title, language and edition.
- Support Ogg/Vorbis (.ogg) audio format.

<!-- 0.3.0 -->

# Changes

## Fixes

- Fixed downloading updated resources (overwrite existing files).
- Fixed downloading from USDB after recent changes.
- Fixed redownloading of unchanged audio files.

## Features

- Vimeo IDs are now supported for audio/video metatags (e.g. #VIDEO:v=123456789).
- Startup time has been improved significantly for large song collections.

<!-- 0.2.1 -->

# Changes

## Fixes

- Fixed another error with fetching browser cookies preventing the app to start.

<!-- 0.2.0 -->

# Changes

## Fixes

- Fixed an error which prevented downloads from finishing successfully ("Only valid ISO 639 language values are supported as arguments.")
- Fixed an error with the USDB login when downloading multiple songs concurrently without being logged in, yet.
- Fixed an error which could prevent the app from starting if unable to retrieve browser cookies.
- Fixed some Linux-specific issues and documented requirements (see [README](https://github.com/bohning/usdb_syncer/blob/main/README.md)).
- Fixed wrong songs being matched when finding local songs.
- Fixed downloading from YouTube by updating yt_dlp.
- Fixed shortening URLs in the meta tags dialog.

## Features

- Implemented importing and exporting a list of USDB song ids from .json, .usdb_ids and hyperlink files.
- Added actions to show the current song on USDB and on the local file system.
