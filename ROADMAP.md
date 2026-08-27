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

- 📋 [SLIP-0006] **Initialise a git repository and publish to GitHub.**
  The project is not under version control. Blocked by SLIP-0005; publication
  is irreversible in practice once indexed.
  Progress (2026-08-27): repository initialised, branch main, one commit on it, working tree clean. Every blocker is closed and gh is authenticated as milnet01. Deliberately stopped before creating the remote and pushing: publication is the one step here that cannot be undone, and the user asked to see the state first. Remaining is the user's go-ahead, then gh repo create Slipcase --public --source . --push.
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
