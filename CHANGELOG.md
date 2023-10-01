<!-- 0.4.0 -->

# Changes

## Fixes

## Features

- The batch view has been removed, and a view dedicated to local songs added.

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
