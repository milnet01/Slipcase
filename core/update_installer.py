"""Replacing the running copy with a verified update (SLIP-0031 § 4.7).

Which kind of copy is running decides what an update may do:
detect_update_mode() returns None (inert: a source run, or a frozen build
outside an AppImage), UpdateMode(None) (notify only: macOS, or a target
folder this user cannot write), or UpdateMode with the installer for the
Linux AppImage or the Windows exe.

An installer's apply() either does not return, or raises UpdateError with
the running copy untouched and `before_exit` uncalled -- except where Linux
has already replaced the file, which its message says.
"""

import logging
import ntpath
import os
import secrets
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, Protocol

from core.config import config_dir
from core.updater import UpdateError, UpdateInstalledError

_log = logging.getLogger(__name__)

APPIMAGE_ASSET = "Slipcase-x86_64.AppImage"
WINDOWS_ASSET = "Slipcase-windows-x64.exe"

# How long the relaunch helper waits for this copy to exit, in seconds.
_WAIT_SECONDS = 60

# Waits for this process to exit, then starts the new copy. The target path
# arrives as $1 and is never spliced into the text, so no file name can
# become shell code; the pid is an int formatted in.
_SH_WAITER = (
    'pid={pid}; i=0; '
    'while kill -0 "$pid" 2>/dev/null && [ "$i" -lt {ticks} ]; do sleep 0.2; i=$((i+1)); done; '
    'exec "$1"'
)

# Waits until no process runs from the exe's path -- by path, not pid,
# because a one-file build runs as two processes with the same image --
# then swaps in the new file, retrying for an antivirus lock, and starts
# the exe whether or not the swap succeeded. Still busy at the cap: delete
# the new file and start nothing.
_PS_HELPER = (
    "$exe = {exe}; $new = {new}; "
    "$deadline = (Get-Date).AddSeconds({wait}); "
    "while (Get-Process -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -eq $exe }}) {{ "
    "if ((Get-Date) -gt $deadline) {{ "
    "Remove-Item -LiteralPath $new -Force -ErrorAction SilentlyContinue; exit 1 }}; "
    "Start-Sleep -Milliseconds 250 }}; "
    "$moved = $false; "
    "for ($i = 0; ($i -lt 10) -and (-not $moved); $i++) {{ "
    "try {{ Move-Item -LiteralPath $new -Destination $exe -Force -ErrorAction Stop; "
    "$moved = $true }} catch {{ Start-Sleep -Milliseconds 500 }} }}; "
    "if (-not $moved) {{ Remove-Item -LiteralPath $new -Force -ErrorAction SilentlyContinue }}; "
    "Start-Process -FilePath $exe"
)

# PowerShell ends a single-quoted string at any of these, not only at '.
_PS_QUOTES = ("'", "‘", "’", "‚", "‛")


class Installer(Protocol):
    def asset_name(self) -> str: ...
    def target_path(self) -> Path: ...
    def can_self_update(self) -> bool: ...
    def apply(self, new_file: Path, before_exit: Callable[[], None]) -> NoReturn: ...


@dataclass(frozen=True)
class UpdateMode:
    installer: Installer | None   # None means notify-only


class _FileInstaller:
    """What both installers share: a target file and the write probe."""

    asset: str = ""

    def __init__(self, target: Path) -> None:
        self._target = Path(target)

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and other._target == self._target

    def __hash__(self) -> int:
        return hash((type(self), self._target))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({str(self._target)!r})"

    def asset_name(self) -> str:
        return self.asset

    def target_path(self) -> Path:
        return self._target

    def can_self_update(self) -> bool:
        """Whether this user can create files beside the target."""
        probe = self._target.parent / f"slipcase-update-probe-{secrets.token_hex(4)}"
        try:
            fd = os.open(probe, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            os.unlink(probe)
        except OSError as e:
            _log.debug("cannot write beside %s: %s", self._target, e)
            return False
        return True


def _exit_after(before_exit: Callable[[], None]) -> NoReturn:
    """Run the app's shutdown, then leave without running Qt's teardown.

    os._exit even when before_exit fails: the helper is already waiting for
    this process, and a copy left running would only block the new one.
    """
    try:
        before_exit()
    finally:
        os._exit(0)


class AppImageInstaller(_FileInstaller):
    """Replaces the AppImage in place; a waiter starts the new one."""

    asset = APPIMAGE_ASSET

    def apply(self, new_file: Path, before_exit: Callable[[], None]) -> NoReturn:
        target = self._target
        # Safe while running: the old AppImage stays mounted from its inode.
        try:
            os.replace(new_file, target)
        except OSError as e:
            Path(new_file).unlink(missing_ok=True)
            raise UpdateError(f"Slipcase could not replace {target.name}: {e}") from None

        env = dict(os.environ)
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        for name in ("APPDIR", "APPIMAGE", "ARGV0"):
            env.pop(name, None)
        original = env.pop("LD_LIBRARY_PATH_ORIG", None)
        if original is not None:
            env["LD_LIBRARY_PATH"] = original
        else:
            env.pop("LD_LIBRARY_PATH", None)

        script = _SH_WAITER.format(pid=os.getpid(), ticks=_WAIT_SECONDS * 5)
        log = None
        try:
            try:
                folder = config_dir()
                folder.mkdir(parents=True, exist_ok=True)
                # Closed below, once the waiter holds its own copy.
                log = open(folder / "update-relaunch.log", "ab")
            except OSError as e:
                _log.debug("no relaunch log: %s", e)
            out = log if log is not None else subprocess.DEVNULL
            subprocess.Popen(  # noqa: S603 -- fixed argv; the path is an argument, not code
                ["/bin/sh", "-c", script, "sh", str(target)],
                env=env, start_new_session=True, close_fds=True,
                stdin=subprocess.DEVNULL, stdout=out, stderr=out,
            )
        except OSError as e:
            _log.debug("relaunch failed: %s", e)
            raise UpdateInstalledError(
                "Slipcase was updated. Close it and open it again.") from None
        finally:
            if log is not None:
                log.close()
        _exit_after(before_exit)


def _ps_quote(text: str) -> str:
    """`text` as a PowerShell single-quoted string."""
    for quote in _PS_QUOTES:
        text = text.replace(quote, quote * 2)
    return f"'{text}'"


class WindowsInstaller(_FileInstaller):
    """Hands the swap to a PowerShell helper that runs after the app exits.

    The running exe is locked, so it cannot be replaced from inside.
    """

    asset = WINDOWS_ASSET

    def apply(self, new_file: Path, before_exit: Callable[[], None]) -> NoReturn:
        root = os.environ.get("SystemRoot", "")
        powershell = (ntpath.join(root, "System32", "WindowsPowerShell", "v1.0",
                                  "powershell.exe")
                      if root else "powershell.exe")
        script = _PS_HELPER.format(exe=_ps_quote(str(self._target)),
                                   new=_ps_quote(str(new_file)), wait=_WAIT_SECONDS)
        # Never DETACHED_PROCESS: PowerShell started with it dies before
        # running a line (finbreak FIBR-0444). getattr, so this loads on Linux.
        flags = (getattr(subprocess, "CREATE_NO_WINDOW", 0)
                 | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        env = dict(os.environ)
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        try:
            subprocess.Popen(  # noqa: S603 -- fixed argv; both paths are quoted data
                [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
                env=env, creationflags=flags, close_fds=True,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as e:
            Path(new_file).unlink(missing_ok=True)
            raise UpdateError(f"Slipcase could not start its updater: {e}") from None
        _exit_after(before_exit)


def detect_update_mode() -> UpdateMode | None:
    """What an update may do in the copy that is running (SLIP-0031 § 4.3)."""
    if not getattr(sys, "frozen", False):
        return None
    installer: Installer
    if sys.platform == "win32":
        installer = WindowsInstaller(Path(sys.executable))
    elif sys.platform == "darwin":
        return UpdateMode(None)
    else:
        appimage = os.environ.get("APPIMAGE", "")
        appdir = os.environ.get("APPDIR", "")
        if not (appimage and appdir and os.path.isfile(appimage)):
            return None
        # $APPIMAGE is inherited: a copy started from inside another
        # AppImage would otherwise overwrite that other app's file.
        if not Path(sys.executable).resolve().is_relative_to(Path(appdir).resolve()):
            return None
        installer = AppImageInstaller(Path(appimage))
    if not installer.can_self_update():
        return UpdateMode(None)
    return UpdateMode(installer)
