# Changelog

All notable changes to Slipcase are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **A subsystem map for review tooling** (SLIP-0086)
  docs/subsystems.md and .indie-review/partition.json divide the code by what it does rather than by directory, so a review is briefed per concern.

- **CONTRIBUTING.md, with steps that have been run** (SLIP-0084)
  Setup, the gate, what a change should look like, the commit shape and where to report things. Every step was executed against a fresh clone rather than only written down.

- **The shell formatter now has a style to check against** (SLIP-0085)
  An `.editorconfig` declares the Python and shell indentation the project
  already uses, so `shfmt` no longer skips every run for want of a config.

- **SECURITY.md, with a private way to report a flaw** (SLIP-0083)
  GitHub private vulnerability reporting is enabled, and the file states what
  is in scope, what is not, and which release is supported.

- **The test suite runs automatically on every push** (SLIP-0022)
  `scripts/local-ci.sh` holds the one list of checks and the GitHub workflow
  calls that same script, so the local push gate and CI cannot drift apart.

- **Regression tests for the security invariants and for every defect fixed in this release**
  `api/` had no coverage at all, so the URL allowlist, credential scrubbing and
  the download limits could each have been removed by a refactor without a test
  noticing.

### Changed

- **Builds install exactly pinned dependencies** (SLIP-0023)
  requirements.lock holds the exact versions, transitive ones included, so two builds of one release bundle the same libraries. requirements.txt stays as the readable declaration of what the project depends on.

- **PNG exports are written atomically**
  An interrupted save could replace a good file with a truncated one.

- **The documented `rendering.supersample` setting is now actually read**
  It was shipped as a default and documented in the config schema, but every
  render path hardcoded 2.

- **PNG compression level is configurable via `rendering.compress_level`**
  Default 6, as the code has always used; 9 is roughly 5% smaller and 2-4x
  slower. The documented requirement said 9 while every call site used 6.

### Fixed

- **The animation dialog shows how many frames will really be written** (SLIP-0072)
  Bounce replays the sweep in reverse, so asking for 120 frames writes 238. Nothing said so, and the file was about twice the size you would expect.

- **A damaged colour file no longer stops the app starting** (SLIP-0053)
  A truncated resources/case_colors.json crashed on launch. It now starts with default spine colours and says why in the status bar; a missing file is reported rather than passing silently.

- **Search says when there is nothing to search** (SLIP-0038)
  With no API credentials entered, and on a platform libretro does not carry, search reported "No results found" -- blaming your search term for a missing setup. It now says so and points at Settings.

- **A failed online search now ends** (SLIP-0052)
  An unexpected error left the progress bar spinning and the Search button disabled until the dialog was closed.

- **Exporting without typing .png no longer replaces a file silently** (SLIP-0039)
  The extension was added after the file dialog had already asked about overwriting, so typing "render" could replace an existing render.png with no warning. Both the image and animation exports are covered.

- **The standards document and the code agree again** (SLIP-0074)
  Seven statements described behaviour the code does not have -- transparency in exports, the status bar's text colour, when libretro is searched, how gradients are built, which regional cover is preferred, and two case details that are not drawn. Covers SLIP-0074, 0075, 0077, 0078, 0079 and 0080.

- **Two remembered settings are now declared** (SLIP-0076)
  The auto-filename checkbox and the last export folder were saved but listed nowhere, so nothing told you they existed. A test now fails if another setting is saved without being declared.

- **libretro cover art can now be found by typing a game's title** (SLIP-0089)
  Thumbnails are stored under the full ROM name with its region tag, so asking
  for the bare title matched nothing on any system. The lookup now tries the
  exact name first, then the common region tags.

- **The release recipe no longer claims the project is not under git** (SLIP-0029)
  It also points at the changelog that exists rather than asking for one to be
  created.

- **About shows the real version** (SLIP-0028)
  The dialog carried its own copy of the version string, which a bump updated
  everywhere else and left behind here.

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

- **Downloads accept only PNG, JPEG and WEBP** (SLIP-0066)
  BMP and GIF were accepted with no recorded use. Every accepted format is
  another image decoder a remote response can reach.

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
