"""Whether a newer release exists, and fetching it safely (SLIP-0031).

check_for_update() turns GitHub's newest release into an offer, or into
nothing: every failure is silent, because a check the user did not ask for
right now must never interrupt them. download_and_verify() stages the new
file beside the running copy and proves the maintainer signed it before
anything is installed. The network itself is api/releases.py's alone.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from cryptography.exceptions import InvalidSignature

from api import releases
from core import update_key
from core.config import Config
from core.version import __version__

if TYPE_CHECKING:
    from core.update_installer import Installer, UpdateMode

_log = logging.getLogger(__name__)

STAGED_PREFIX = "slipcase-update-"
SIGNATURE_BYTES = 64
# A staged file this old belongs to no download still running.
STALE_SECONDS = 60 * 60

VERIFY_FAILED = "The download could not be verified, so nothing was installed."


class UpdateError(Exception):
    """An update could not be fetched, staged or installed."""


class UpdateDownloadError(UpdateError):
    """The release host could not deliver the file."""


class UpdateVerificationError(UpdateError):
    """The download's signature did not verify."""


@dataclass(frozen=True)
class UpdateOffer:
    version: str            # tag without its leading "v"
    tag: str                # the tag as published
    asset_url: str | None   # None in notify-only mode
    sig_url: str | None


def parse_version(text: str) -> tuple[int, ...] | None:
    """A release tag's numbers, or None when it is not plain dotted digits.

    One leading v or V is dropped. Each part must be ASCII digits: int()
    alone accepts "1_4" and Arabic-Indic digits, which no tag here uses.
    """
    if text[:1] in ("v", "V"):
        text = text[1:]
    parts = text.split(".")
    if not all(p.isascii() and p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def _is_newer(candidate: tuple[int, ...], current: tuple[int, ...]) -> bool:
    width = max(len(candidate), len(current))
    pad = (0,) * width
    return (candidate + pad)[:width] > (current + pad)[:width]


def check_for_update(config: Config, mode: UpdateMode | None, *,
                     fetch=releases.fetch_latest_release,
                     current: str = __version__) -> UpdateOffer | None:
    """The offer to make, or None. Calls `fetch` only when the user opted in.

    On means exactly True: any other stored value reads as off (INV-1).
    """
    if mode is None or config.get("updates", "check") is not True:
        return None
    try:
        return _offer(fetch(), mode, current, config.get("updates", "skipped_version"))
    except Exception as e:
        _log.debug("update check failed: %s", e)
        return None


def _offer(release: object, mode: UpdateMode, current: str,
           skipped: object) -> UpdateOffer | None:
    if not isinstance(release, dict):
        return None
    tag = release.get("tag_name")
    if not isinstance(tag, str):
        return None
    newest, running = parse_version(tag), parse_version(current)
    if newest is None or running is None or not _is_newer(newest, running):
        return None
    version = tag[1:] if tag[:1] in ("v", "V") else tag
    if version == skipped:
        return None
    if mode.installer is None:
        return UpdateOffer(version, tag, None, None)
    name = mode.installer.asset_name()
    asset_url = _asset_url(release, name)
    sig_url = _asset_url(release, name + ".sig")
    if asset_url is None or sig_url is None:
        return None
    return UpdateOffer(version, tag, asset_url, sig_url)


def _asset_url(release: dict, name: str) -> str | None:
    """The download URL of the one asset called exactly `name`, or None."""
    assets = release.get("assets")
    if not isinstance(assets, list):
        return None
    matches = [a for a in assets if isinstance(a, dict) and a.get("name") == name]
    if len(matches) != 1:
        return None
    url = matches[0].get("browser_download_url")
    if not isinstance(url, str) or not releases.is_allowed_release_url(url):
        return None
    return url


def _extension(installer: Installer) -> str:
    return Path(installer.asset_name()).suffix


def download_and_verify(offer: UpdateOffer, installer: Installer, *,
                        download=releases.download,
                        on_progress: Callable[[int, int], None] | None = None,
                        should_stop: Callable[[], bool] | None = None) -> Path:
    """Download the offer's file and signature, verify, and return the file.

    The file returned is a fresh copy of the verified bytes, not the
    download temp, so what is installed is exactly what was checked.
    Every temp sits beside the target, keeping the swap a same-filesystem
    move, and every one is deleted on failure.
    """
    from core.update_installer import AppImageInstaller

    folder = installer.target_path().parent
    ext = _extension(installer)
    staged: list[Path] = []

    def stage(suffix: str) -> tuple[int, Path]:
        fd, name = tempfile.mkstemp(prefix=STAGED_PREFIX, suffix=suffix, dir=folder)
        staged.append(Path(name))
        return fd, Path(name)

    try:
        fd, asset_tmp = stage(ext)
        os.close(fd)
        fd, sig_tmp = stage(ext + ".sig")
        os.close(fd)
        try:
            download(offer.asset_url, asset_tmp, max_bytes=releases.MAX_UPDATE_BYTES,
                     on_progress=on_progress, should_stop=should_stop)
            download(offer.sig_url, sig_tmp, max_bytes=releases.MAX_SIGNATURE_BYTES,
                     should_stop=should_stop)
        except releases.ReleaseError as e:
            raise UpdateDownloadError(f"The update could not be downloaded: {e}") from None
        signature = sig_tmp.read_bytes()
        if len(signature) != SIGNATURE_BYTES:
            _log.debug("signature is %d bytes, not %d", len(signature), SIGNATURE_BYTES)
            raise UpdateVerificationError(VERIFY_FAILED)
        data = asset_tmp.read_bytes()
        try:
            update_key.public_key().verify(signature, data)
        except InvalidSignature:
            raise UpdateVerificationError(VERIFY_FAILED) from None
        fd, verified = stage(ext)
        with os.fdopen(fd, "wb") as out:
            out.write(data)
        del data
        if isinstance(installer, AppImageInstaller) and os.name == "posix":
            verified.chmod(0o755)
        for path in (asset_tmp, sig_tmp):
            path.unlink()
            staged.remove(path)
        return verified
    except UpdateError:
        _remove(staged)
        raise
    except OSError as e:
        _remove(staged)
        raise UpdateError(f"The update could not be saved beside Slipcase: {e}") from None
    except BaseException:
        _remove(staged)
        raise


def _remove(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError as e:
            _log.debug("could not delete %s: %s", path, e)


def remove_stale_staged_updates(installer: Installer) -> None:
    """Delete update files an interrupted run left beside the target.

    Only names that fully match what download_and_verify stages, older than
    STALE_SECONDS, and never the target itself. Errors are logged and ignored.
    """
    target = installer.target_path()
    pattern = re.compile(re.escape(STAGED_PREFIX) + r"[a-z0-9_]{8}"
                         + re.escape(_extension(installer)) + r"(\.sig)?")
    cutoff = time.time() - STALE_SECONDS
    try:
        entries = list(os.scandir(target.parent))
    except OSError as e:
        _log.debug("cannot list %s: %s", target.parent, e)
        return
    for entry in entries:
        try:
            if (pattern.fullmatch(entry.name) and entry.name != target.name
                    and entry.is_file(follow_symlinks=False)
                    and entry.stat(follow_symlinks=False).st_mtime < cutoff):
                os.unlink(entry.path)
        except OSError as e:
            _log.debug("cannot remove %s: %s", entry.path, e)
