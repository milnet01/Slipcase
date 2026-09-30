# Changelog

All notable changes to Slipcase are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **A cover preview from an earlier search no longer appears beside a newer result** (SLIP-0102)
  Searching again while a preview was still downloading could show the old
  game's cover against a result from the new search.

- **Clicking quickly through search results no longer freezes the window** (SLIP-0099)
  Choosing another result while a preview was still downloading made the
  window wait up to a second for it. The running download is now left to
  finish, and the preview for whichever result is selected by then follows.

### Security

- **A cover that arrives one byte at a time is now cut off at the time limit** (SLIP-0101)
  The 60 second download limit was only checked once a full 64 KiB block had
  arrived, so a server trickling bytes could hold a download open far past
  it. Every read now returns as soon as anything arrives, and the limit is
  checked each time.

- **Search replies are capped in size and time, like image downloads** (SLIP-0100)
  A reply from a cover-art service was read whole with no limit. It is now
  held to 5 MB and to the same 60 second limit as an image.

## [1.3.0] - 2026-09-30

**Theme:** Windows and Mac downloads.

### Added

- **Mac downloads: Slipcase-macos-arm64.dmg and Slipcase-macos-x86_64.dmg** (SLIP-0020)
  One disk image for Apple silicon and one for Intel. The app is not signed
  with an Apple developer certificate, so macOS asks you to allow the first
  launch under System Settings, Privacy & Security. Built and self-checked
  on GitHub's Mac machines; nobody has tried it by hand on a real Mac.

- **A one-file Windows download: Slipcase-windows-x64.exe** (SLIP-0019)
  A portable program: double-click it, nothing is installed. It is not
  signed, so Windows shows its "Windows protected your PC" screen the
  first time; choose More info, then Run anyway.

- **The tests run on Windows and macOS at every push** (SLIP-0019)
  A new CI job runs the suite on both, which no Linux machine can do
  locally.

### Changed

- **On Windows the settings live in %APPDATA%\slipcase** (SLIP-0019)
  Running from source on Windows used to put them in a `.config` folder in
  your user folder; a settings file there is not moved. The lock that keeps
  one copy running sits in the settings folder on Windows and macOS.

## [1.2.0] - 2026-09-30

**Theme:** A one-file Linux download.

### Added

- **A one-file Linux download: Slipcase-x86_64.AppImage** (SLIP-0018)
  Each release now carries an AppImage with Python, Qt and the imaging
  libraries inside, so the app runs without installing anything. It is
  built on Ubuntu 22.04 and needs a system at least that recent.

- **`--smoke` checks that a packaged build is whole** (SLIP-0018)
  Renders one box in a worker process and opens the main window against a
  temporary settings file, then prints one line and exits. Every packaged
  build must pass it before it is attached to a release.

### Fixed

- **A packaged batch render no longer opens another copy of the app** (SLIP-0018)
  Batch rendering starts worker processes, and in a packaged build each
  worker began by running the application again. `main.py` now calls
  `multiprocessing.freeze_support()`, which is what turns that run into
  the worker.

## [1.1.0] - 2026-09-29

**Theme:** Cover-art search checked against the real services, lighter previews, and a long run of fixes.

### Added

- **Online cover-art search is verified against the live services, with recorded replies in the test suite.** (SLIP-0088)
  ScreenScraper, TheGamesDB and libretro were each searched live. The
  ScreenScraper and TheGamesDB replies are kept, with every credential
  removed, so the tests now check the parser against what the services
  really send.

- **A Settings switch turns libretro search off** (SLIP-0071)
  libretro needs no login, so it was contacted on every search. A new
  libretro tab in Settings turns it off; it stays on by default.

- **You can render the back of the box** (SLIP-0033)
  Set View to Back to see the back cover with the spine beside it. It uses
  the back cover you load, or the back half of a wraparound scan. Before
  this, a loaded back cover was accepted and then not used at all.

- **You can tell the app an image is not a wraparound cover** (SLIP-0051)
  A wide front-only image could be mistaken for back + spine + front and
  cut into three. Untick "Full cover detected" to use the whole image as the
  front.

- **A subsystem map for review tooling**
  docs/subsystems.md and .indie-review/partition.json divide the code by what it does rather than by directory, so a review is briefed per concern.
  SLIP-0086 stays open until the Ants review tooling reads the map.

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

- **Search previews load a small copy of each cover instead of the full image.** (SLIP-0093)
  Clicking through results now fetches tens of kilobytes per cover rather
  than up to a megabyte. The full-size cover is downloaded once, when a
  result is chosen.

- **All window and dialog text is ready for translation** (SLIP-0094)
  The settings, search and animation dialogs, and the main window's status
  messages and message boxes, now route their text through Qt's
  translation system. No translations ship yet.

- **Settings honour XDG_CONFIG_HOME** (SLIP-0050)
  Settings live in $XDG_CONFIG_HOME/slipcase/ when that variable is set to
  an absolute path, and in ~/.config/slipcase/ otherwise. A config already
  at ~/.config is not moved: if you set the variable, copy it across.

- **STANDARDS.md is the one home of the security, performance and memory rules** (SLIP-0092)
  CLAUDE.md now points at STANDARDS.md sections 10-12 instead of keeping
  a second copy that could drift.

- **Dragging the spine adjustment sliders is smooth** (SLIP-0067)
  The app no longer re-searches the whole cover for the spine on every
  step; it redraws the split preview once you pause.

- **Spines are drawn about twice as fast, and resizing the window is smoother** (SLIP-0047)
  Fonts are loaded once instead of about thirty times per spine, and the
  preview is re-scaled once you stop dragging rather than on every step.

- **Only one copy of Slipcase runs at a time** (SLIP-0049)
  Opening it again brings the window that is already open to the front.
  Two copies used to overwrite each other's settings, which could lose login
  details you had entered.

- **The settings file now records its version, so later releases can upgrade it safely** (SLIP-0042)
  Settings saved by a newer version are kept intact by an older one. A
  damaged settings file that holds something other than settings no longer
  stops the app from starting, and is left untouched.

- **The standards document now matches the code it governs** (SLIP-0081)
  An independent cold review of STANDARDS.md, run because the shutdown rule in
  section 12 had been rewritten without one. That section turned out to be
  correct; thirty-one other claims were not. Among them: the decompression-bomb
  ceiling was credited to the wrong file, so following the document could have
  removed the only copy that protects a test or a batch child; the download
  allowlist was described as covering image downloads when it gates every
  request; the test suite was said to finish in under five seconds when it takes
  about twenty; and the status-bar colour rule described two themes when seven
  ship. The review also surfaced two real defects in the code, filed as
  SLIP-0090 and SLIP-0091.

- **The export width is capped at a size the app documents** (SLIP-0037)
  The width box accepted values that could use all available memory before anything was saved.

- **Renders are faster and slightly sharper** (SLIP-0043)
  Every render did two full image-resize passes that changed nothing. Measured at 512px: about 8% quicker, and cover art is no longer resampled twice.

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

### Removed

- **Unused ScreenScraper spine download removed** (SLIP-0073)
  download_spine and the spine_url result field had no callers.

### Fixed

- **A refused cover-art search now says why, in the service's own words.**
  ScreenScraper answers bad developer credentials with a line of text
  rather than data, and the search dialog showed "Expecting value: line 1
  column 1 (char 0)". It now shows the reply itself, with credentials
  scrubbed and long replies cut short. Found by the SLIP-0088 live run.

- **The left column scrolls instead of squashing the spine panel** (SLIP-0095)
  In an 800-pixel-tall window with a full cover loaded, "Reset to Auto"
  was clipped and the split thumbnails were cut off.

- **Batch mode now uses your PNG compression setting** (SLIP-0091)
  It always saved at the default level, whatever the setting said.

- **Spine titles use a proper bold font on more systems** (SLIP-0070)
  The app looked for its fonts in a few fixed places and, on openSUSE, found
  none and used a thin fallback font. It now finds installed
  fonts wherever the system keeps them.

- **Screen readers now announce each field by name** (SLIP-0046)
  Fields such as Title, Serial and Angle were read out as unnamed boxes.
  Most can also be reached with Alt and the underlined letter of their label.

- **The progress bar no longer vanishes early when one job ends while another runs** (SLIP-0059)

- **The spine finder no longer moves the spine edge to a faint smudge** (SLIP-0058)
  Where the cover had no detail at the expected spine edge, any faint mark
  nearby could pull the edge towards it.

- **When the spine finder fails, it now says so instead of hiding it** (SLIP-0054)
  It falls back to the size-based estimate and logs a warning; a genuine
  bug is no longer silently swallowed.

- **The window reopens where you left it, and stays on a screen you can see** (SLIP-0040)
  It crept down-right by the height of the title bar on every restart, and
  could reopen on a monitor that was no longer connected. It also now
  remembers being maximised. After this update the window opens at its
  default place once, then remembers again.

- **Large animations stop with a clear message instead of using up all your memory** (SLIP-0036)
  An animation that would need more than 1 GB is refused after its first
  frame, with a note to lower the width or frame count. Bounce animations
  also use half the memory they did.

- **Choosing a search result no longer downloads its cover a second time** (SLIP-0035)
  The cover fetched for the preview is reused when you pick the result.

- **Every case type now has moulded detail on its spine** (SLIP-0034)
  Jewel, Switch, DS, 3DS, PSP and Vita cases had a plain spine while the
  others had grooves or fold lines.

- **The shadow under the box fades softly instead of ending in a hard edge** (SLIP-0032)
  It sat too far right and down and was cut off square at the image
  edge. It now sits where intended and fades out on every side.

- **Two smaller search-window fixes** (SLIP-0061)
  The 3D Boxart button could look available for a game that has none, and a failed preview said only "No preview" while discarding the reason. Covers SLIP-0061 and SLIP-0062.

- **Clearer failures in the rendering helpers** (SLIP-0057)
  A width too small to draw at raised an unhelpful maths error, or silently produced a corrupt image. Shading now refuses an unknown direction instead of doing nothing, and the reflection helper accepts an image without transparency. Covers SLIP-0055, 0056 and 0057.

- **Exporting from a drive root no longer produces a blank name** (SLIP-0063)
  An image loaded from the top of a drive exported as " 3D Boxart.png". The name is now derived in one place, which falls back to the title and then the file name.

- **The app shows its own icon in the taskbar** (SLIP-0048)
  Neither the X11 nor the Wayland route to an icon was set, so the window showed a generic one on both.

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

- **Cover-art searches can no longer be redirected off the allowed sites** (SLIP-0090)
  Search requests followed any redirect a server sent, to any host or to
  plain http. Every hop is now checked against the allowed list, as image
  downloads already were, and login details are never re-sent to a
  redirected address.

- **A download now has a time limit, not only a size limit** (SLIP-0065)
  A server drip-feeding data could hold a search open indefinitely without ever reaching the 50MB cap.

- **Data requests are held to the same allowlist as image downloads** (SLIP-0064)
  The rule that all traffic goes to known sites over HTTPS was enforced when downloading a cover but not when asking the service for search results.

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
