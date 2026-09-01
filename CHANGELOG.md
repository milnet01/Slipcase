# Changelog

All notable changes to Slipcase are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Regression tests for the security invariants and for every defect fixed in this release**
  The suite grows from 18 tests to 56. `api/` had no coverage at all, so the URL
  allowlist, credential scrubbing and the download limits could each have been
  removed by a refactor without a test noticing.

### Changed

- **PNG exports are written atomically**
  An interrupted save could replace a good file with a truncated one.

- **The documented `rendering.supersample` setting is now actually read**
  It was shipped as a default and documented in the config schema, but every
  render path hardcoded 2.

- **PNG compression level is configurable via `rendering.compress_level`**
  Default 6, as the code has always used; 9 is roughly 5% smaller and 2-4x
  slower. The documented requirement said 9 while every call site used 6.

### Fixed

- **Credentials are trimmed of stray whitespace before being saved**

- **Browsing search results starts one preview download at a time**

- **Holding Enter in the search box no longer starts overlapping searches**

- **The Generate button and comparison captions follow a theme change**

- **Disabled menu entries are dimmed**

- **A corrupt or non-UTF-8 config no longer prevents the app from starting**

- **Rate limiting is immune to system clock changes**

- **Spine text is readable on systems without the bundled font paths**
  The fallback font was loaded at a fixed ~10px regardless of the size requested.

- **Spine text stays legible when a custom spine colour is chosen**
  The platform accent colour was used regardless of contrast, which could render
  white text on a white spine.

- **A malformed API response no longer raises out of a search**

- **ScreenScraper reports itself unconfigured unless all four credentials are set**

- **libretro thumbnail URLs are percent-encoded**
  Titles containing '#' or '%' silently failed to download.

- **Shadow blur looks the same with and without OpenCV installed**
  The OpenCV path derived its blur radius from the kernel size, giving roughly a
  third of the intended blur.

- **PC now resolves to the DVD case**
  It was claimed by two case types and which one won depended on declaration order.

- **Copy to clipboard no longer risks pasting corrupt image data**

- **Export and settings failures are reported instead of terminating the app**
  A full disk or a read-only folder raised out of a Qt slot, which is fatal.

- **Unchecking Case Texture now applies to animated exports**

- **The search dialog releases its cached images when a result is chosen**
  The cache was only cleared when the dialog was cancelled.

- **Rate limiting now holds across API clients instead of resetting for each search**
  Each background task built its own client, so the interval only ever applied
  within a single task.

- **Search failures say what went wrong rather than reporting no results**
  Network, TLS, authentication and rate-limit errors were all reported as an
  empty result list, which made a wrong password indistinguishable from a game
  that is genuinely not in the database.

- **Batch failures are reported instead of being overwritten by the progress message**
  A batch in which every file failed previously reported success with no cause.

- **Starting a second render, batch or animation while one is running is refused**
  It could leave a stale render overwriting a newer one.

- **Closing the window during a render, batch or animation no longer risks a crash**
  The shutdown handshake could not stop these workers and then dropped the last
  reference to a still-running thread. Workers now honour an interruption request
  and a live worker is never discarded.

- **Batch processing no longer overwrites source images or same-named covers**
  Output was keyed on the filename stem alone, so two covers named the same in
  different folders collided, and choosing the source folder as the output folder
  overwrote each source with its own render.

- **Settings are written atomically and can no longer be lost**
  Saving truncated the live file before writing, and a config that failed to
  load was silently replaced by defaults which the next save then wrote over the
  stored credentials. The file is now written to a temp file created 0600 and
  renamed into place, and a save is refused while the existing file is unreadable.

- **The floor reflection mirrors the bottom of the case rather than the top**

- **Renders are no longer stretched horizontally**
  The final downscale used a different factor for each axis, so every render was
  12-14% too wide and did not match the real-world case proportions.

### Security

- **Escape cover-art titles and API errors before showing them in the search dialog**
  Titles come from a community-edited database and were rendered as rich text.

- **Hide the TheGamesDB API key and the ScreenScraper developer ID on screen**
  Both were plain-text fields while the two password fields were masked.

- **Sanitise export filenames taken from cover-art API results**
  A game title supplied by a remote API reached a filesystem path unchecked, so
  a name containing path separators could write outside the chosen folder.

- **Lower the decompression-bomb limit, which had been set to twice Pillow's own default**
  `Image.MAX_IMAGE_PIXELS` was 178,956,970, exactly 2x Pillow's default, so the
  line documented as bomb protection had been raising the ceiling. It is now
  40,000,000, defined and applied in `api/base.py` so the download path is
  protected even when `main.py` has not run, and downloaded images are checked
  against it before they are decoded.

- **Validate the download allowlist on every redirect hop**
  The allowlist and the HTTPS-only rule were checked on the URL requested, not
  the one actually fetched, so a redirect from an allowed host could pull the
  response body from anywhere -- including localhost and the local network --
  and could silently downgrade to plain HTTP.

## [1.0.0] - 2026-08-27

Initial release. Converts 2D game cover art into 3D boxart renders for 15 case
types, with online cover-art search across ScreenScraper, TheGamesDB and
libretro-thumbnails, batch processing, animated turntable export, and seven
themes.
