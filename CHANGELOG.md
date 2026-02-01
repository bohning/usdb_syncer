<!-- 0.20.0 -->

# Changes

## Features

- Updated yt-dlp to 2026.1.29
- Added support for Python 3.13 and 3.14. The Syncer now supports Python 3.11 to 3.14.
- Columns in the song table can be hidden by right-clicking the header.

## Fixes

- Fixed broken wheels from 0.19.0
- Fixed fonts being broken on some Linux distros (#518).

## Developer notes

- Python 3.14 has a free-threaded build. This is unsupported for the Syncer, as PySide6 is currently not compatible.

<!-- 0.19.0 -->

# Changes

- The syncer is now licensed with the GPLv3. We consider this a correction of the previous invalid license condition and not a change.
- Removed support for cookies from Arc, Librewolf, Octo Browser, and Opera GX. This was due to an internal change. If you used one of those browsers, you may be interested in creating/using an addon, which can now natively supply the syncer with cookies.

## Features

- FFmpeg's freezefilter is used to determine if a commented (fallback) resource is audio-only or not.
- Commented resources from dailymotion, vimeo, facebook and soundcloud are now parsed.
- A dialog will show the reason why a song was not submitted to USDB.
- You can now open local files by double-clicking in the respective resource column icon.

## Fixes

- Resolved crash when using replaygain on linux with the bundles (#495).
- A BPM of exactly 200 is now correctly doubled to 400.
- URL params from a/v meta tags are now stripped and a log message is issued.
- Status of updated files is now correctly written to the db.
- Reading song files from legacy encodings (namely CP1252) is fixed.
- Determining local changes for submission is fixed (no canonical fixes for remote txt).
- Saving searches now works in the Linux bundle again.
- Half-star ratings are now properly supported.

## Developer notes

- The build process was migrated to uv. Poetry is no longer used.
  See the README for instructions.
- A new build script (`tools/bundle.py`) makes bundling outside of github actions possible.
- Addons are loaded earlier in the startup process than before. This means code executed at addon import time may behave differently. Hooks are unchanged.
- Two new hooks regarding cookies have been introduced. See the new wiki page for details and usage.
- Cookies for USDB are now pulled using yt-dlp instead of rookiepy.
- Added a hook to control when the syncer retries a YouTube download with cookies.

<!-- 0.18.0 -->

# Changes

- yt-dlp has been updated to latest available version 2025.11.12, solving latest download issues. This introduces Deno Javascript Runtime as new external dependency.
  The Syncer will inform you about this missing dependency and will give hints on how to install Deno on your OS.

## Features

- Medley sections are auto-corrected to start on the first beat of the first note of a line and to end of the last beat of the last note of a line.
- Local changes can now be submitted to USDB. Please use this feature only for significant adaptations, enhancements and corrections (please use the comment function for small corrections, especially when it only concerns header values such as #GAP or #BPM).
- The statuses of the resources (success/unchanged, fallback resource, unavailable/disabled, failed) is now indicated in the respective columns.

## Fixes

<!-- 0.17.0 -->

# Changes

## Features

- A new dock widget displays the cover of the currently selected song.

## Fixes

- Handled HTML escapes in the USDB song list (e.g. `&` instead of `&amp;`).
- Fixed running the webserver from the bundled app.
- Check if webserver port is valid and not in use.

<!-- 0.16.0 -->

# Changes

## Features

- A webserver can be launched to let devices in the local network browse your song collection.
- Added filters for custom data to the sidebar tree.
- Files may be deleted permanently instead of being sent to the trash folder - useful to save disk space or if trashing is not supported on your system.
- Medley sections are now checked if they start on a line start and end on a line end, otherwise a warning is issued.
- The song previewer can be launched as a standalone window (`usdb_syncer preview path/to/song.txt`).

## Fixes

- Fixed deleting songs on startup that were removed from USDB.
- The Syncer will now also retry for Vimeo resources with logged-in cookies if necessary.

<!-- 0.15.0 -->

# Changes

## Features

- Upon start, not only new songs are fetched, but updates for existing songs as well.
  - The first launch may take a while, because the song list has to be rebuilt.
- There are now shortcuts for commonly used actions.
- Added Tune Perfect (https://tuneperfect.org/) to supported apps. You can now open a selected song in Tune Perfect directly via the Syncer.
- Meta tags parsing is now case insensitive.
- Don't overwrite song txt if contents haven't changed (preserve metadata).
- Local songs may be automatically trashed if the according USDB songs were removed.
- The columns of the song table may be reorganized by drag-and-drop.

## Fixes

- Fixed extraction of allowed countries for geo-restricted resources.
- The song directory now defaults to ~/songs to avoid possible permission issues with the current directory.
- Enable the app to run if sounddevice / portaudio is not available (required for the preview feature).

<!-- 0.14.0 -->

# Changes

## Features

- Check out how a downloaded song will appear in-game with the _Preview Song_ feature!

## Fixes

- Fixed the Linux bundle.
- Fixed an error on startup for large collections.

<!-- 0.13.0 -->

# Changes

## Features

- We are now on PyPI! Simply install and update USDB Syncer with your favourite package manager, e.g. [pipx](https://pipx.pypa.io/stable/): `pipx install usdb_syncer`
- We got a dark mode, and it's even customisable! Try it out with the View tab in the settings.
- Image resources are now redownloaded if metatag postprocessing parameters have changed.

## Developer notes

- All previously accepted environment variables have been converted to commandline arguments. Check out `poetry run usdb_syncer -h`.
- pylint, black and isort have been replaced with [ruff](https://docs.astral.sh/ruff/), making the tox pipeline run much faster. ruff also integrates with common code editors.
- The hook `MainWindowDidLoad` was moved to the new module `usdb_syncer.gui.hooks`. This will contain all hooks called from the GUI going forward.

<!-- 0.12.1 -->

# Changes

## Fixes

- Fix ReplayGain for Windows (by updating ffmpeg-normalize).

<!-- 0.12.0 -->

# Changes

## Fixes

- Audio/video format selection regression in 0.11.0 fixed.
- Downloads of non-jpg images are now correctly converted to jpg.
- Image processing order is now correctly handled (crop before resize for covers, resize before crop for backgrounds).
- Improve compatibility of Linux bundle with older distributions (glibc >= 2.34).

## Features

- The Syncer now checks if a new version is available.
- Infos about unavailable or invalid resources are now sent to Discord (**please enable this in the settings to support the community**).
- Songs can now be rated on USDB via the Syncer (1-5 star rating).
- Artist initial is now available for templates.
- Audio normalization has a new option ReplayGain. If your karaoke software supports ReplayGain (e.g. UltraStar deluxe >= 2025.4.0), this is the preferred option as it does not reencode the audio file but instead only writes normalization information into the header of the audio file.
- PDF report (song list) creation has been fixed and extended.

## Developer notes

- Added hook when MainWindow was loaded.

<!-- 0.11.0 -->

# Changes

## Fixes

- Cover postprocessing parameters are ignored if USDB cover is downloaded as fallback.

## Features

- Add more fine-grained options for video container/codec selection.

<!-- 0.10.0 -->

# Changes

## Fixes

- The check for existing / outdated local resources has been improved to account for different precisions of modified times for different file systems.
- Provide binaries for Intel-based MacOS systems.
- YouTube logged-in cookies are now used for age-restricted resources.
- Games started from within the Syncer are properly cleaned up, fixing subsequent starts.

## Features

- Song tags are no longer parsed from comments, but instead from meta tags
  (Use `%2C` as separation, e.g. `tags=explicit%2C80s%2CSoundtrack).
  See https://github.com/bohning/usdb_syncer/wiki/Meta-Tags for a full list of
  supported tags.
- The UltraStar format version can now be specified in the settings (see https://usdx.eu/format/).
- The number of download threads and the per-thread bandwidth limit for Youtube can be configured in the settings.
- Option to embed artwork into video files (mp4).

<!-- 0.9.0 -->

# Changes

## Fixes

- Switch from browser_cookie3 to rookiepy in order to retrieve browser cookies on
  different OSes more reliably.

## Features

- Third-party karaoke software can now be launched from within the Syncer, passing
  the song directory as parameter.
- Add optional fix for quotation marks (language-specific)

<!-- 0.8.0 -->

# Changes

## Fixes

- Age-restricted content can now be successfully downloaded if you are logged in to
  YouTube in your browser.

## Features

- Custom data may be added to downloaded songs as key-value pairs.
- The download path can now be customized using a dedicated template syntax (see
  _Settings_). The template must contain at least two components, which are separated
  using slashes. The last component specifies the filename, excluding its extension.
  Example: `:year: / :artist: / :title: / song` will store files like
  `1975/Queen/Bohemian Rhapsody/song.txt` and so on.
  - You can even reference custom data with `:*my_key:`, which resolves to the value
    associated with `my_key` for a given song.
- Searches can be saved to the sidebar.
  - A single saved search may be made the default to automatically apply it on startup.
  - You can subscribe to saved searches to automatically download matches when new songs
    are found on USDB.
- Comments can now be posted on songs. Each comment includes a message and a rating.
  Ratings can be negative, neutral, or positive, with neutral being the default.
- The VP9 codec can be excluded for mp4 video containers (see _Settings_).
- Tags such as artist, title and year are now also written to the video file (mp4 only).
- Some text file fixes are now optional and can be configured in the settings:
  - fix linebreaks (disabled | USDX style | YASS style)
  - fix first words capitalization (disabled | enabled)
  - fix spaces (after words | before words)
- We're trying out a hook system to make the syncer extensible. See addons/README.md.

## Developer notes

- We have upgraded to Python 3.12.
- The build process was migrated to Poetry. Pipenv is no longer used.
  See the README for instructions.

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
