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

- 📋 [SLIP-0022] **Run the test suite in CI on push.**
  The repository has no CI configuration. The project rule that all tests must
  pass before a commit is enforced only by whoever remembers to run pytest.
  This is also a prerequisite for two of the Distribution items rather than a
  separate concern: a Windows build and a macOS build cannot be produced on
  this machine, and hosted runners are the route to both. The repository is public, so Linux runner minutes cost nothing. Note that the push gate is wired but idle: the pre-push hook runs and reports it has no pipeline to gate, so landing CI means giving it a local gate script to run.
  **Layman:** Have the tests run automatically whenever code is pushed.
  Kind: chore.
  Source: in-session-2026-08-27.
  Lanes: ci.

- 📋 [SLIP-0023] **Pin dependencies so a build is reproducible.**
  requirements.txt declares minimum versions only. That is fine for developing
  against, but it means two builds of the same Slipcase version can bundle
  different PyQt6, Pillow or NumPy releases, and a rendering change arriving
  from a dependency would be untraceable to any commit here.
  Blocks nothing today; matters once the Distribution items start shipping
  binaries with the libraries baked in.
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

- 📋 [SLIP-0044] **Reconcile the spine nudge cap with what the code actually clamps to.**
  STANDARDS.md section 5 states a flat "up to 15% of spine width". The code is
  max(8, min(30, int(expected_sw * 0.15))), so the real cap is 21.6% on a 500px
  scan and 10% on a 4000px one.
  The floor and ceiling look deliberate -- they keep the search window usable at
  both extremes -- which points at the document being under-specified rather
  than the code being wrong. Decide, then make one match the other.
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
  **Layman:** Convert a whole folder of covers from a script, without opening the window.
  Kind: feature.
  Source: in-session-2026-08-27.
  Lanes: cli, core.

- 💭 [SLIP-0027] **Let users define their own case types.**
  CASE_TYPES is a dictionary in core/case_types.py, so covering a system that
  is not already listed means editing Python. Case colours are already loaded
  from resources/case_colors.json, so the precedent for data-driven case
  definitions exists in the project.
  A case type is dimensions plus a colour, which is exactly the shape that
  survives being moved into a config file. The open question is whether user
  definitions live alongside the built-ins or override them by name.
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

- 📋 [SLIP-0028] **The About dialog carries its own copy of the version string.**
  __init__.py holds __version__ as the source of truth, and .claude/bump.json
  rewrites that file and only that file. The About dialog in ui/main_window.py
  spells its version into a literal string instead of reading __version__, so
  the next bump updates one and leaves the other behind.
  The two also disagree in form already: one is a three-part version, the
  other is written to two parts.
  Fix by reading __version__ in the dialog. The bump recipe's own todo list
  anticipates this, asking that the version be stamped wherever it is shown.
  **Layman:** The version shown in About will go stale the next time the version changes.
  Kind: fix.
  Source: in-session-2026-08-27.
  Lanes: ui.

- 📋 [SLIP-0029] **The bump recipe still says the project is not version-controlled.**
  The tag todo in .claude/bump.json reads "once this becomes a git repo
  (currently not version-controlled)". The project is a git repository now, so
  the caveat is stale and the tagging step is simply live.
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

- 📋 [SLIP-0038] **A search with no APIs configured reports "No results found".**
  With no credentials both is_configured guards are false, and libretro only
  runs for a platform in LIBRETRO_SYSTEMS -- PS5, Xbox One and Xbox Series X
  are in ALL_PLATFORMS and in none of its 24 keys. Every source is then skipped
  and the user is told the query found nothing.
  Track how many sources actually ran and say "No APIs configured -- add
  credentials in Settings" when the count is zero.
  **Layman:** If you have not entered any API keys, search blames your search term.
  Kind: ux.
  Source: review-code-2026-09-01 lane-6.

- 📋 [SLIP-0039] **The export overwrite prompt runs before the .png extension is added.**
  The extension is appended after QFileDialog.getSaveFileName has already done
  its overwrite confirmation, so typing "render" silently overwrites an existing
  render.png. Set a defaultSuffix on the dialog instead of appending afterwards.
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
