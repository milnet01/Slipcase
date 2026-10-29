<!-- ants-spec-format: 1 -->
# SLIP-0031 — Offer an opt-in in-app update, modelled on finbreak

**Status:** accepted (2026-10-29).
**Kind:** feature.
**Source:** ROADMAP SLIP-0031 (user-request-2026-08-27). Ported from
finbreak's updater: its contract `tests/features/auto_update/spec.md`, and
`src/finbreak/services/update.py`, `update_fetch.py`,
`update_installer.py`, `update_key.py` in that repository.
**Blocked by:** SLIP-0030 (signatures to verify;
[`SLIP-0030-release-signing.md`](SLIP-0030-release-signing.md)).
SLIP-0018 and SLIP-0006 are shipped.
**Pairs with:** SLIP-0030.

If you turn it on in Settings, the app tells you when a new version is out;
on Linux and Windows it can then download, check and install it and reopen
itself, and on a Mac it opens the download page.

## 1. Goal

A packaged Slipcase can learn that a newer release exists and offer it.
The check is off until the user turns it on. On Linux and Windows,
**Update now** downloads the new file, proves the maintainer signed it,
replaces the running copy and starts the new one. On macOS the app only
says a new version is out and opens its release page. Run from source, the
feature does nothing.

## 2. Problem

1. **Nothing tells a user a release exists.** `core/version.py` holds
   `__version__`, and nothing in the app compares it with anything.
2. **Updating is by hand.** The user must find the release page, download
   the right file and replace their copy (`README.md` § Getting it running).
3. **A release host is a new kind of egress.** Every request today passes
   `api/base.py::_is_allowed_url`, whose `ALLOWED_IMAGE_DOMAINS` names only
   the three cover-art services. GitHub is not among them.
4. **The app cannot replace itself naively.** On Windows the running `.exe`
   is locked. On Linux a new copy started while the old one holds
   `ui/single_instance.py`'s lock hands over to the old one and exits
   (`main.py::main`, the `instance.acquire` branch).

## 3. Scope decisions (agreed with the user)

- **Built now, with SLIP-0030.** User, 2026-10-29.
- **macOS is notify-only.** User, 2026-10-29. The app says a new version
  is out and opens the release page. It installs nothing.
- **Linux and Windows get the full update.** User, 2026-10-29: download,
  verify, install, relaunch. Linux replaces the AppImage in place; Windows
  uses a detached helper that swaps the locked `.exe` after the app exits.
- **The five properties on the roadmap item carry over.** User,
  2026-08-27, in the item's body: an Installer seam; inert off a packaged
  build; network confined to one module; a failed check is silent; Skip
  persists and Later does not.
- **Two specs, not one.** Author, 2026-10-29. `spec-format.md` § 2 allows
  one spec per id. Signing is SLIP-0030's; this spec cites it.

Every other choice below is the author's and is open to review. Where it
departs from finbreak, § 16 says why.

## 4. Design

### 4.1 Modules

| File | New | Holds |
|------|-----|-------|
| `api/releases.py` | yes | The only code that contacts the release host: `fetch_latest_release()`, `download()`, `ALLOWED_RELEASE_HOSTS` |
| `core/updater.py` | yes | Version grammar, asset choice, `check_for_update()`, `download_and_verify()`, `remove_stale_staged_updates()` |
| `core/update_installer.py` | yes | `Installer` protocol, `AppImageInstaller`, `WindowsInstaller`, `detect_update_mode()` |
| `core/update_key.py` | yes | The public key (SLIP-0030 § 4.2) |
| `ui/update_dialog.py` | yes | The offer and its progress |
| `ui/workers.py` | no | Gains `UpdateCheckWorker`, `UpdateDownloadWorker` |
| `ui/settings_dialog.py` | no | Gains an **Updates** tab |
| `ui/main_window.py` | no | Starts the check; owns the dialog; the shutdown hook (§ 4.8) |
| `core/config.py` | no | Gains the `updates` section |
| `main.py` | no | Passes `instance.release` to `MainWindow`; runs the stale clean-up |

### 4.2 Settings

`DEFAULT_CONFIG` gains:

```python
"updates": {
    "check": False,          # off until the user ticks it
    "skipped_version": "",   # the version "Skip this version" stored
},
```

- **On means exactly `True`.** Any other stored value reads as off.
- `CONFIG_VERSION` does not change. Both keys are new, and
  `core/config.py::_deep_merge` gives an older file their defaults.
- The **Updates** tab holds one checkbox, *Check for new versions when
  Slipcase starts*. Where `detect_update_mode()` is `None` it is disabled,
  with the tooltip *Only the downloaded app can check for updates.*

### 4.3 What kind of copy is running

```python
@dataclass(frozen=True)
class UpdateMode:
    installer: Installer | None   # None means notify-only

def detect_update_mode() -> UpdateMode | None: ...
```

| Running copy | Result |
|---|---|
| Not frozen (`sys.frozen` absent) | `None` |
| Frozen, `sys.platform == "win32"` | `UpdateMode(WindowsInstaller(sys.executable))` |
| Frozen, `$APPIMAGE` names an existing file, `$APPDIR` set, and `sys.executable` resolves under `$APPDIR` | `UpdateMode(AppImageInstaller($APPIMAGE))` |
| Frozen, `sys.platform == "darwin"` | `UpdateMode(None)` |
| Anything else (a frozen Linux build run outside an AppImage) | `None` |

**The `$APPDIR` test is finbreak's** (`detect_installer`). `$APPIMAGE` is
inherited, so a copy started from inside another AppImage would otherwise
overwrite that other app's file.

**An installer whose target folder is not writable becomes notify-only.**
`Installer.can_self_update()` creates and deletes a probe file
`slipcase-update-probe-<8 random chars>` there. Failure turns the mode into
`UpdateMode(None)`.

`None` means inert: no check, no network, Settings disabled.

### 4.4 The check

`MainWindow` starts one `UpdateCheckWorker` after the window is first
shown, once per launch, only when the mode is not `None` and
`updates.check` is `True`. The worker calls:

```python
def check_for_update(config: Config, mode: UpdateMode, *,
                     fetch=releases.fetch_latest_release,
                     current: str = __version__) -> UpdateOffer | None: ...

@dataclass(frozen=True)
class UpdateOffer:
    version: str            # tag without its leading "v"
    tag: str                # the tag as published
    asset_url: str | None   # None in notify-only mode
    sig_url: str | None
```

`check_for_update` returns `None` without calling `fetch` unless
`updates.check` is exactly `True` (INV-1).

1. **The endpoint:** `GET https://api.github.com/repos/milnet01/Slipcase/releases/latest`.
   GitHub's documentation says it returns the newest release that is
   neither a draft nor a prerelease (unverified here beyond finbreak's use
   of it, `update_fetch.py::fetch_latest_release`).
2. **The version grammar**, finbreak's D13: strip one leading `v` or `V`;
   split on `.`; every part must pass `isascii() and isdigit()`; compare as
   integers, padding the shorter with zeros. A tag that does not parse is
   no offer.
3. **Offer only when** the tag is strictly newer than `current`, and its
   version is not `updates.skipped_version`.
4. **Install mode also needs the files.** The release's `assets` must hold
   exactly one asset named `installer.asset_name()` and exactly one named
   that plus `.sig`. Each needs a `browser_download_url` that passes
   `releases.is_allowed_release_url`. Otherwise no offer. The names are
   SLIP-0030 § 4.1's: `Slipcase-x86_64.AppImage`, `Slipcase-windows-x64.exe`.
5. **Notify mode needs only the tag.**
6. **Every failure is `None`.** Network, HTTP status, JSON, a missing key,
   anything: logged at debug level, never shown. The worker emits
   `offer_ready(object)` with the offer or `None`, and declares `error(str)`
   as `STANDARDS.md` § 2 requires; this worker never emits it.

### 4.5 The network module — `api/releases.py`

```python
ALLOWED_RELEASE_HOSTS: frozenset[str] = frozenset({
    "api.github.com",
    "github.com",
    "release-assets.githubusercontent.com",
    "objects.githubusercontent.com",
})
MAX_RELEASE_REPLY_BYTES = 1024 * 1024
MAX_UPDATE_BYTES = 512 * 1024 * 1024
MAX_SIGNATURE_BYTES = 64
MAX_UPDATE_SECONDS = 30 * 60

def is_allowed_release_url(url: str) -> bool: ...
def fetch_latest_release() -> dict: ...
def download(url: str, dest: Path, *, max_bytes: int,
             on_progress: Callable[[int, int], None] | None = None,
             should_stop: Callable[[], bool] | None = None) -> None: ...
```

- **Exact hosts, no subdomains.** `release-assets.githubusercontent.com` is
  where `https://github.com/milnet01/Slipcase/releases/download/v1.3.1/Slipcase-x86_64.AppImage`
  redirected on 2026-10-29 (`curl -sI`, the `location:` header).
  `objects.githubusercontent.com` served GitHub's release downloads before
  it, and is allowed so a move back does not stop every update (added
  2026-10-29 from the code review; the signature still guards each file).
  A wider `githubusercontent.com` would admit user-hosted content.
- **`ALLOWED_IMAGE_DOMAINS` does not change.** The cover-art path cannot
  reach GitHub, and the updater cannot reach a cover-art host.
- **It keeps `STANDARDS.md` § 10's rules, on its own list:** HTTPS only;
  `verify=True`; redirects followed by hand with `allow_redirects=False`,
  each hop re-checked, at most `api/base.py::MAX_REDIRECTS`; connect and read
  timeouts as `api/base.py` sets them.
- **The reply** is read under `MAX_RELEASE_REPLY_BYTES` and
  `api/base.py::MAX_DOWNLOAD_SECONDS`, with `read1()` as
  `api/base.py::_read_body` does.
- **A download** streams to `dest` under `max_bytes` and
  `MAX_UPDATE_SECONDS`. It refuses a `Content-Length` above `max_bytes`. A
  body shorter than a stated `Content-Length` is an error, so a dropped
  connection is not reported as tampering (finbreak FIBR-0327). It checks
  `should_stop()` after each read. Any failure deletes `dest`.
  `on_progress(received, total)` gives `total` as the `Content-Length`, or
  `0` when there is none.
- **Errors:** both calls raise `ReleaseError`, new in `api/releases.py`, for
  a network, HTTP, size, time or stop failure, and `OSError` for a failure
  writing `dest`. So `core/updater.py` never catches a `requests` type.
- **Each call opens its own `requests.Session` and closes it in
  `finally`** (`STANDARDS.md` § 12, API Sessions).

### 4.6 Verify before install

```python
def download_and_verify(offer: UpdateOffer, installer: Installer, *,
                        download=releases.download, on_progress=None,
                        should_stop=None) -> Path: ...
```

1. Stage two temps in `installer.target_path().parent`, named
   `slipcase-update-<8 random chars><ext>` and
   `slipcase-update-<8 random chars><ext>.sig`, each by `tempfile.mkstemp`. The same folder keeps the swap a same-filesystem
   move.
2. Download the asset, then the signature under `MAX_SIGNATURE_BYTES`.
3. The signature must be exactly 64 bytes.
4. Read the asset. Verify with `core.update_key.public_key().verify`. A
   failure raises `UpdateVerificationError`.
5. Write the verified bytes to a fresh temp and delete the download temp,
   so the file installed is the file checked (finbreak FIBR-0170). For an
   `AppImageInstaller`, set mode `0o755`.
6. Delete the signature temp. Release the in-memory copy. Return the fresh
   temp.

Any failure deletes every temp and raises: `UpdateVerificationError` for a
bad signature, `UpdateDownloadError` for a `ReleaseError`, `UpdateError` for
the disk. All three are new, in `core/updater.py`, and derive from
`UpdateError`.

### 4.7 The Installer seam

```python
class Installer(Protocol):
    def asset_name(self) -> str: ...
    def target_path(self) -> Path: ...
    def can_self_update(self) -> bool: ...
    def apply(self, new_file: Path,
              before_exit: Callable[[], None]) -> NoReturn: ...
```

`apply` either does not return, or raises `UpdateError` with the running
copy untouched and `before_exit` uncalled — except where Linux has
already replaced the file (below).

**Linux — `AppImageInstaller.apply`:**

1. `os.replace(new_file, target)`. A failure deletes `new_file` and raises.
   The old AppImage is still mounted and running, so replacing its path is
   safe.
2. Spawn the waiter, `["/bin/sh", "-c", script, "sh", str(target)]`, with
   `start_new_session=True`. The script waits until this process's pid has
   exited, at most about 60 s, then runs `exec "$1"`. **The path is an
   argument, never spliced into the script** (finbreak FIBR-0327).
   - Its environment: `PYINSTALLER_RESET_ENVIRONMENT=1`; `APPDIR`,
     `APPIMAGE` and `ARGV0` removed; `LD_LIBRARY_PATH` restored from
     `LD_LIBRARY_PATH_ORIG`, or removed where there is none. Whether
     Slipcase's PyInstaller build sets that variable is unverified; the
     restore is harmless if not.
   - Its output goes to `config_dir() / "update-relaunch.log"`, opened for
     append.
   - **A spawn failure after step 1** raises `UpdateError` with the message
     *Slipcase was updated. Close it and open it again.* The app keeps
     running.
3. Call `before_exit()`, then `os._exit(0)`.

**Waiting is required here, not only tidy.** A copy started before the old
one exits finds the single-instance lock held, asks the old copy to show
itself, and exits.

**Windows — `WindowsInstaller.apply`:**

1. Spawn the helper: the absolute `powershell.exe` under `%SystemRoot%`,
   `-NoProfile -NonInteractive -Command <script>`. Flags
   `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`, read with `getattr` so the
   code loads on Linux. **Never `DETACHED_PROCESS`**: finbreak measured that
   PowerShell started with it dies before running a line (FIBR-0444).
   - The script waits until no process's image path equals the `.exe`
     path, at most about 60 s. It waits by path, not pid, because a
     one-file build runs as two processes with the same image (finbreak
     FIBR-0131 D3). Still busy at the cap: delete the new file, exit 1, do
     not relaunch.
   - Then `Move-Item -Force` the new file over the `.exe`, retried a few
     times for antivirus locks. A move that never succeeds deletes the new
     file. Either way, `Start-Process` the `.exe`.
   - Both paths are PowerShell single-quoted with `'` doubled.
   - Environment: `PYINSTALLER_RESET_ENVIRONMENT=1`.
   - **A spawn failure** deletes `new_file` and raises `UpdateError`.
2. Call `before_exit()`, then `os._exit(0)`.

**macOS:** no installer. Notify mode only.

### 4.8 The offer dialog

`ui/update_dialog.py::UpdateDialog(QDialog)`, shown with `show()`. It never
calls `exec()`, so the main window keeps working and `closeEvent` still
runs.

- Text, plain: *Slipcase {version} is available. You have {current}.*
- **Later** closes it. Nothing is stored; the next launch offers again.
- **Skip this version** sets `updates.skipped_version` to the version and
  saves at once through `MainWindow._save_config()`.
- **Update now** (install mode):
  - While `MainWindow._busy_worker()` returns a worker, it shows *Finish or
    stop the current render first* and does nothing else.
  - Otherwise starts one `UpdateDownloadWorker` and shows a progress bar,
    determinate when `Content-Length` is known.
  - On `ready(str)`: if the dialog has since closed, delete the file and
    stop. If `_busy_worker()` returns a worker, delete the file and show the
    busy message above. Otherwise call
    `installer.apply(path, window.shutdown_for_update)`, and show an
    `UpdateError` it raises in a `QMessageBox.warning`.
  - On `error(str)`: show it in a `QMessageBox.warning`. A verification
    failure says *The download could not be verified, so nothing was
    installed.*
- **Open release page** replaces **Update now** in notify mode. It opens
  `RELEASE_PAGE + offer.tag` with `QDesktopServices.openUrl`, where
  `RELEASE_PAGE = "https://github.com/milnet01/Slipcase/releases/tag/"`.
  **The URL is never taken from the reply's `html_url`.** The tag has
  passed the grammar of § 4.4, so it holds only `v` and digits and dots.

**`MainWindow.shutdown_for_update()`** does what quitting must, because
`os._exit` skips `closeEvent`:

1. `_save_state()`, which saves the config.
2. Clears images as `closeEvent` does.
3. Calls `release_instance`, so the new copy takes the lock. It is the
   argument of `MainWindow(config, release_instance: Callable[[], None] | None = None)`.
   `main.py::main` passes `instance.release`; `None`, as `_smoke` passes,
   releases nothing.

### 4.9 Workers

Both connect `finished` to `deleteLater` at creation. `closeEvent` adds both
to the workers it interrupts and waits for (`STANDARDS.md` § 12, QThread
Lifecycle). `_busy_worker()` keeps its three workers; the update workers
join `closeEvent` only. `UpdateDownloadWorker` passes `isInterruptionRequested` as
`should_stop`, so an interrupted download deletes its temps.

| Worker | Signals |
|---|---|
| `UpdateCheckWorker` | `offer_ready(object)`, `error(str)` |
| `UpdateDownloadWorker` | `progress(int, int)`, `ready(str)`, `error(str)` |

### 4.10 Leftovers

`remove_stale_staged_updates(installer)` deletes files beside the target
that fully match `slipcase-update-[a-z0-9_]{8}` plus `<ext>` or
`<ext>.sig`, are older than one hour, and are not the target. Errors are
logged and ignored. `main.py` calls it after taking the single-instance
lock, so a second copy never deletes the first copy's download.

## 5. Invariants

The updater tests are in `tests/test_updater.py` unless named otherwise.
None touches the network: every fetch and download is an injected fake, and
signatures use a throwaway key monkeypatched over `RELEASE_PUBLIC_KEY_B64`.

- **INV-1** — The check is off by default and runs only when
  `updates.check` is exactly `True`.
  *Test:* `TestCheck::test_opt_in` — the injected fetch is never called for
  a fresh config, `False`, `"true"` or `1`; it is called for `True`.
  *Breaks when:* the default becomes `True`, or the gate tests truthiness.

- **INV-2** — Off a packaged build the feature is inert: no fetch, the
  Settings checkbox disabled.
  *Test:* `TestMode::test_source_run_is_inert` (`sys.frozen` absent →
  `detect_update_mode() is None`; `MainWindow` with `updates.check` `True`
  starts no `UpdateCheckWorker`) and `TestSettings::test_checkbox_disabled`.
  *Breaks when:* detection keys on the platform alone, or the window starts
  the worker before asking for the mode.

- **INV-3** — An offer is made only for a well-formed, strictly newer,
  non-skipped tag, and in install mode only with exactly one asset and one
  `.sig` of the platform's name on allowed hosts.
  *Test:* `TestCheck::test_offer_rules`, against current `1.3.1`: `v1.4.0`
  offers; `v1.3.1`, `v1.3.0`, `v1.3.1.0`, `v1.4-rc1`, `latest`, `v1_4.0`
  and `v١.٤.٠` do not; `v1.4.0` with no `.sig`, with two assets of the
  name, or with an `http://` URL does not; a release whose only assets are
  `Old-Slipcase-x86_64.AppImage` and its `.sig` does not; skipped `1.4.0` does not and
  `1.4.1` then does.
  *Breaks when:* the grammar uses `int()` alone (`v1_4.0` then offers), or
  the asset match uses `endswith`.

- **INV-4** — A failed check is silent and safe.
  *Test:* `TestCheck::test_failures_are_silent` — fetch raising
  `requests.ConnectionError`, `ValueError`, returning `[]`, or returning a
  dict without `tag_name` → `None`, nothing raised; and
  `TestWindow::test_no_message_on_failed_check` — no `QMessageBox` is
  shown.
  *Breaks when:* one exception type escapes `check_for_update`.

- **INV-5** — The release host is reached only through `api/releases.py`,
  only on `ALLOWED_RELEASE_HOSTS` over HTTPS, re-checked at every redirect
  hop; and `ALLOWED_IMAGE_DOMAINS` gains nothing.
  *Test:* `TestNetwork::test_redirect_hops_rechecked` (a fake session whose
  302 points at `https://example.com/` and then at `http://github.com/` —
  both refused before the second request); `TestNetwork::test_exact_hosts`
  (`evil.github.com`, `raw.githubusercontent.com` refused);
  `TestNetwork::test_network_imports_confined` — a source scan outside
  `tests/`: `requests`, `urllib.request`, `http.client` and `socket` are
  imported only under `api/`; and `tests/test_security.py` gains a case asserting
  `ALLOWED_IMAGE_DOMAINS` is exactly its three hosts.
  *Breaks when:* `download` passes `allow_redirects=True`, or
  `core/updater.py` imports `requests`.

- **INV-6** — Downloads are bounded: an over-cap stream or `Content-Length`
  aborts with the file deleted; a short body is an error; a signature that
  is not 64 bytes is refused.
  *Test:* `TestNetwork::test_caps` with a fake streamed response;
  `TestVerify::test_signature_length`.
  *Breaks when:* the size check or the short-body check is dropped.

- **INV-7** — Nothing is installed unless its signature verifies, and the
  file handed to `apply` holds exactly the verified bytes.
  *Test:* `TestVerify::test_good_signature` (the returned path's bytes equal
  the signed blob; on POSIX, with an `AppImageInstaller`, its mode is
  `0o755`; it is not the path the injected `download` wrote; no other
  `slipcase-update-*` file remains);
  `TestVerify::test_tamper` (one byte changed in the blob, then in the
  signature → `UpdateVerificationError`, every temp gone); and
  `TestDialog::test_verify_failure_never_applies` (a fake installer's
  `apply` is not called).
  *Breaks when:* verification is skipped on error, or `apply` is given the
  download temp after the check.

- **INV-8** — Skip persists across restarts; Later does not.
  *Test:* `TestDialog::test_skip_and_later` — Skip on `1.4.0`, then a new
  `Config` read from the same file: `1.4.0` is not offered, `1.4.1` is.
  Later, then a new `Config`: `1.4.0` is offered.
  *Breaks when:* Skip only sets the value without `save()`, or Later
  writes it.

- **INV-9** — Linux install: the swap is in the target's folder; a failed
  replace leaves the old file byte-identical and the app running; the
  waiter gets the path as `$1`.
  *Test:* `TestAppImage` with `subprocess.Popen` and `os._exit`
  monkeypatched: success → target holds the new bytes, the argv ends `["sh", <target>]`, the script text does not
  contain the target path, `start_new_session` is `True`, the env has
  `PYINSTALLER_RESET_ENVIRONMENT=1` and no `APPIMAGE`, and `before_exit`
  runs before `os._exit`; `os.replace` patched to raise → target unchanged, temp
  gone, `before_exit` not called; `Popen` raising → `UpdateError`,
  `before_exit` not called. The target path used is `it's here.AppImage`.
  *Breaks when:* the path is formatted into the script, or `before_exit`
  runs before the replace.

- **INV-10** — Windows install: the helper is spawned before the app
  shuts down, waits by image path, and a spawn failure changes nothing.
  *Test:* `TestWindows`, on any platform, `Popen` and `os._exit`
  monkeypatched: argv[0] ends in `powershell.exe` and is absolute when
  `SystemRoot` is set; the script contains `$_.Path -eq $exe` and no `-Id`;
  the flags omit `DETACHED_PROCESS`; a path with `'` appears doubled;
  `Popen` raising → `UpdateError`, `new_file` deleted, `before_exit` not
  called.
  *Breaks when:* the helper polls a pid, or `before_exit` runs before the
  spawn.

- **INV-11** — macOS is notify-only: it downloads nothing, and opens a
  page built from `RELEASE_PAGE` and the checked tag.
  *Test:* `TestMode::test_macos_notify` (`sys.platform` `darwin`, frozen →
  `UpdateMode(None)`); `TestDialog::test_open_release_page` — a reply whose
  `html_url` is `https://evil.example/` opens
  `https://github.com/milnet01/Slipcase/releases/tag/v1.4.0`, and the
  injected `download` is never called.
  *Breaks when:* the dialog opens `html_url`, or notify mode offers
  **Update now**.

- **INV-12** — Before the app exits for an update, the config is saved and
  the single-instance lock released. Nothing is installed while a render,
  batch or animation runs, and an `UpdateError` from `apply` is shown, not
  raised.
  *Test:* `TestWindow::test_shutdown_for_update` — a changed setting is in
  the saved file and a fresh `SingleInstance` on the same folder acquires;
  `TestDialog::test_refused_while_busy` — with a fake running worker,
  **Update now** starts no `UpdateDownloadWorker`, and a `ready` deletes its
  file without calling `apply`; `TestDialog::test_apply_error_shown` — a
  fake `apply` raising `UpdateError` shows a warning and the slot raises
  nothing.
  *Breaks when:* `shutdown_for_update` skips `_save_state`, either busy
  check is dropped, or the `ready` slot lets `UpdateError` escape.

- **INV-13** — Update workers follow `STANDARDS.md` § 12, and a download
  that finishes after its dialog closed is deleted, not installed.
  *Test:* `TestDialog::test_late_ready` — the dialog closed, then `ready`
  with a temp path: the file is gone and the fake `apply` was not called;
  `TestWindow::test_close_stops_update_workers`.
  *Breaks when:* `ready` is handled without checking the dialog, or
  `closeEvent` leaves the update workers out.

- **INV-14** — `ui/update_dialog.py` never blocks the event loop.
  *Test:* `TestDialog::test_no_exec` — a source scan finds no `.exec(` in
  the file.
  *Breaks when:* the dialog is shown with `exec()`.

- **INV-15** — Stale staged files are removed and nothing else is.
  *Test:* `TestLeftovers` — in a temp folder: an old
  `slipcase-update-abcd1234.AppImage` and `slipcase-update-abcd1234.AppImage.sig`
  go; a new one, the target, and an old `slipcase-update-notes.txt` stay; an unreadable folder raises nothing.
  *Breaks when:* the pattern is a prefix match, or the age check is dropped.

- **INV-16** — Detection does not adopt another app's AppImage, and an
  unwritable target falls back to notify-only.
  *Test:* `TestMode::test_inherited_appimage` (`$APPIMAGE` set,
  `sys.executable` outside `$APPDIR` → `None`) and
  `TestMode::test_unwritable_target` (probe creation raising
  `PermissionError` → `UpdateMode(None)`).
  *Breaks when:* detection reads `$APPIMAGE` alone.

## 6. Failure modes

- **Offline, DNS failure, GitHub down, rate-limited.** `check_for_update`
  returns `None`; nothing is shown (INV-4). GitHub limits unauthenticated
  API calls per address; one call per launch stays far inside it.
- **A release published before its files are attached.** Each job attaches
  its own files when it finishes. Until a platform's `.sig` is there, that
  platform gets no offer (INV-3). Notify mode may offer as soon as the tag
  exists.
- **A release rerun mid-download** can pair a new asset with an old `.sig`.
  Verification fails and nothing is installed (SLIP-0030 § 6).
- **An older signed file served under a newer tag.** A per-file signature
  proves who made the bytes, not which version they are. A host able to
  rewrite the release could install an older genuine release. § 15 Q1.
- **Disk full or read-only folder.** Staging fails with `UpdateError`; the
  running copy is untouched. A read-only folder is caught earlier by
  `can_self_update()` (INV-16).
- **The relaunch fails.** The new file is in place. The user starts
  Slipcase again by hand. `update-relaunch.log` holds the waiter's output.
- **Windows: the old copy never exits.** The helper gives up at its cap,
  deletes the new file and starts nothing.
- **Windows: antivirus holds the file.** The move is retried, then given
  up; the old `.exe` is relaunched.
- **The user quits during a download.** `closeEvent` interrupts the worker;
  the temps are deleted (§ 4.9).

## 7. Tests

New `tests/test_updater.py`, `unittest.TestCase` classes, plus one case in
`tests/test_security.py`. Qt cases use the offscreen platform as the
existing Qt tests do. All run on the Linux gate and on CI's Windows and
macOS jobs; platform behaviour is reached by monkeypatching `sys.platform`,
`sys.frozen`, `subprocess.Popen`, `os.replace` and `os._exit`, never by
running on that platform.

| Class | Locks |
|---|---|
| `TestCheck` | INV-1, INV-3, INV-4 |
| `TestMode` | INV-2, INV-11, INV-16 |
| `TestSettings` | INV-2 |
| `TestNetwork` | INV-5, INV-6 |
| `TestVerify` | INV-6, INV-7 |
| `TestDialog` | INV-7, INV-8, INV-11, INV-12, INV-13, INV-14 |
| `TestWindow` | INV-2, INV-4, INV-12, INV-13 |
| `TestAppImage` | INV-9 |
| `TestWindows` | INV-10 |
| `TestLeftovers` | INV-15 |
| `tests/test_security.py` new case | INV-5 |

Every test is seen failing before the code it locks exists. The modules are
new, so each first fails on import; the mutation named under its *Breaks
when* is the second run.

**What these tests do not prove.** They check the commands and the order.
They never run `/bin/sh`'s wait, PowerShell's swap, the AppImage runtime,
or GitHub's real replies. finbreak states the same limit in its contract.

### 7.1 Manual recipe, before the release that ships this is announced

Needs two real signed releases: N carrying the updater, then N+1 (§ 15 Q2).

1. **Linux:** run release N's AppImage from a folder you own; tick the
   setting; restart. Expected: the offer for N+1. **Update now** → the app
   closes and reopens; **Help → About** shows N+1. Repeat once more from
   N+1 if a later release exists.
2. **Windows** (the test machine reached by `ssh wintest`): the same with
   `Slipcase-windows-x64.exe`.
3. **macOS:** expected: the offer with **Open release page**, which opens
   N+1's page. Nobody has a Mac to hand (`README.md`); this leg is
   unverified until someone does.
4. **Tamper:** not runnable against real releases; `TestVerify` covers it.

## 8. Alternatives considered (and rejected)

- **Add GitHub to `ALLOWED_IMAGE_DOMAINS`.** One list is simpler, but it
  would let a cover-art reply send the image downloader to GitHub, and the
  updater to a cover-art host. Two lists keep each path to its own hosts.
- **Reuse `APIClient`.** Its per-host rate limiter and in-memory
  `_read_body` suit small replies. An update must stream a large file to
  disk with a longer deadline. `api/releases.py` copies the hop-checking
  pattern instead.
- **A modal dialog (`exec()`).** Simpler to code, but it blocks the event
  loop, so a render's progress stops and the window cannot close.
- **Install on macOS too.** Rejected by the user, 2026-10-29. Replacing a
  `.app` bundle that is not code-signed has no design to copy.
- **Show the release notes in the offer.** They are untrusted text from
  the reply. Deferred (§ 9).
- **Check on a timer during the session.** One check per launch is what
  finbreak does and what the roadmap describes.

## 9. Out of scope

- **Help → Check for updates**, a manual check (finbreak has one). § 15 Q3.
  Deferred; not yet queued.
- Release notes in the offer (finbreak FIBR-0152). Deferred; not yet
  queued.
- A signed release-wide manifest binding version and platform (finbreak
  FIBR-0169). § 15 Q1. Deferred; not yet queued.
- Updating a Flatpak or distribution package. None exists.
- Delta or background downloads.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 | `tests/test_updater.py::TestCheck::test_opt_in` |
| INV-2 | `tests/test_updater.py::TestMode::test_source_run_is_inert`, `TestSettings::test_checkbox_disabled` |
| INV-3 | `tests/test_updater.py::TestCheck::test_offer_rules` |
| INV-4 | `tests/test_updater.py::TestCheck::test_failures_are_silent`, `TestWindow::test_no_message_on_failed_check` |
| INV-5 | `tests/test_updater.py::TestNetwork`, `tests/test_security.py` new case |
| INV-6 | `tests/test_updater.py::TestNetwork::test_caps`, `TestVerify::test_signature_length` |
| INV-7 | `tests/test_updater.py::TestVerify`, `TestDialog::test_verify_failure_never_applies` |
| INV-8 | `tests/test_updater.py::TestDialog::test_skip_and_later` |
| INV-9 | **Partial:** `tests/test_updater.py::TestAppImage` checks the command and the order; the real wait and relaunch are § 7.1 step 1 |
| INV-10 | **Partial:** `tests/test_updater.py::TestWindows` checks the command and the order; the real swap is § 7.1 step 2 |
| INV-11 | **Partial:** `tests/test_updater.py::TestMode::test_macos_notify`, `TestDialog::test_open_release_page`; a real Mac is § 7.1 step 3, unrun |
| INV-12 | `tests/test_updater.py::TestWindow::test_shutdown_for_update`, `TestDialog::test_refused_while_busy`, `TestDialog::test_apply_error_shown` |
| INV-13 | `tests/test_updater.py::TestDialog::test_late_ready`, `TestWindow::test_close_stops_update_workers` |
| INV-14 | `tests/test_updater.py::TestDialog::test_no_exec` |
| INV-15 | `tests/test_updater.py::TestLeftovers` |
| INV-16 | `tests/test_updater.py::TestMode::test_inherited_appimage`, `test_unwritable_target` |
| § 4.5 the redirect host | **nothing** — measured once on 2026-10-29; if GitHub moves it, the check fails silently and no offer appears |

## 11. Cross-doc impact

- `STANDARDS.md` § 2: the four new modules in the dependency flow; the two
  workers in the threading table. § 7: the `updates` section in the schema;
  *Skip this version* and the update exit in the save list. § 9: a
  `test_updater.py` row. § 10: `ALLOWED_RELEASE_HOSTS` beside
  `ALLOWED_IMAGE_DOMAINS`, and that the gate sentence now names both; the
  updater's `subprocess` use with its own paths only, under *No code
  execution*.
- `SECURITY.md` § What is in scope: the release allowlist, and that
  installing a file whose signature does not verify is a finding.
- `README.md`: a short *Updates* paragraph — off by default, where to turn
  it on, Mac notify-only.
- `CLAUDE.md` § Architecture: unchanged; the new files sit in existing
  folders.
- `CHANGELOG.md`: an entry.
- SLIP-0104, SLIP-0106, SLIP-0107: `invariant_check` matched them on
  `core/config.py` and `ui/workers.py`. This spec adds keys and workers and
  changes none of their clauses.

## 12. Cold-eyes loop log

Rows live in `../reviews/SLIP-0031-auto-update-loop-log.md`.

## 13. Resource cost

- **Memory:** one copy of the downloaded file while it is verified;
  `Ed25519PublicKey.verify` takes the whole message. Released before
  `apply`. Bounded by `MAX_UPDATE_BYTES`.
- **Disk:** up to two copies of the new file beside the target while
  verifying, then one. Leftovers are removed on the next start (§ 4.10).
- **Network:** one small API call per launch, only when turned on.
- **Dependencies:** none beyond SLIP-0030's `cryptography`.

## 14. Migration / compatibility

- Old settings files gain `updates` with its defaults on load (§ 4.2).
- **The update path is itself a compatibility surface.** Every copy of
  release N and later reads `releases/latest`, the asset names in SLIP-0030
  § 4.1 and the `.sig` format. Renaming an asset or changing the signature
  format silently stops those copies being offered updates.

## 15. Open questions

- **Q1 — Bind the version, not only the bytes?** A per-file signature lets
  a compromised host serve an older genuine release as the newest (§ 6).
  finbreak closed this with a signed `SHA256SUMS` naming each file with its
  version (FIBR-0169). Slipcase's file names carry no version, and each is
  built in a separate job. Decided (2026-10-29, user): accept the risk for
  now — the worst case is a genuine older Slipcase — and queue the
  manifest as a follow-up.
- **Q2 — How is the full update tested before users rely on it?**
  `releases/latest` skips prereleases, so a test release is a real public
  release. Decided (2026-10-29, user): ship the updater in release N, and treat N → N+1
  as § 7.1's run, announcing the feature only after it passes. Adding a
  hidden setting to point the check elsewhere would widen what the
  allowlist trusts.
- **Q3 — Add Help → Check for updates?** It would let a user with the
  setting off ask once, and is the only way a Mac user can check on demand.
  Decided (2026-10-29, user): defer; it is one menu item later and not in
  the roadmap's shape.
- **Q4 — The offline backup of the signing key.** SLIP-0030 § 14 Q1.

## 16. Departures from finbreak

| finbreak | Here | Why |
|---|---|---|
| Signs on the maintainer's machine | Signs in CI (SLIP-0030) | User, 2026-10-29 |
| `urllib` with a bundled `certifi` context | `requests`, as `api/` already uses | One HTTP stack; `requests` already verifies against `certifi`, which is in `requirements.lock` |
| Settings in a plaintext INI, read before the vault unlocks | `config.json` keys | Slipcase has no vault |
| A key-wipe callback before relaunch | `shutdown_for_update`: save, clear, release lock | Slipcase holds no key; it holds unsaved settings and the single-instance lock |
| Linux: wipe after replace, then spawn | Spawn the waiter, then shut down | A spawn failure then leaves a running, saved app rather than a shut-down one |
| Assets matched by suffix with a version in the name | Matched by exact name | Slipcase's asset names carry no version |
| Signed `SHA256SUMS` manifest | Not ported | § 15 Q1 |
| Release notes in the prompt | Not ported | § 9 |
| A historical signed fixture against the real key | Not ported yet | SLIP-0030 § 9 |
| A Help-menu check | Not ported | § 15 Q3 |
| Inert on macOS | Notify-only on macOS | User, 2026-10-29 |
