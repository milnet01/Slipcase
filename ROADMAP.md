<!-- ants-roadmap-format: 1 -->

# Slipcase — Roadmap

Forward-looking work for Slipcase. Status legend: 📋 planned · 🚧 in-progress ·
✅ shipped · 💭 considered. Each actionable bullet carries a stable `[SLIP-NNNN]` id.

See [STANDARDS.md](STANDARDS.md) for the rendering pipeline, security, performance
and memory rules every item must comply with.

## Rename to Slipcase

- ✅ [SLIP-0001] **Rename the application from 3D Boxart Generator to Slipcase.**
  Product-name strings only. The domain term "3D boxart" is deliberately kept:
  it names the ScreenScraper asset type and the artifact being rendered, not
  the application. The ScreenScraper `softname` parameter is also kept as
  `BoxArt3D` by decision, because that value identifies the client to a
  third-party API that may recognise it.
  Resolved (2026-08-27): product-name strings renamed across main.py, __init__.py, ui/main_window.py, api/base.py, core/config.py, tests/conftest.py and both documents. Domain term "3D boxart" and the ScreenScraper softname kept by decision. Suite green.
  **Layman:** Change the app's name everywhere it shows to the user
  Kind: chore.
  Source: user-request-2026-08-27.
  Lanes: main, ui, api, core.

- ✅ [SLIP-0002] **Move saved settings to the config directory under the new name.**
  `core/config.py` now reads `~/.config/slipcase`. The existing
  `~/.config/boxart3d/config.json` holds live settings and must be moved so
  themes, credentials and output paths survive the rename.
  Resolved (2026-08-27): ~/.config/boxart3d moved to ~/.config/slipcase; existing config.json carried across intact.
  **Layman:** Carry your saved settings over so nothing is lost when the app is renamed
  Kind: chore.
  Source: user-request-2026-08-27.
  Lanes: core.

- ✅ [SLIP-0003] **Repoint the desktop entry at the current project location.**
  `boxart3d.desktop` sets `Exec` and `Icon` under a
  `/mnt/Emulators/storage_backup_2026-05-08/` path that no longer holds the
  project, so launching from the desktop cannot work. Rename the file to match
  the application and correct both paths.
  Resolved (2026-08-27): renamed to slipcase.desktop; Exec and Icon repointed at the current project root; Name and StartupWMClass updated.
  **Layman:** The desktop shortcut points at a folder that no longer exists, so it cannot start the app
  Kind: fix.
  Source: in-session-2026-08-27.

- ✅ [SLIP-0004] **Replace the installed launcher entry filed under the old name.**
  A copy of the old entry is installed at
  `~/.local/share/applications/boxart3d.desktop`. It carries the same stale
  paths and the former application name.
  Resolved (2026-08-27): slipcase.desktop installed under ~/.local/share/applications and the old boxart3d entry removed.
  **Layman:** Remove the old menu shortcut and install one under the new name
  Kind: chore.
  Source: in-session-2026-08-27.

## Publication

- ✅ [SLIP-0005] **Review the tree for personal data and third-party copyright before publishing.**
  Gate for SLIP-0006. Personal data: absolute paths naming the user's home and
  drives, any credential reachable from the tree, and local machine detail in
  `.claude/`. Copyright: verified 2026-08-27 — no logo artwork is shipped. `resources/` holds four app icons and a hex-colour table. Console names appear as short rendered text on spines, which is trademark use rather than copied artwork.
  Progress (2026-08-27): scan complete, decisions outstanding. Personal data — no email addresses and no hardcoded credentials found; the two password strings in `ui/settings_dialog.py` are form labels. Credentials live in `~/.config/slipcase/config.json`, outside the tree. `.claude/settings.local.json` is the one genuinely personal file, naming the user's home directory and an unrelated media drive; SLIP-0015 excludes it. Two stale absolute paths under the retired drive were found and fixed rather than published. Copyright — no logo artwork ships. Outstanding before SLIP-0006: SLIP-0014 licence, SLIP-0015 gitignore, SLIP-0016 icon provenance. Publication itself remains gated on the user.
  Resolved (2026-08-27): review complete and its three blockers closed (SLIP-0014 licence, SLIP-0015 gitignore, SLIP-0016 icon provenance). Final sweep was run over STAGED content rather than the working tree, which is the set that would actually publish. Personal data: no credentials and no addresses in the tree; the one personal file is excluded by gitignore. Four machine-specific absolute paths were found; three were removed by making the Claude Code hook paths derive from CLAUDE_PROJECT_DIR, the convention four sibling projects already use. The fourth is the desktop entry, where the freedesktop spec requires absolute paths and README documents editing them. Copyright: no logo artwork ships; icons confirmed original. Commit identity publishes the author's real name and email, raised explicitly and confirmed by the user as intended.
  **Layman:** Check nothing private or owned by someone else is in the code before it goes public
  Kind: security.
  Source: user-request-2026-08-27.

- ✅ [SLIP-0006] **Initialise a git repository and publish to GitHub.**
  The project is not under version control. Blocked by SLIP-0005; publication
  is irreversible in practice once indexed.
  Progress (2026-08-27): repository initialised, branch main, one commit on it, working tree clean. Every blocker is closed and gh is authenticated as milnet01. Deliberately stopped before creating the remote and pushing: publication is the one step here that cannot be undone, and the user asked to see the state first. Remaining is the user's go-ahead, then gh repo create Slipcase --public --source . --push.
  Resolved (2026-08-27): published to github.com/milnet01/Slipcase as a public repository. Five commits pushed; main tracks origin/main.
  **Layman:** Put the project on GitHub once it has been checked over
  Kind: release.
  Source: user-request-2026-08-27.

- ✅ [SLIP-0014] **Add a licence file before the repository goes public.**
  The project ships no LICENSE or COPYING file. Without one, published code
  carries no grant of rights and defaults to all-rights-reserved, which is
  rarely what a public repository intends. Blocker for SLIP-0006.
  Resolved (2026-08-27): MIT licence chosen by the user. LICENSE added; README and STANDARDS.md § 1 updated, the latter having still read "Private project". Copyright holder written as "Slipcase contributors" rather than a personal name — see the note on this item.
  **Layman:** Pick and add the licence that says what others may do with this code.
  Kind: release.
  Source: in-session-2026-08-27.

- ✅ [SLIP-0015] **Add a .gitignore before the first commit.**
  The tree has no .gitignore. `__pycache__/` and `.pytest_cache/` are present
  and must not be committed. `.claude/settings.local.json` holds local machine
  paths naming the user's home directory and an unrelated media drive, so it
  is the one file in the tree that is genuinely personal. Blocker for SLIP-0006.
  Resolved (2026-08-27): .gitignore added covering Python bytecode, virtualenvs, the pytest and lint caches, OS files, and .claude/settings.local.json — the one file in the tree holding machine-specific absolute paths.
  **Layman:** Tell git which local-only files to leave out, including one holding your own folder paths.
  Kind: chore.
  Source: in-session-2026-08-27.

- ✅ [SLIP-0016] **Confirm the app icons are original work.**
  `resources/` ships four PNG icons. Their provenance cannot be established
  from the files, and it is the one copyright question in the tree that a scan
  cannot answer. If they were taken from an icon set, its licence governs
  redistribution.
  Resolved (2026-08-27): user confirmed the icons were generated for them by an AI assistant at their direction, so they are original work carrying no third-party set licence. No attribution needed and nothing blocks publication on this count.
  **Layman:** Confirm the app's icon images are yours to publish.
  Kind: release.
  Source: in-session-2026-08-27.

## Distribution

Getting a runnable Slipcase into a user's hands. Separate from Publication,
which covers the source repository going public.

- 📋 [SLIP-0018] **Publish an AppImage for Linux.**
  Bundle the interpreter, PyQt6 and the imaging dependencies into a single
  self-contained executable so the app runs without a Python environment.
  Builds on the same machine family it targets, so this is the cheapest of
  the three platforms to reach from here.
  **Layman:** One file a Linux user downloads and runs — nothing to install.
  Kind: package.
  Source: user-request-2026-08-27.

- 📋 [SLIP-0019] **Publish a Windows build.**
  Two things must be settled before packaging. The config layer writes to
  ~/.config/slipcase and sets POSIX permission bits (0o700 on the directory,
  600 on the file), which have no Windows equivalent. And slipcase.desktop is
  a freedesktop launcher entry that Windows does not read, so the installed
  shortcut needs a separate mechanism.
  Building needs a Windows machine or a Windows CI runner.
  **Layman:** A Windows download people can run without installing Python.
  Kind: package.
  Source: user-request-2026-08-27.

- 📋 [SLIP-0020] **Publish a macOS build.**
  Ship an .app bundle. macOS is POSIX, so the config layer's permission bits
  carry over, but the desktop entry does not — a bundle declares its own
  launcher metadata.
  Building needs a Mac or a macOS CI runner; it cannot be cross-built from
  Linux. Running without a Gatekeeper warning additionally needs signing and
  notarisation, which requires a paid Apple developer account — decide whether
  that cost is worth paying or whether an unsigned build with install
  instructions is acceptable.
  Decided (2026-09-02, user): ship UNSIGNED with install instructions. A
  paid Apple developer account is not being bought, so the first launch
  shows Gatekeeper's "unidentified developer" warning and the README
  must document the right-click -> Open step that clears it. Signing and
  notarisation are out of scope for this item; reopen only if the
  warning proves to be a real barrier.
  **Layman:** A Mac download that opens like any other Mac app.
  Kind: package.
  Source: user-request-2026-08-27.

- 📋 [SLIP-0030] **Sign release assets so an update can be verified.**
  Prerequisite for the in-app updater, and separate work: it changes how a
  release is published rather than what the app does.
  Generate an Ed25519 keypair, embed the public half in the app, and have the
  release step sign every downloadable artifact and upload the signature
  alongside it under the artifact's own name plus .sig. finbreak's updater
  refuses any download whose signature does not verify, which is what stops a
  compromised or spoofed release host from installing arbitrary code.
  Key custody is the part to decide deliberately: the private key must never
  be committed, and finbreak backs that with a test that scans the tree for
  private-key material. Signing needs an Ed25519 implementation, which means a
  cryptography dependency this project does not have yet.
  Blocked-by: SLIP-0018 (nothing to sign until a build artifact exists).
  **Layman:** Put a tamper-proof seal on each download so the app can tell a real release from a fake one.
  Kind: security.
  Source: user-request-2026-08-27.
  Lanes: packaging, security.

- 📋 [SLIP-0031] **Offer an opt-in in-app auto-update, modelled on finbreak.**
  Port the design used by the finbreak app, whose contract is documented in tests/features/auto_update/spec.md within that project.
  Shape of it: off by default and enabled in Settings; a background check asks
  the release host for the newest tag; on a newer, signed, non-skipped version
  the user is offered Later, Skip this version, or Update now; Update now
  downloads, verifies the signature, installs and relaunches.
  Five properties are what make it safe rather than merely working, and each
  is worth carrying over. Install sits behind an Installer seam, because the
  platforms differ in kind: Linux can replace the running AppImage in place,
  while Windows cannot overwrite its own locked executable and needs a
  detached helper to swap it after the app exits. The feature is inert off a
  packaged build, so running from source is unaffected. Network access is
  confined to one module, which suits this project since api/base.py already
  restricts downloads to an allowlist and a release host would be a new
  egress. A failed check is silent, so being offline is not an error. Skip
  persists across restarts and Later does not.
  macOS is the open question: finbreak implements Linux and Windows only, so
  there is no design to copy for a .app bundle.
  Blocked-by: SLIP-0018 (a build to update into), SLIP-0030 (signatures to
  verify), SLIP-0006 (a release host to check).
  **Layman:** The app can notice a new version, ask if you want it, and install it for you.
  Kind: feature.
  Source: user-request-2026-08-27.
  Lanes: core, ui, security.

## Quality and tooling

Keeping the stated requirements enforced rather than merely written down, and
making a build reproducible.

- ✅ [SLIP-0021] **Cover the API security invariants with tests.**
  CLAUDE.md lists the download allowlist, credential scrubbing and the download
  size cap as rules that must hold in every change. The test suite imports only
  from core/, so api/ has no coverage at all: `_is_allowed_url`,
  `_sanitize_message` and the MAX_DOWNLOAD_BYTES cut-off could each be removed
  by a refactor and the suite would stay green.
  These are pure functions with no network in them, so they are among the
  cheapest tests in the project to write.
  Resolved (2026-09-01): tests/test_security.py locks the URL allowlist
  (including the userinfo, suffix and scheme spoofing vectors), redirect
  revalidation, credential scrubbing for all seven key names, the 50 MB
  download cap enforced during streaming, the decompression-bomb ceiling and
  the image-format restriction -- 22 tests, no network. Written alongside the
  code review that found the allowlist was checked on the requested URL rather
  than the fetched one.
  **Layman:** The safety rules are written down but nothing checks they are still there.
  Kind: test.
  Source: in-session-2026-08-27.
  Lanes: api, tests.

- ✅ [SLIP-0022] **Run the test suite in CI on push.**
  The repository has no CI configuration. The project rule that all tests must
  pass before a commit is enforced only by whoever remembers to run pytest.
  This is also a prerequisite for two of the Distribution items rather than a
  separate concern: a Windows build and a macOS build cannot be produced on
  this machine, and hosted runners are the route to both. The repository is public, so Linux runner minutes cost nothing. Note that the push gate is wired but idle: the pre-push hook runs and reports it has no pipeline to gate, so landing CI means giving it a local gate script to run.
  Resolved (2026-09-02): scripts/local-ci.sh holds the one list of
  checks (ruff, pytest) and .github/workflows/ci.yml calls that same
  script, so the local gate and GitHub cannot drift. The machine-wide
  pre-push hook discovers the script by name, so the push gate is no
  longer idle -- it ran and passed on the pushing commit. Actions pinned
  to immutable SHAs, checkout with persist-credentials: false. First CI
  run was green in 43s.
  **Layman:** Have the tests run automatically whenever code is pushed.
  Kind: chore.
  Source: in-session-2026-08-27.
  Lanes: ci.

- ✅ [SLIP-0023] **Pin dependencies so a build is reproducible.**
  requirements.txt declares minimum versions only. That is fine for developing
  against, but it means two builds of the same Slipcase version can bundle
  different PyQt6, Pillow or NumPy releases, and a rendering change arriving
  from a dependency would be untraceable to any commit here.
  Blocks nothing today; matters once the Distribution items start shipping
  binaries with the libraries baked in.
  Resolved (2026-09-02): requirements.lock pins the runtime exactly,
  transitive dependencies included, resolved on the Python version CI
  uses; requirements-dev.txt pins the two gate tools so a linter release
  cannot redden a commit that changed no code. requirements.txt stays as
  the readable declaration of direct dependencies, which is how a newer
  release gets noticed. CI installs from the pinned files. Verified
  twice: a clean local Python 3.12 venv built only from them runs the
  suite green, and the CI run on the pushing commit did the same on a
  hosted runner.
  **Layman:** Lock the exact library versions so two builds of one release are identical.
  Kind: package.
  Source: in-session-2026-08-27.
  Lanes: packaging.

- ✅ [SLIP-0024] **Scaffold a CHANGELOG.**
  There is no CHANGELOG.md. The bump recipe in .claude/bump.json already
  expects one and carries a todo to scaffold it in Keep a Changelog format on
  the first version bump.
  Worth doing before the repository is public, so the first release has notes
  rather than a bare tag.
  Resolved (2026-09-01): CHANGELOG.md scaffolded in Keep a Changelog format
  with a [1.0.0] section for the initial release and an [Unreleased] section
  carrying this review's fixes. The bump recipe's todo is satisfied.
  **Layman:** A file listing what changed in each release.
  Kind: doc.
  Source: in-session-2026-08-27.
  Lanes: docs.

- 📋 [SLIP-0025] **Break up the MainWindow class.**
  MainWindow is by some distance the largest unit in the tree, and owns the
  menu bar, both panels, image loading, PNG and split-cover export, batch
  processing, animation export, online search, themes and the recent-files
  list. Panel construction alone accounts for much of it.
  The practical cost is testability: behaviour reachable only through this
  class is why ui/ has no tests. Splitting the export and batch paths out into
  their own modules would make them testable without a running Qt window.
  Low urgency and worth doing incrementally rather than as one rewrite.
  **Layman:** Split the biggest file so each piece does one job.
  Kind: refactor.
  Source: in-session-2026-08-27.
  Lanes: ui.

- 📋 [SLIP-0041] **Wrap user-visible strings in tr() so the UI can be translated.**
  There is not one tr() call in the tree. ~/.claude/standards/languages/qt.md
  makes it an idiom from the first commit, on the grounds that retrofitting
  translation across a finished UI costs many times more than never skipping it.
  Roughly 60 literals in main_window alone -- menu items, group box titles,
  tooltips, field labels.
  No user-visible bug today, since STANDARDS.md claims no localisation. The cost
  of leaving it grows monotonically, so the cheap move is to wrap new strings
  from now on and retrofit the two builder methods in one pass.
  **Layman:** Groundwork so the app could be offered in other languages later.
  Kind: enhancement.
  Source: review-code-2026-09-01 lanes 4 and 6.

- 📋 [SLIP-0042] **Version the config schema so a value's type can change safely.**
  DEFAULT_CONFIG has no version key and _deep_merge copies any saved value over
  a typed default with no validation. Unknown keys survive a downgrade, which is
  fine, but a change to an existing key's TYPE has no migration path.
  The 2026-09-01 pass added a _cfg() helper that falls back on a bad type, so
  the app no longer fails to start -- but that is a guard, not a migration.
  Blocks the saveGeometry() change, which necessarily alters window_geometry's
  type.
  **Layman:** Lets settings files from older versions be upgraded instead of breaking.
  Kind: enhancement.
  Source: review-code-2026-09-01 lanes 2 and 4.

- 📋 [SLIP-0043] **Skip the no-op resample in the perspective warp.**
  _perspective_quad calls cv2.resize (and the PIL equivalent on the fallback
  path) to the size the image already is: front_shaded is front_w x front_h and
  spine_shaded is spine_w x front_h at both call sites. That is a full
  INTER_LANCZOS4 pass over roughly 1.3 MP for no change, twice per render, and
  a second resample of already-resized cover art costs sharpness.
  Guard both with `if image.size != (src_w, src_h)`.
  **Layman:** Removes a slow image-resize step that does nothing, twice per render.
  Kind: perf.
  Source: review-code-2026-09-01 lane-1.

- ✅ [SLIP-0044] **Reconcile the spine nudge cap with what the code actually clamps to.**
  STANDARDS.md section 5 states a flat "up to 15% of spine width". The code is
  max(8, min(30, int(expected_sw * 0.15))), so the real cap is 21.6% on a 500px
  scan and 10% on a 4000px one.
  The floor and ceiling look deliberate -- they keep the search window usable at
  both extremes -- which points at the document being under-specified rather
  than the code being wrong. Decide, then make one match the other.
  Resolved (2026-09-02): the document took the correction, as this item
  expected. Section 5 now states the 15% of expected spine width AND the
  8-30 pixel clamp, and says why the clamp exists -- it keeps the search
  window usable on a small scan and bounded on a large one, which is
  what makes the effective percentage vary.
  **Layman:** The written rule for spine detection does not match what the code does.
  Kind: doc-fix.
  Source: review-code-2026-09-01 lane-2.

- 📋 [SLIP-0045] **STANDARDS section 8 says search runs in parallel within a single thread.**
  Section 8 says search "queries all configured APIs in parallel (within a
  single worker thread)". SearchWorker.run calls them strictly sequentially,
  each behind a rate limiter, and one thread cannot issue three blocking HTTP
  calls in parallel.
  Two lanes flagged it independently and both declined to pick a side: either
  the wording means "parallel with the UI" and should say so, or genuine
  concurrency was intended and SearchWorker is the wrong shape. Contract
  document, so it runs through review-contract rather than being edited
  directly.
  **Layman:** A line in the standards document contradicts itself.
  Kind: doc-fix.
  Source: review-code-2026-09-01 lanes 3 and 6.

- 📋 [SLIP-0046] **Field labels are not linked to their controls for screen readers.**
  No setBuddy links any label to its control and none carries a mnemonic, so a
  screen reader announces an unnamed edit box; the search field has a
  placeholder and no accessible name. The preview label is fixed at 150x200 and
  clips its own prompt text at large font scales, and the busy spinner honours
  no reduced-motion preference.
  STANDARDS.md section 6 claims only a shortcut table -- all ten of which are
  implemented -- so this is filed on general principles rather than against a
  named standard.
  **Layman:** Screen-reader users hear unnamed boxes instead of field names.
  Kind: accessibility.
  Source: review-code-2026-09-01 lanes 4 and 6.

- 📋 [SLIP-0047] **Cache the font object, and debounce the preview rescale.**
  Only the font PATH is cached; ImageFont.truetype() is rebuilt on every probe
  of _fit_text's binary search, which is 30-40 font-file parses per spine and
  repeats per image in batch mode. An lru_cache on (path, size) closes it.
  Separately, PreviewWidget.resizeEvent re-scales the full-resolution pixmap
  with SmoothTransformation on every resize event, on the GUI thread. Coalesce
  with a single-shot timer and cache one downscaled pixmap.
  **Layman:** Two small speedups: reusing loaded fonts, and not re-scaling the preview on every pixel of a window drag.
  Kind: perf.
  Source: review-code-2026-09-01 lanes 2 and 4.

- 📋 [SLIP-0048] **The window has no icon under Wayland.**
  main() calls neither setDesktopFileName nor setWindowIcon, though
  slipcase.desktop ships an Icon= line and resources/ holds four PNG sizes. On
  X11 the title-bar icon comes from _NET_WM_ICON, which Qt writes only from
  setWindowIcon; on Wayland matching is by app_id, which Qt takes from
  desktopFileName(). Plasma 6 defaults to Wayland here, so today there is no
  icon on either path. Two lines in main().
  **Layman:** The app shows a generic icon in the taskbar instead of its own.
  Kind: fix.
  Source: review-code-2026-09-01 lane-4.

- 📋 [SLIP-0049] **Two running copies can overwrite each other's settings.**
  Each instance holds a full in-memory copy loaded at startup and whoever calls
  save() last wins wholesale. Enter credentials in the second window, close the
  first afterwards, and its stale snapshot erases them.
  The 2026-09-01 atomic-write change makes each save all-or-nothing but does not
  make it a merge. Wants an flock around load+save, or a re-read and re-merge
  inside save().
  **Layman:** Running the app twice can lose settings you entered in the other window.
  Kind: fix.
  Source: review-code-2026-09-01 lane-2.

- 📋 [SLIP-0050] **Honour XDG_CONFIG_HOME for the config location.**
  Config hardcodes Path.home() / ".config" / "slipcase" and ignores
  $XDG_CONFIG_HOME. That conforms to STANDARDS.md section 7 as written, so the
  document is the thing to change first if this is wanted.
  **Layman:** Put settings where the user's system says they should go.
  Kind: enhancement.
  Source: review-code-2026-09-01 lane-2.

- 📋 [SLIP-0051] **Full-cover detection cannot be overridden.**
  is_full_cover decides on aspect ratio alone, and the accepted band for the
  Blu-ray case contains 16:9 while the DVD band contains 4:3 and 3:2. A
  landscape front-only artwork is therefore always split and two thirds of it
  discarded, with no way to say no.
  The code matches STANDARDS.md section 4 step 2 as written; the missing escape
  hatch is the defect.
  **Layman:** If the app wrongly decides your image is a wraparound cover, you cannot tell it otherwise.
  Kind: ux.
  Source: review-code-2026-09-01 lane-2.

- 📋 [SLIP-0064] **The JSON request path applies no host or scheme validation.**
  download_image() runs every URL through _is_allowed_url on every redirect hop
  since 2026-09-01. get() does not: it builds full_url from base_url and a
  relative path with `startswith("http")` as its only test, so "TLS only" on the
  JSON path rests entirely on the hardcoded API_URL constants being right.
  That is true today. It is not enforced, and a base_url taken from a response
  or a config would not be caught.
  Route get() through the same check, with the two API hosts added to the set or
  a second allowlist for them.
  **Layman:** The rule that all traffic is HTTPS is enforced for image downloads but not for the data requests.
  Kind: security.
  Source: review-code-2026-09-01 lane-3.
  Lanes: api, security.

- 📋 [SLIP-0065] **The request timeout is per-read, not a deadline.**
  timeout=(10, 30) bounds the gap between reads, not the total. A server sending
  one byte every 29 seconds holds a worker thread and a connection open forever
  while never reaching MAX_DOWNLOAD_BYTES, so neither the size cap nor the
  timeout fires.
  Add a wall-clock check inside the iter_content loop.
  **Layman:** A server that trickles data very slowly can tie up a search indefinitely.
  Kind: security.
  Source: review-code-2026-09-01 lane-3.
  Lanes: api, security.

- ✅ [SLIP-0066] **Decide whether BMP and GIF need to be accepted image formats.**
  _ALLOWED_IMAGE_FORMATS is {PNG, JPEG, WEBP, BMP, GIF}. The comment above it
  says the list exists to "reject complex formats with larger attack surface",
  but nothing records why BMP and GIF are in it -- the app only ever renders a
  cover. If the intent was minimum attack surface, both are droppable.
  Separately worth recording: ScreenScraper credentials travel as query
  parameters, so they land in the upstream's access logs (CWE-598). The upstream
  API mandates that form, so there is nothing to fix -- but it should be written
  down rather than rediscovered by the next review.
  Resolved (2026-09-02): user decided to drop both.
  _ALLOWED_IMAGE_FORMATS is now PNG, JPEG and WEBP, with the reasoning
  kept beside it so adding a format back is a deliberate decision. The
  ScreenScraper credentials-in-query-string exposure (CWE-598) is
  recorded in _auth_params' docstring as accepted rather than missed --
  the upstream API mandates that form, the transport is HTTPS with
  verify=True, and _sanitize_message strips those keys before display.
  Two tests lock the accepted set; both were mutation-checked.
  **Layman:** The download filter accepts two image formats the app has no obvious use for.
  Kind: investigate.
  Source: review-code-2026-09-01 lane-3.
  Lanes: api, security.

- 📋 [SLIP-0067] **Dragging the spine slider re-runs the whole detector on the GUI thread.**
  Every valueChanged calls _update_split_preview, which calls split_full_cover,
  which calls detect_spine_bounds unconditionally -- the full 16-band analysis.
  That result does not depend on the offsets at all. It is then followed by three
  full-resolution crops, three convert("RGBA") calls and three pixmap
  conversions, all on the GUI thread, with a slider range up to plus or minus 150.
  Against STANDARDS.md section 2, "the main thread is never blocked".
  Compute detect_spine_bounds once in _set_front_image and cache it; have
  _update_split_preview only re-crop; add a ~100ms debounce.
  **Layman:** Adjusting the spine position feels sluggish because the app redoes work that cannot have changed.
  Kind: perf.
  Source: review-code-2026-09-01 lane-5.
  Lanes: ui, core.

- 📋 [SLIP-0068] **Nested thread pools contend during batch rendering.**
  BoxRenderer.render opens a ThreadPoolExecutor(max_workers=2) per render. In
  batch mode that sits inside a ProcessPoolExecutor of up to 4 processes, with
  OpenCV's own internal pool underneath -- up to 4 x 2 x N threads contending on
  a 4-core machine. The per-render pool is also allocated and torn down for every
  image in the batch.
  Measure before changing anything: the parallel warp is a real win for a single
  render and may still be one under the process pool.
  **Layman:** Batch mode can start far more threads than the machine has cores.
  Kind: perf.
  Source: review-code-2026-09-01 lane-1.
  Lanes: core.

- 📋 [SLIP-0069] **Bring the workers and the animation dialog up to the project's own conventions.**
  Three STANDARDS.md section 3 breaches, none behavioural:
  AnimationDialog builds its entire UI inline in __init__, where both sibling
  dialogs use the required _build_<component>() methods.
  RenderWorker.__init__'s parameters (front, back, title, serial, platform,
  spine_color) are unannotated, and no worker run() has a return annotation or a
  docstring, against "type annotations throughout" and "docstrings required on
  all public classes and functions". Same for the front/back/image parameters of
  three main_window handlers.
  A mypy run with --disallow-untyped-defs would enumerate the full set.
  **Layman:** Some code does not follow the style rules the project wrote down for itself.
  Kind: refactor.
  Source: review-code-2026-09-01 lanes 5 and 6.
  Lanes: ui.

- 📋 [SLIP-0070] **Font discovery is Linux-only with no probe for other platforms.**
  _get_font tries five hardcoded Linux paths and then falls back to
  ImageFont.load_default(). The 2026-09-01 pass fixed the worst half -- the
  fallback now receives the requested size, so text is no longer rendered at a
  fixed ~10px -- but the discovery itself still finds nothing outside those five
  paths.
  This blocks nothing today, since the project targets Linux, and it becomes
  live the moment SLIP-0019 or SLIP-0020 ships a Windows or macOS build.
  Blocked-by: nothing, but worth doing with those.
  **Layman:** On macOS or Windows the spine text falls back to a basic font.
  Kind: fix.
  Source: review-code-2026-09-01 lane-2.
  Lanes: core, packaging.

- 📋 [SLIP-0071] **libretro is contacted on every search with no way to opt out.**
  The ScreenScraper and TheGamesDB lookups are gated on is_configured, so a user
  who has entered no credentials contacts neither. The libretro lookup is gated
  only on the platform being in LIBRETRO_SYSTEMS, so it runs on every search
  regardless, and there is no per-source toggle anywhere in Settings.
  Search terms leaving the machine on an explicit user action is consented by the
  act, so this is a preference rather than a privacy defect -- but the asymmetry
  is undocumented and a user cannot turn it off.
  **Layman:** Every search reaches out to the libretro thumbnail site whether you want it to or not.
  Kind: ux.
  Source: review-code-2026-09-01 lane-6.
  Lanes: ui, api.

- ✅ [SLIP-0072] **The animation frame count does not say that bounce doubles it.**
  Frame count maxes at 120 and bounce is checked by default, so
  `angles += angles[-2:0:-1]` yields 2n-2 = 238 frames in the file. Neither the
  spinbox label nor its tooltip says so, and the estimated output size a user
  might reason about is therefore out by a factor of two.
  Related to SLIP-0036, which bounds the memory; this one is about the label.
  Resolved (2026-09-02): frames_in_file() holds the arithmetic and both
  the dialog's live total and the export's progress maximum call it, so
  the label and the file cannot disagree. The dialog shows the real
  count as the spinbox or the bounce checkbox changes -- 24 frames with
  bounce reads 46, and 120 reads 238, the figure this item cited. Both
  controls' tooltips now say bounce nearly doubles the file.
  **Layman:** Asking for 120 frames with bounce on actually produces 238.
  Kind: ux.
  Source: review-code-2026-09-01 lane-6.
  Lanes: ui.

- 📋 [SLIP-0073] **download_spine and ScreenScraperResult.spine_url have no callers.**
  Both have zero callers tree-wide, tests included. No contract document
  promises a spine download, so the reviewing lane correctly declined to file it
  as a zombie feature -- the question is whether it was meant to be wired up
  (the app does generate spines, and a real one would be better than a generated
  one) or whether it is leftover surface to delete.
  Decide, then either wire it into the search dialog or remove it with its
  dataclass field.
  **Layman:** A piece of the cover-art API code is never used by anything.
  Kind: investigate.
  Source: review-code-2026-09-01 lane-3.
  Lanes: api.

- 📋 [SLIP-0088] **Online cover-art search has never been verified against the live APIs.**
  The 2026-09-01 verify-delivery pass ran every user-facing promise except this
  one. Fifteen were executed -- render, spine generation, real-case proportions,
  split, batch, animation, transparent PNG, the two output size targets, the app
  launch, the rename, the settings location, the desktop entry and the export
  filename. Searching ScreenScraper, TheGamesDB and libretro was reported
  `unverified`, because it needs live network calls and real credentials, which
  the skill routes to an explicit ask rather than running unasked.

  What WAS checked: the feature is reachable (Search Online in both the menu and
  as a button), and the offline half of the libretro path builds correct URLs --
  including the percent-encoding fixed that day, verified against `100% Orange
  Juice`, `#IDARB` and `Ratchet &amp; Clank`.

  What was NOT checked: that any of the three services actually answers, that the
  responses still parse, or that a downloaded image reaches the canvas. The
  2026-09-01 pass changed all three clients -- search_game now raises instead of
  returning an empty list, is_configured requires all four ScreenScraper
  credentials, and the redirect path is revalidated -- so this is the code most
  in need of a live run and the code that has had none.

  Needs a human with credentials, or a recorded-response fixture (vcrpy or
  similar) so it can run in CI without them. The second is the better answer and
  composes with SLIP-0022.
  Progress (2026-09-02): the libretro third is now verified live, and
  the run found SLIP-0089 -- the lookup asked for a filename the server
  does not have, so that path had never worked for any title a person
  would type. That is the argument for this item stated as evidence: the
  offline tests were green throughout, because the URL builder matched
  its specification and the specification was wrong about the server.
  tests/test_libretro.py carries an opt-in live check behind
  SLIPCASE_LIVE_API, which is what a fixture cannot replace for a naming
  contract that lives on someone else's server. ScreenScraper and
  TheGamesDB remain unverified: no credentials are configured on this
  machine (all four ScreenScraper fields and the TheGamesDB key are
  empty), so neither the live run nor the agreed fixture recording can
  be made. Recording needs the user's credentials once. Kept open for
  those two thirds.
  **Layman:** The one feature nobody has actually run end to end against the real services.
  Kind: test.
  Source: verify-delivery-2026-09-01.
  Lanes: api, tests.

## Feature ideas

Suggested rather than requested. Each is worth a decision before it is worth
building.

- 💭 [SLIP-0026] **Offer a command-line mode for batch conversion.**
  Batch conversion already exists in BatchWorker, including a parallel path,
  but it is reachable only by opening the app and using the menu. main.py does
  nothing but launch the GUI.
  The audience is the argument: someone filling a RetroArch or LaunchBox
  thumbnail library is working across a whole ROM set, on a machine that may
  have no desktop session at all. The rendering core takes no Qt dependency,
  so a CLI entry point would mostly be argument parsing over code that is
  already there.
  Decide first whether that audience is one this project wants to serve.
  Declined (2026-09-02, user): GUI only. The project keeps one way in,
  so batch conversion stays reachable through the window and main.py
  keeps launching nothing else. Recorded rather than deleted so the idea
  is not re-proposed; reopen only on a real request for headless use.
  **Layman:** Convert a whole folder of covers from a script, without opening the window.
  Kind: feature.
  Source: in-session-2026-08-27.
  Lanes: cli, core.

- 📋 [SLIP-0027] **Let users define their own case types.**
  CASE_TYPES is a dictionary in core/case_types.py, so covering a system that
  is not already listed means editing Python. Case colours are already loaded
  from resources/case_colors.json, so the precedent for data-driven case
  definitions exists in the project.
  A case type is dimensions plus a colour, which is exactly the shape that
  survives being moved into a config file. The open question is whether user
  definitions live alongside the built-ins or override them by name.
  Accepted (2026-09-02, user): build it, loaded from a file. Promoted
  from considered to planned. The open design question in this item's
  body still stands and is the first thing the work must settle: whether
  user definitions sit alongside the built-ins or override them by name.
  resources/case_colors.json is the precedent for the loading path, and
  SLIP-0053 (a truncated case_colors.json kills startup) is the failure
  mode a second data file must not repeat."
  **Layman:** Let people add a case for a console the app does not know about yet.
  Kind: feature.
  Source: in-session-2026-08-27.

## Project record

- ✅ [SLIP-0007] **Migrate the roadmap to the roadmap store.**
  The store is the source of truth and `ROADMAP.md` becomes its render. This
  file was authored to bootstrap that migration, because both `roadmap_migrate`
  and `roadmap_log` refuse a project with no roadmap file.
  Resolved (2026-08-27): ROADMAP.md authored in ants-v1 to bootstrap, migrated to the store (project_id 20, slug slipcase), and re-rendered from it. roadmap_query now answers source: store.
  **Layman:** Keep the to-do list in a shared database rather than only in a text file
  Kind: chore.
  Source: user-request-2026-08-27.

- ✅ [SLIP-0008] **Declare the project layout in `.ants/project.json`.**
  The project has no `.ants` directory, so tooling infers source, test and doc
  locations. This project keeps its code in top-level packages rather than
  `src/`, which is the case inference handles worst.
  Resolved (2026-08-27): .ants/project.json written from project_settings op:detect — source_roots ["."], test_roots ["tests"], roadmap ROADMAP.md. detect confirmed the default walk indexed 3 of 26 source files. docs_dir, specs_dir and changelog left undeclared because those paths do not exist.
  **Layman:** Tell the tools where the code, tests and docs actually live
  Kind: chore.
  Source: user-request-2026-08-27.

- ✅ [SLIP-0009] **Write a README.**
  The project has no README. An independent reader given the project's own
  documents identified this as the most likely home of the answer it could not
  find, and a public repository needs one.
  Resolved (2026-08-27): README.md written for a non-technical reader — what the app does, who it is for, the case types, install and run steps, and where settings and logins are kept. Three drafted claims were checked against the code and corrected before landing: spine colours come from the per-platform table rather than from the cover, libretro is a boxart lookup rather than a search, and the Python floor is stated as 3.12 rather than assuming newer versions. The licence section records that none is chosen yet, matching SLIP-0014.
  **Layman:** Write the front page that tells a newcomer what this is and how to run it
  Kind: doc.
  Source: adopt-project-2026-08-27.

- ✅ [SLIP-0010] **State what makes a render "realistic" enough to ship.**
  The stated purpose names four things: a desktop GUI, realistic 3D renders,
  RetroArch compatibility and LaunchBox style. Three carry a checkable bar;
  "realistic" carries none. The pipeline is documented in detail, but every
  such statement constrains the method rather than judging the result.
  Resolved (2026-08-27): user decided the bar is their own judgement by eye, with no written test. STANDARDS.md § 1 now states that explicitly, names the three dimensions that DO carry a checkable bar and where they live, and warns against reading the rendering pipeline as the quality bar since it constrains method rather than result. The gap adopt-project found was the silence, not the absence of a test — stating it closes the item.
  **Layman:** Write down how we would know a finished box render actually looks good enough
  Kind: doc.
  Source: adopt-project-2026-08-27.

- ✅ [SLIP-0011] **Reconcile the default viewing angle between the two documents.**
  `CLAUDE.md` gives the default as roughly 25-30 degrees; `STANDARDS.md` gives
  it as 30 degrees with a user-adjustable range. One of the two is the bar.
  Resolved (2026-08-27): settled from the code rather than by choosing between documents. The default is 30.0 in core/config.py, core/renderer.py and the ui/main_window.py label, so STANDARDS.md was already correct and CLAUDE.md carried the loose range. CLAUDE.md now states 30 degrees with the 5-60 adjustable range.
  **Layman:** Two documents disagree about the default camera angle; pick one
  Kind: doc-fix.
  Source: adopt-project-2026-08-27.

- ✅ [SLIP-0017] **Correct the description of the resources directory.**
  `CLAUDE.md` describes `resources/` as holding platform logos and case
  colours. Verified 2026-08-27: it holds four app icons and a hex-colour
  table, and no logo artwork. The claim overstated the project's copyright
  exposure and was taken at face value when the publication item was first
  filed.
  Resolved (2026-08-27): CLAUDE.md described resources/ as holding platform logos. It holds application icons and the case-colour table; the line now says so.
  **Layman:** A project note says the app ships console logos; it does not, and the note should be corrected.
  Kind: doc-fix.
  Source: in-session-2026-08-27.

- ✅ [SLIP-0074] **STANDARDS section 4 promises RGBA output while section 11 drops the alpha channel.**
  Section 4's output table says Transparency "Yes (RGBA)" for both RetroArch and
  LaunchBox. Section 11 optimisation 3 drops the alpha channel entirely whenever
  the image is fully opaque, which is every render with a White or Black
  background.
  The code follows section 11 and is right to -- an opaque RGBA image wastes a
  quarter of the file. Section 4 is the side to change: it should say the output
  is RGBA where transparency is present.
  Resolved (2026-09-02): section 4's table now reads "RGBA where
  present", with one sentence saying an opaque render is written as RGB
  and why. Section 11 was the correct side, as this item said.
  **Layman:** Two parts of the standards document disagree about whether exported images keep transparency.
  Kind: doc-fix.
  Source: review-code-2026-09-01 lane-1.

- ✅ [SLIP-0075] **STANDARDS section 6 says the status bar has white text; it has dark text.**
  Section 6 states "Status bar: Accent background with white text". themes.py
  uses accent_text, which is #2e3440 on Nord and #1a1a1a on Monokai -- dark, and
  correctly so, since the accent backgrounds are light and white would be
  unreadable. Section 6's own colour-slot table already describes the real rule.
  Document side.
  Resolved (2026-09-02): section 6 now names accent_text and says it is
  dark in both themes because the accent backgrounds are light.
  **Layman:** A colour rule in the standards document does not match what the app does.
  Kind: doc-fix.
  Source: review-code-2026-09-01 lane-4.

- ✅ [SLIP-0076] **Two persisted config keys are missing from the STANDARDS schema.**
  ui.auto_filename and ui.last_export_directory are written by main_window and
  appear in neither section 7's schema block nor DEFAULT_CONFIG. Harmless at
  runtime, since every read passes a default -- but one of the two sides is
  wrong, and the reviewing lanes could not tell which: are they intended config
  keys the schema forgot, or scratch state that should not be persisted?
  Decide, then either add them to both or stop persisting them.
  Section 7's schema gained compress_level on 2026-09-01, so it is otherwise
  current.
  Resolved (2026-09-02): decided that both keys are genuine user
  preferences -- a checkbox state and a remembered export folder -- so
  they are declared rather than dropped. Added to DEFAULT_CONFIG and to
  section 7's schema, and the persistence rule now names the export
  directory. A mutation-checked test fails if the window persists
  another ui key nothing declares, so the two sides cannot drift apart
  again.
  **Layman:** The settings file holds two values the documentation does not list.
  Kind: doc-fix.
  Source: review-code-2026-09-01 lanes 2 and 4.

- ✅ [SLIP-0077] **STANDARDS section 8 says libretro is queried always; it is not.**
  Section 8's search strategy says "libretro (always)". The lookup is gated on
  the platform appearing in LIBRETRO_SYSTEMS, which holds 24 keys -- PS5, Xbox
  One and Xbox Series X are in ALL_PLATFORMS and in none of them, so for those
  three platforms libretro is never queried.
  SLIP-0038 covers the user-facing half (the misleading "No results found").
  This is the document side.
  Resolved (2026-09-02): section 8 now says libretro is queried only
  where the platform appears in LIBRETRO_SYSTEMS, and points at
  SLIP-0038 for what a user is shown when every source is skipped.
  **Layman:** The search documentation overstates which sources are checked.
  Kind: doc-fix.
  Source: review-code-2026-09-01 lane-6.

- ✅ [SLIP-0078] **STANDARDS section 11 names np.tile for gradients; the code uses broadcasting.**
  Section 11 says gradients are built with np.tile. core/image_utils.py uses
  np.newaxis and np.broadcast_to instead, which is strictly better -- broadcasting
  does not materialise the array. The code is the right side; the wording is
  stale.
  Resolved (2026-09-02): section 11 now names np.newaxis with
  np.broadcast_to and says broadcasting is deliberate over np.tile
  because it never materialises the repeated array.
  **Layman:** A performance rule names a technique the code improved on.
  Kind: doc-fix.
  Source: review-code-2026-09-01 lane-2.

- ✅ [SLIP-0079] **The ScreenScraper media-selection docstring contradicts REGION_PRIORITY.**
  _select_best_media's docstring says "prefer US > World > SS > first available".
  REGION_PRIORITY is (us, wor, eu, uk, jp, ss) -- Europe, UK and Japan are
  missing from the docstring and SS is last rather than third. The constant is
  the behaviour; the docstring is wrong.
  Resolved (2026-09-02): the comment now gives all six regions in
  REGION_PRIORITY order and says to read the constant if the two ever
  disagree.
  **Layman:** A comment lists the wrong order for choosing which regional cover to use.
  Kind: doc-fix.
  Source: review-code-2026-09-01 lane-3.

- ✅ [SLIP-0080] **Two case-texture docstrings describe features that are not drawn.**
  _draw_psp_front's docstring says "border indent + UMD/card slot" and the body
  draws only the indent. _draw_cardboard_front says "fold lines and slight
  texture grain" and draws no grain.
  Either implement the missing halves or correct the docstrings. Worth deciding
  alongside SLIP-0034, which covers the six case types whose spine overlay is
  empty -- the same question of how complete the texture set is meant to be.
  Resolved (2026-09-02): both docstrings corrected to describe what is
  drawn, each naming this item, rather than inventing the missing art.
  How complete the texture set should be stays SLIP-0034's question.
  **Layman:** Comments promise case details the code does not actually draw.
  Kind: doc-fix.
  Source: review-code-2026-09-01 lane-1.

- 📋 [SLIP-0081] **STANDARDS section 12's rewritten shutdown rule owes a cold review.**
  The 2026-09-01 fix pass rewrote section 12's closeEvent clause. The old text
  prescribed worker.quit() plus worker.wait(2000) -- the exact handshake that
  caused the crash, since every worker overrides run() without calling exec(),
  so quit() reaches no event loop and wait() simply times out. The new text
  prescribes requestInterruption() and forbids clearing a reference to a live
  QThread.
  That changes what a conformer writes, which is CLAUDE.md rule 14's test for
  whether a review-contract gate is owed. It is, and it did not run: the fix
  session's scope was the code review. Run
  `review-contract STANDARDS.md --genre standard` before anyone implements
  against that section.
  Recorded in commit 9e04017's body.
  **Layman:** A rule that was changed needs an independent read before anyone builds to it.
  Kind: doc.
  Source: in-session-2026-09-01.

- 📋 [SLIP-0082] **There is no design document.**
  The project has README.md (what it does), STANDARDS.md (what is true of the
  code) and ROADMAP.md (what is planned), and no docs/design.md -- the document
  that records the decisions and the reasoning behind them.
  The gap is visible in this review's own output: several findings came down to
  "the code does X, the standard says Y, and nobody can tell which was intended"
  -- SLIP-0044's nudge clamp, SLIP-0076's two undocumented config keys,
  SLIP-0073's unused spine download. A design document is where that intent
  lives.
  ~/.claude/skeleton/files/docs/design.md is the skeleton; it is authored
  directly and gated with `review-contract docs/design.md --genre adr`.
  **Layman:** Nothing written down explains why the app is built the way it is.
  Kind: doc.
  Source: in-session-2026-09-01.
  Lanes: docs.

- ✅ [SLIP-0083] **There is no SECURITY.md, on a public repository that handles credentials.**
  The repository is public, the app stores API credentials on disk and downloads
  images from three third-party services. CLAUDE.md section Security Requirements
  lists real invariants -- an allowlist, credential scrubbing, a download cap, a
  decompression-bomb limit -- and the 2026-09-01 review found a live SSRF in the
  first of them.
  There is no stated way to report the next one privately, and no statement of
  what is in scope. GitHub reads SECURITY.md and surfaces it on the Security tab
  and in the report flow.
  Short: how to report, what is in scope, and what response to expect.
  Resolved (2026-09-02): SECURITY.md states the private reporting route,
  what is in scope, what is not, and that only the latest release is
  supported. GitHub private vulnerability reporting was disabled, so the
  document would have pointed at a channel that did not exist -- enabled
  as part of this item. The out-of-scope section records the
  ScreenScraper query-string credentials as an accepted upstream
  constraint, so a reporter is not sent to write up a finding already
  ruled on. Every code claim was checked against the source.
  **Layman:** Nobody who finds a security problem knows how to report it.
  Kind: security.
  Source: in-session-2026-09-01.
  Lanes: docs, security.

- ✅ [SLIP-0084] **There is no CONTRIBUTING.md.**
  The repository is public and has no contributor guidance. The pieces already
  exist and are scattered: the setup steps are in README.md, the code style and
  the all-tests-must-pass gate are in STANDARDS.md, and the commit-message shape
  is enforced by a hook nobody outside the project can read.
  Worth writing once verify-instructions can be run against it -- that skill
  executes a document's steps rather than reading them, which is the check this
  particular file needs.
  Resolved (2026-09-02): CONTRIBUTING.md gathers the setup, the gate,
  the change expectations, the commit shape and the reporting routes
  that were scattered across README.md, STANDARDS.md and the git
  history. This item asked that it be written once verify-instructions
  could be run against it, so the steps were executed rather than read:
  a fresh clone of the public repository, a Python 3.12 venv, install
  from requirements.lock and requirements-dev.txt, the gate green in
  that clone, and python3 main.py launching and staying up. One claim in
  this item's own body turned out to be false and is not repeated in the
  document -- the commit-message shape is enforced by no hook; the only
  hook here is pre-push, which runs the gate.
  **Layman:** Nothing tells someone how to set the project up and what is expected of a change.
  Kind: doc.
  Source: in-session-2026-09-01.
  Lanes: docs.

- ✅ [SLIP-0085] **There is no .editorconfig, so the shell formatter cannot run.**
  check-code probes shfmt because the tree holds a shell script
  (.claude/hook-on-py-edit.sh), then skips it as "no config to run against":
  without an .editorconfig section whose glob selects *.sh, shfmt would diff
  every file against its own tab default and report a conforming project as
  entirely malformed.
  One small file fixes it. Declare the shell indent the project actually uses,
  and note that a blanket [*] section does not count -- it is what a project
  writes when it has not thought about shell, and produces exactly that noise.
  Worth declaring the Python indent at the same time; STANDARDS.md section 3
  already states 4 spaces and no tabs.
  Resolved (2026-09-02): .editorconfig declares the Python and shell
  styles in separate sections, so shfmt has a glob that selects *.sh and
  no longer skips. switch_case_indent is declared because this project
  indents case branches and shfmt does not by default. One mechanical
  reformat followed -- shfmt normalises the spacing around case pattern
  separators and that is not configurable -- so
  .claude/hook-on-py-edit.sh took it; it still parses and passes
  shellcheck. shfmt is not in the CI gate, which stays ruff plus pytest;
  it runs from check-code locally.
  **Layman:** One code checker has no style to check against and is skipped every time.
  Kind: chore.
  Source: check-code-2026-09-01.
  Lanes: ci.

- 📋 [SLIP-0086] **There is no subsystem map, so review tooling partitions by directory.**
  indie_review_partition looks for docs/subsystems.md or a `## Module map`
  heading in CLAUDE.md. Neither exists, so it falls back to grouping source files
  by directory -- which review-code's own procedure forbids, since a directory is
  not a subsystem.
  On the 2026-09-01 sweep it returned ui/ as a single 8-file lane containing the
  1170-line main_window.py, roughly a quarter of the project by line count, and
  its too_coarse flag did not fire because that flag counts files rather than
  lines. The partition had to be built by hand.
  A short module map fixes it permanently and makes every future review cheaper.
  The hand-built partition from that sweep is a good starting point: render
  engine, image analysis and spine, API clients, window construction, window
  actions and workers, dialogs.
  Progress (2026-09-02): the map is written and the partition is pinned
  -- docs/subsystems.md describes eleven lanes in prose and
  .indie-review/partition.json holds the file-to-lane assignment,
  including the CI workflow and the gate script, which are not Python
  and which the computed partition never covered. Left OPEN because it
  does not yet achieve what this item asked for: indie_review_partition
  still answers partition_source "computed" with map_lane_count 0,
  having ignored the heading form, the "- name -- summary" bullet form
  the verb's own hint names, and the JSON override, before and after
  committing them. So the tooling still groups by directory and still
  reports ui/ as one 2,968-line lane. Filed against the MCP in
  Slipcase_Ants_MCP_Feedback.md, 2026-09-02. The documents stand on
  their own for a human or for an orchestrator that reads them directly;
  close this once the verb picks one of them up.
  **Layman:** The code-review tooling has to guess how the project is organised.
  Kind: doc.
  Source: in-session-2026-09-01.
  Lanes: docs.

- 💭 [SLIP-0087] **There is no code-pairs list for facts that live in two places.**
  close-findings walks .claude/code-pairs.json on every sweep -- the things that
  must change together but share no searchable token, which no grep will ever
  surface. The file does not exist, so that step was skipped on 2026-09-01.
  This review found several genuine pairs the hard way and they are what would
  seed it: MAX_IMAGE_PIXELS in api/base.py against the figure quoted in CLAUDE.md
  and STANDARDS.md section 10; the DEFAULT_CONFIG keys against section 7's schema
  block; CASE_TYPES against the README's case list (which was wrong, fixed in 0d2616c);
  the worker signal set against section 2's threading table (which was wrong).
  Filed as considered rather than planned: a pair earns its place the first time
  a sweep finds a defect across it, and four is thin. Worth starting when the
  next one appears.
  **Layman:** A list of things that must be changed together, so one does not drift from the other.
  Kind: chore.
  Source: in-session-2026-09-01.
  Lanes: ci, docs.

## Defects

- ✅ [SLIP-0012] **Export filename repeats the boxart phrase when no title is known.**
  In `ui/main_window.py` the export dialog falls back to a placeholder name and
  then appends the same phrase again, so the suggested filename doubles it.
  Cosmetic, and only on the fallback path.
  Resolved (2026-08-27): the export dialog's fallback name was the same phrase it then appends, producing a doubled suggestion. The fallback is now Untitled, so the suggested filename reads Untitled 3D Boxart.png. Suite green.
  **Layman:** With no title set, the suggested save name says "3D Boxart" twice
  Kind: fix.
  Source: in-session-2026-08-27.
  Lanes: ui.

- ✅ [SLIP-0013] **Repoint the Claude Code edit hook at the current project path.**
  `.claude/settings.json` runs its post-edit hook from a `/mnt/Storage/` path.
  That drive is retired, so the hook cannot fire. The script itself is present
  in `.claude/`.
  Resolved (2026-08-27): post-edit hook repointed from the retired /mnt/Storage path to the current project root.
  **Layman:** An automatic check that runs after each code edit is pointed at a drive that no longer exists
  Kind: fix.
  Source: in-session-2026-08-27.

- ✅ [SLIP-0028] **The About dialog carries its own copy of the version string.**
  __init__.py holds __version__ as the source of truth, and .claude/bump.json
  rewrites that file and only that file. The About dialog in ui/main_window.py
  spells its version into a literal string instead of reading __version__, so
  the next bump updates one and leaves the other behind.
  The two also disagree in form already: one is a three-part version, the
  other is written to two parts.
  Fix by reading __version__ in the dialog. The bump recipe's own todo list
  anticipates this, asking that the version be stamped wherever it is shown.
  Resolved (2026-09-02): core/version.py now holds __version__ as the
  single definition and ui/main_window.py imports it, so the About
  dialog cannot go stale. The version moved out of the root __init__.py
  because the repository root is a sys.path entry rather than an
  importable package, which is why the dialog could not read it in the
  first place. Three source-inspection regression tests lock it --
  importing ui.main_window pulls in QtWidgets, which a CI runner may
  lack the desktop libraries for.
  **Layman:** The version shown in About will go stale the next time the version changes.
  Kind: fix.
  Source: in-session-2026-08-27.
  Lanes: ui.

- ✅ [SLIP-0029] **The bump recipe still says the project is not version-controlled.**
  The tag todo in .claude/bump.json reads "once this becomes a git repo
  (currently not version-controlled)". The project is a git repository now, so
  the caveat is stale and the tagging step is simply live.
  Resolved (2026-09-02): .claude/bump.json's tag todo no longer says the
  project is not version-controlled, and the CHANGELOG todo now points
  at the file that exists rather than asking for one to be scaffolded.
  The recipe's version_source moved to core/version.py with SLIP-0028.
  **Layman:** A note in the release config is out of date now that git is set up.
  Kind: doc-fix.
  Source: in-session-2026-08-27.
  Lanes: docs.

- 📋 [SLIP-0032] **The drop shadow is displaced too far and clipped square at the canvas edge.**
  generate_shadow pads its canvas by blur_radius*2 on each side and places the
  silhouette inside that padding. _render_shadow crops from (0,0) without
  removing the padding, so the shadow lands about 2x the blur further right and
  down than the named _SHADOW_OFFSET constants imply. The box's right edge sits
  close to the canvas edge, so the shadow is then cut off square instead of
  fading, and the final getbbox crop locks that hard edge in.
  Fix subtracts blur_radius*2 when cropping and widens the canvas to cover the
  offset plus blur. Left out of the 2026-09-01 fix pass because it changes
  canvas geometry and wants its own before/after comparison.
  **Layman:** The shadow under the case sits too low and is cut off flat on one side.
  Kind: fix.
  Source: review-code-2026-09-01 lane-1.

- 📋 [SLIP-0033] **A loaded back cover is advertised in the menu and discarded by the renderer.**
  render() assigns back_image and never reads it again; its own docstring says
  "optional, unused in current view". STANDARDS.md section 6 advertises Open
  Back Cover as Ctrl+Shift+O, and the split export does use it, so the feature
  is half-real: the shortcut works, the render ignores it.
  Decide which way it goes -- render the back face, or say in the UI that the
  back cover is used only by the split export.
  **Layman:** You can load a back cover with Ctrl+Shift+O and it does not appear in the render.
  Kind: fix.
  Source: review-code-2026-09-01 lane-1.

- 📋 [SLIP-0034] **Six of fifteen case types get an empty spine texture overlay.**
  generate_spine_texture dispatches DVD, Blu-ray and the cardboard group only.
  CD Jewel, Switch, DS, 3DS, PSP and PS Vita fall through to a fully
  transparent overlay, which is then composited for no effect. Silent no-op
  rather than an error, so nothing reports it.
  **Layman:** Some case types are missing the moulded detail on the spine that others have.
  Kind: fix.
  Source: review-code-2026-09-01 lane-1.

- 📋 [SLIP-0035] **The search preview downloads the full-size cover, then downloads it again.**
  PreviewWorker calls download_front to fill a 150x200 label, pulling the
  full-size image up to the 50 MB cap. _download_selected then requests the same
  URL again instead of reusing _preview_cache. Reuse the cached image for the
  front, and request a thumbnail URL where the API exposes one.
  **Layman:** Selecting a search result downloads the whole cover twice.
  Kind: fix.
  Source: review-code-2026-09-01 lane-6.

- 📋 [SLIP-0036] **Animation export can allocate several gigabytes with no bound.**
  Frame count runs to 120, bounce roughly doubles it to 238, and output width
  runs to 2048. Every frame is retained at full resolution before the encoder
  is reached -- on the order of 5 GB at the top of both ranges. Nothing in the
  dialog or the worker bounds the product.
  Either estimate it in the dialog and refuse or warn above a threshold, or
  stream frames to the encoder instead of accumulating them.
  **Layman:** A long, wide animation can use all your memory before it starts saving.
  Kind: fix.
  Source: review-code-2026-09-01 lane-6.

- 📋 [SLIP-0037] **Output width accepts values that exhaust memory.**
  width_spin ranges to 8192 and the renderer multiplies by the supersample
  factor, so the working canvas reaches roughly 16k x 21k RGBA -- about 1.4 GB
  per layer, with several alive at once. Image.MAX_IMAGE_PIXELS guards decoding,
  not Image.new, so it does not cover this. STANDARDS.md section 4 documents no
  target above 1200px.
  Clamp output_width in BoxRenderer, and lower the spinner maximum.
  **Layman:** The width box lets you pick a size far larger than anything the app documents.
  Kind: fix.
  Source: review-code-2026-09-01 lane-1.

- ✅ [SLIP-0038] **A search with no APIs configured reports "No results found".**
  With no credentials both is_configured guards are false, and libretro only
  runs for a platform in LIBRETRO_SYSTEMS -- PS5, Xbox One and Xbox Series X
  are in ALL_PLATFORMS and in none of its 24 keys. Every source is then skipped
  and the user is told the query found nothing.
  Track how many sources actually ran and say "No APIs configured -- add
  credentials in Settings" when the count is zero.
  Resolved (2026-09-02): SearchWorker counts the sources it actually
  queried and reports it with the results. Where the count is zero -- no
  credentials and a platform absent from LIBRETRO_SYSTEMS -- the dialog
  says no sources are available and points at Settings, instead of
  blaming the search term. Three tests, including PS5, which is in
  ALL_PLATFORMS and in none of LIBRETRO_SYSTEMS' keys.
  **Layman:** If you have not entered any API keys, search blames your search term.
  Kind: ux.
  Source: review-code-2026-09-01 lane-6.

- ✅ [SLIP-0039] **The export overwrite prompt runs before the .png extension is added.**
  The extension is appended after QFileDialog.getSaveFileName has already done
  its overwrite confirmation, so typing "render" silently overwrites an existing
  render.png. Set a defaultSuffix on the dialog instead of appending afterwards.
  Resolved (2026-09-02): one helper appends the extension and asks
  before replacing, but only where it changed the name -- if the user
  typed the extension, the dialog's own confirmation already covered the
  right file, so there is no double prompt. Applied to both save paths:
  the PNG export and the animation export, which had the same defect and
  was not named in this item.
  **Layman:** Typing a filename without .png can overwrite an existing file with no warning.
  Kind: fix.
  Source: review-code-2026-09-01 lane-5.

- 📋 [SLIP-0040] **The window walks down-right on each restart and can reopen off-screen.**
  On X11 geometry() returns the client rect excluding the frame while
  setGeometry positions the client area, so each close/reopen cycle shifts the
  window by the title-bar height. There is also no validation against the
  current screens, so a window last closed on a second monitor reopens
  unreachable when that monitor is gone.
  Qt's answer is saveGeometry()/restoreGeometry(), which also handles maximised
  state. That changes the stored value's type, so it needs the config schema
  version item to land first.
  **Layman:** The window creeps across the screen every time you reopen it, and can vanish if you unplug a monitor.
  Kind: fix.
  Source: review-code-2026-09-01 lane-4.

- ✅ [SLIP-0052] **SearchWorker.run is unguarded, so a failure leaves the progress bar spinning forever.**
  The client construction at the top of run() and the two emits at the bottom sit
  outside every try. An exception there means finished_signal is never sent, so
  _on_search_done never runs: the progress bar stays visible and Search stays
  disabled until the dialog is closed. PyQt6 also treats an unhandled exception
  in a thread as fatal.
  The 2026-09-01 pass wrapped BatchWorker.run for exactly this reason and did
  not carry the same guard to SearchWorker, PreviewWorker or DownloadWorker.
  Wrap each run() body and emit finished_signal from a finally.
  Resolved (2026-09-02): SearchWorker.run is wrapped and both
  results_ready and finished_signal are emitted from a finally, so a
  failure anywhere -- including constructing a client -- still releases
  the progress bar and the Search button. One claim in this item's body
  was wrong and is worth recording: PreviewWorker and DownloadWorker
  already carry an outer try/except that emits error, so neither needed
  the change. Two tests cover it, including the constructor case that
  was the actual gap.
  **Layman:** If an online search hits an unexpected error, the search never appears to finish.
  Kind: fix.
  Source: review-code-2026-09-01 lane-6.

- ✅ [SLIP-0053] **A truncated case_colors.json kills startup; a missing one degrades silently.**
  core/spine_generator.py loads the file at module scope with a bare json.load
  guarded only by an exists() check. A truncated or malformed file raises at
  import time, before any window exists, so the app cannot start and there is no
  in-app route to recovery. A missing file leaves _CASE_COLORS empty, and every
  platform then falls back to grey with nothing said.
  Wrap in try/except (OSError, ValueError), and report the degraded state rather
  than letting it look like a design choice.
  Resolved (2026-09-02): the colour table is read through
  _load_case_colors, which returns the table and what went wrong. A
  truncated or unreadable file degrades to an empty table instead of
  raising during import, and a missing one is distinguished from it. The
  status bar reports either at start-up, so grey spines no longer look
  like a design choice. Four tests, one of which asserts the shipped
  resources/case_colors.json still loads.
  **Layman:** If the colour file is damaged the app will not start, and if it is absent every spine turns grey with no warning.
  Kind: fix.
  Source: review-code-2026-09-01 lane-2.

- 📋 [SLIP-0054] **Spine-detection failures are hidden by a blanket except around the whole analysis.**
  _refine_spine_bounds is wrapped by its caller in `except Exception: return
  geo_left, geo_right`. STANDARDS.md section 5 justifies falling back to the
  geometric estimate, but not doing it silently -- and the catch is wide enough
  to hide a genuine bug anywhere in the 55 lines of analysis, including the
  empty-slice np.percentile case when hi <= lo.
  The scipy import also sits inside the function, so a missing or broken SciPy
  disappears the documented Stage 2 entirely with no signal.
  Hoist the import to module scope, narrow the catch to (ValueError,
  IndexError), and set a status message when the fallback fires.
  **Layman:** If the automatic spine finder breaks, you get the rough guess and no hint that anything went wrong.
  Kind: fix.
  Source: review-code-2026-09-01 lane-2.

- 📋 [SLIP-0055] **Shading silently does nothing for an unrecognised direction, and wraps above intensity 1.0.**
  apply_directional_shading has no else branch: an unrecognised `direction`
  returns the image unshaded with no error. And an intensity above 1.0 makes the
  gradient factor negative, so astype(np.uint8) wraps to bright values instead of
  clamping to black.
  Neither is reachable from the UI today, which is why this is filed rather than
  fixed -- but both are silent, and the function is public.
  **Layman:** Two small robustness holes in the shading helper.
  Kind: fix.
  Source: review-code-2026-09-01 lane-2.

- 📋 [SLIP-0056] **generate_reflection assumes a 4-band image.**
  `r, g, b, a = reflection.split()` raises ValueError on an RGB input rather than
  converting. Every current caller passes RGBA, so this is latent, but the
  function is public and its signature does not say so.
  **Layman:** Passing a non-transparent image to the reflection helper raises instead of converting.
  Kind: fix.
  Source: review-code-2026-09-01 lane-2.

- 📋 [SLIP-0057] **A very small render width can raise LinAlgError from the perspective solve.**
  If proj_spine_w truncates to 0 the spine destination quad is degenerate and
  np.linalg.solve raises LinAlgError; the OpenCV path produces a garbage matrix
  instead of failing. Not reachable at the spinner's 128px minimum, but
  BoxRenderer is constructible directly with any width, and the batch and
  animation paths both build one by hand.
  Validate the computed quad and raise something a caller can act on.
  **Layman:** At extreme settings the renderer can fail with an unhelpful maths error.
  Kind: fix.
  Source: review-code-2026-09-01 lane-1.

- 📋 [SLIP-0058] **A uniform region makes any spine nudge look like a 20% improvement.**
  The acceptance test is `best_score > geo_score * 1.2`, which implements
  STANDARDS.md section 5's 20% bar correctly except when geo_score is 0 -- a
  uniform region at the geometric estimate -- where any non-zero score clears it.
  Also worth reconciling: the internal docstring says the nudge goes to the
  nearest strong edge, while np.argmax takes the strongest in the window.
  **Layman:** The spine detector can accept a bad adjustment when the image has no detail where it is looking.
  Kind: fix.
  Source: review-code-2026-09-01 lane-2.

- 📋 [SLIP-0059] **The progress bar is shared by batch and animation, so one hides it for the other.**
  _on_batch_done and _on_anim_done both call progress_bar.hide() unconditionally.
  The 2026-09-01 re-entrancy guard makes the overlapping case much harder to
  reach from the UI, but the two handlers still share one widget with no owner,
  so the coupling is still there for any future path that starts both.
  **Layman:** Running an export while a batch is going makes the progress bar disappear early.
  Kind: fix.
  Source: review-code-2026-09-01 lane-5.

- 📋 [SLIP-0060] **Three workers can read the same PIL image object concurrently.**
  RenderWorker, BatchWorker and AnimationWorker all read self._front_image, and
  PIL images are not documented thread-safe. The 2026-09-01 re-entrancy guard
  makes concurrent starts much harder to reach, so this is latent rather than
  live -- but the guard is a UI-level check, not an ownership rule, and nothing
  in the workers says the image must not be shared.
  **Layman:** Two long jobs running at once share one image in memory, which PIL does not promise is safe.
  Kind: fix.
  Source: review-code-2026-09-01 lane-5.

- 📋 [SLIP-0061] **Use 3D Boxart is re-enabled for results that have none.**
  search_dialog re-enables use3d_btn unconditionally after a 3D download
  completes, rather than re-deriving it from the newly selected result's
  box3d_url. Selecting a result without one immediately afterwards leaves the
  button enabled.
  **Layman:** The 3D Boxart button can look available for a game that does not have one.
  Kind: fix.
  Source: review-code-2026-09-01 lane-6.

- 📋 [SLIP-0062] **A failed preview shows two words and discards the reason.**
  The error handler is `lambda msg: self.preview_label.setText("No preview")` --
  it binds msg and throws it away, and nothing reaches the status line. Show the
  reason (escaped, as the 2026-09-01 pass now does for the other API-supplied
  strings).
  **Layman:** When a preview image fails to load you are told "No preview" and nothing else.
  Kind: fix.
  Source: review-code-2026-09-01 lane-6.

- 📋 [SLIP-0063] **The export base name is derived in three places and only one handles a root folder.**
  The "derive a base name" logic exists at three call sites and only the first
  guards an empty parent folder name. An image loaded from a filesystem root
  exports as " 3D Boxart.png".
  Extract one helper. The 2026-09-01 pass added _safe_filename() for the
  sanitising half, which is the natural home for this.
  **Layman:** Exporting an image loaded from a drive root can produce a filename starting with a space.
  Kind: fix.
  Source: review-code-2026-09-01 lane-5.

- ✅ [SLIP-0089] **The libretro lookup asked for a filename that does not exist.**
  A libretro thumbnail is named after the full No-Intro ROM name, which carries
  a region tag: the SNES cover for Super Mario World is stored as
  "Super Mario World (USA).png". download_boxart built the URL from the bare
  title, and ui/search_dialog.py passes the user's typed query, so the libretro
  half of Search Online returned nothing for any title a person would type.
  Measured 2026-09-02: "Super Mario World" 404, the same name with " (USA)" 200
  and 301,072 bytes.
  Found by the first live run of the search path, which is what SLIP-0088 asked
  for. Nothing in the offline tests could have caught it -- the URL builder was
  behaving exactly as specified, and the specification was wrong about the
  server.
  Resolved (2026-09-02): download_boxart tries the exact name first, then
  " (USA)", " (World)", " (Europe)" and " (Japan)", stopping at the first hit,
  so a caller holding the full ROM name pays nothing. A total miss costs one
  request per candidate at the client's 0.5s interval. The per-system directory
  listing was considered and rejected: it is about 1 MB for the SNES alone.
  Verified live: Super Mario World, Sonic The Hedgehog and Ratchet &amp; Clank all
  resolve to real PNGs; an invented title still misses. tests/test_libretro.py
  locks the candidate order offline and carries an opt-in live check behind
  SLIPCASE_LIVE_API.
  **Layman:** Searching libretro for cover art never found anything, because it asked for the wrong filename.
  Kind: fix.
  Source: verify-delivery-2026-09-02.
  Lanes: api.
