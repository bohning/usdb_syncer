<!-- 0.5.0 -->

# Changes

## Features

- Added an SQLite database.
  - Vastly improved performance for loading, searching etc.
  - Meta files are still being used, but are upgraded with a unique ID. Therefore,
    initially launching the new release may take some time.
  - SQLite's FTS5 is used for searching, which works by matching tokens (words). So
    a search for "beat" matches "Beat It", but not, unlike before, the "The Beatles".
- The download status column now shows the last sync time.
- Support Ogg/Opus (.opus) audio format.

<!-- 0.4.0 -->

# Changes

## Fixes

- Don't fail download if mp3/m4a tags cannot be written.
- Fix cover and background change detection.
- Let users resize all text-based columns, as width is not calculated correctly on Linux and macOS.
- Enable running the app even without keyring backend available (usually the case on Linux).

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
