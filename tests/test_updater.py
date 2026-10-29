"""Tests for the in-app updater (SLIP-0031, docs/specs/SLIP-0031-auto-update.md).

None touches the network: every fetch and download is a fake, and every
signature is made with a throwaway key patched over RELEASE_PUBLIC_KEY_B64.
Platform behaviour is reached by patching sys.platform, sys.frozen,
subprocess.Popen, os.replace and os._exit, never by running there. So these
check the commands and their order; the real shell wait, PowerShell swap and
AppImage runtime are the spec's manual recipe (§ 7.1).
"""

import ast
import base64
import ntpath
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat  # noqa: E402

from api import releases  # noqa: E402
from core import update_key  # noqa: E402
from core.config import Config  # noqa: E402
from core.update_installer import (  # noqa: E402
    AppImageInstaller,
    UpdateMode,
    WindowsInstaller,
    detect_update_mode,
)
from core.updater import (  # noqa: E402
    UpdateDownloadError,
    UpdateError,
    UpdateOffer,
    UpdateVerificationError,
    check_for_update,
    download_and_verify,
    remove_stale_staged_updates,
)

APPIMAGE = "Slipcase-x86_64.AppImage"
EXE = "Slipcase-windows-x64.exe"
DOWNLOADS = "https://github.com/milnet01/Slipcase/releases/download/"


def _release(tag="v1.4.0", names=(APPIMAGE, APPIMAGE + ".sig"), base=DOWNLOADS):
    """A releases/latest reply. html_url is hostile: nothing may open it."""
    return {
        "tag_name": tag,
        "html_url": "https://evil.example/",
        "assets": [{"name": n, "browser_download_url": f"{base}{tag}/{n}"} for n in names],
    }


class _FakeInstaller:
    """An Installer whose apply() only records the call."""

    def __init__(self, folder, name=APPIMAGE, error=None):
        self.target = Path(folder) / name
        self.applied = []
        self.error = error

    def asset_name(self):
        return self.target.name

    def target_path(self):
        return self.target

    def can_self_update(self):
        return True

    def apply(self, new_file, before_exit):
        self.applied.append(new_file)
        if self.error is not None:
            raise self.error


class _FakeDownload:
    """Stands in for releases.download: writes the bytes mapped to each URL."""

    def __init__(self, bodies):
        self.bodies = bodies
        self.calls = []

    def __call__(self, url, dest, *, max_bytes, on_progress=None, should_stop=None):
        self.calls.append((url, Path(dest), max_bytes))
        body = self.bodies[url]
        if isinstance(body, Exception):
            Path(dest).unlink(missing_ok=True)
            raise body
        Path(dest).write_bytes(body)
        if on_progress is not None:
            on_progress(len(body), len(body))


def _config(folder, **updates):
    config = Config(Path(folder) / "config.json")
    for key, value in updates.items():
        config.set("updates", key, value)
    return config


def _throwaway_key():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return private, base64.b64encode(public).decode()


_APP = []


def _app():
    """The one QApplication, kept referenced: a dropped one aborts the run.

    QApplication, not QCoreApplication, as tests/test_single_instance.py
    explains."""
    from PyQt6.QtWidgets import QApplication
    if not _APP:
        _APP.append(QApplication.instance() or QApplication([]))
    return _APP[0]


def _settle(seconds=0.2):
    """Let queued signals and timers run."""
    from PyQt6.QtCore import QCoreApplication
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


class _TempDir(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.dir = Path(self._dir.name)

    def tearDown(self):
        self._dir.cleanup()


class TestCheck(_TempDir):
    """INV-1, INV-3, INV-4."""

    def _mode(self):
        return UpdateMode(_FakeInstaller(self.dir))

    def test_opt_in(self):
        for label, kwargs in (("fresh", {}), ("False", {"check": False}),
                              ("'true'", {"check": "true"}), ("1", {"check": 1})):
            fetch = MagicMock(return_value=_release())
            offer = check_for_update(_config(self.dir, **kwargs), self._mode(),
                                     fetch=fetch, current="1.3.1")
            self.assertIsNone(offer, label)
            fetch.assert_not_called()
        fetch = MagicMock(return_value=_release())
        offer = check_for_update(_config(self.dir, check=True), self._mode(),
                                 fetch=fetch, current="1.3.1")
        fetch.assert_called_once()
        self.assertEqual(offer.version, "1.4.0")

    def test_default_is_off(self):
        self.assertIs(Config(self.dir / "absent.json").get("updates", "check"), False)
        self.assertEqual(Config(self.dir / "absent.json").get("updates", "skipped_version"), "")

    def _offer(self, release, mode=None, **updates):
        return check_for_update(_config(self.dir, check=True, **updates),
                                mode or self._mode(),
                                fetch=lambda: release, current="1.3.1")

    def test_offer_rules(self):
        offer = self._offer(_release("v1.4.0"))
        self.assertEqual(offer, UpdateOffer(
            version="1.4.0", tag="v1.4.0",
            asset_url=f"{DOWNLOADS}v1.4.0/{APPIMAGE}",
            sig_url=f"{DOWNLOADS}v1.4.0/{APPIMAGE}.sig"))
        for tag in ("v1.3.1", "v1.3.0", "v1.3.1.0", "v1.4-rc1", "latest", "v1_4.0",
                    "v\u0661.\u0664.\u0660", "", "v", "v1..4", "vv1.4.0"):
            self.assertIsNone(self._offer(_release(tag)), repr(tag))
        self.assertEqual(self._offer(_release("V1.4.0")).version, "1.4.0")
        self.assertEqual(self._offer(_release("1.4.0")).version, "1.4.0")

        self.assertIsNone(self._offer(_release(names=(APPIMAGE,))), "no .sig")
        self.assertIsNone(self._offer(_release(names=(APPIMAGE + ".sig",))), "no asset")
        self.assertIsNone(self._offer(_release(names=(APPIMAGE, APPIMAGE, APPIMAGE + ".sig"))),
                          "two assets of the name")
        self.assertIsNone(self._offer(_release(base="http://github.com/x/")), "http URL")
        self.assertIsNone(self._offer(_release(base="https://evil.example/")), "other host")
        old = "Old-" + APPIMAGE
        self.assertIsNone(self._offer(_release(names=(old, old + ".sig"))), "suffix match")

        self.assertIsNone(self._offer(_release("v1.4.0"), skipped_version="1.4.0"))
        self.assertIsNotNone(self._offer(_release("v1.4.1"), skipped_version="1.4.0"))

    def test_notify_mode_needs_only_the_tag(self):
        offer = self._offer({"tag_name": "v1.4.0"}, mode=UpdateMode(None))
        self.assertEqual(offer, UpdateOffer("1.4.0", "v1.4.0", None, None))

    def test_failures_are_silent(self):
        for label, fetch in (
            ("ConnectionError", MagicMock(side_effect=requests.ConnectionError("down"))),
            ("ValueError", MagicMock(side_effect=ValueError("bad json"))),
            ("ReleaseError", MagicMock(side_effect=releases.ReleaseError("404"))),
            ("list", MagicMock(return_value=[])),
            ("no tag_name", MagicMock(return_value={"name": "v1.4.0"})),
            ("tag not a string", MagicMock(return_value={"tag_name": 140})),
            ("assets not a list", MagicMock(return_value={"tag_name": "v1.4.0", "assets": 3})),
        ):
            offer = check_for_update(_config(self.dir, check=True), self._mode(),
                                     fetch=fetch, current="1.3.1")
            self.assertIsNone(offer, label)


class TestMode(_TempDir):
    """INV-2, INV-11, INV-16."""

    def _appimage_env(self):
        appimage = self.dir / APPIMAGE
        appimage.write_bytes(b"old")
        appdir = self.dir / "mount"
        (appdir / "usr" / "bin").mkdir(parents=True)
        return appimage, appdir

    def test_source_run_is_inert(self):
        self.assertFalse(hasattr(sys, "frozen"), "the test run is not frozen")
        # Not frozen means inert on every platform, even inside an AppImage.
        appimage, appdir = self._appimage_env()
        with patch.dict(os.environ, {"APPIMAGE": str(appimage), "APPDIR": str(appdir)}), \
                patch.object(sys, "executable", str(appdir / "usr" / "bin" / "python3")):
            for platform in ("linux", "win32", "darwin"):
                with patch.object(sys, "platform", platform):
                    self.assertIsNone(detect_update_mode(), platform)

        _app()
        from ui.main_window import MainWindow
        config = _config(self.dir, check=True)
        with patch("ui.main_window.UpdateCheckWorker") as worker:
            window = MainWindow(config)
            window.show()
            _settle()
            window.close()
            _settle(0.05)
        worker.assert_not_called()

    def test_macos_notify(self):
        with patch.object(sys, "frozen", True, create=True), \
                patch.object(sys, "platform", "darwin"):
            self.assertEqual(detect_update_mode(), UpdateMode(None))

    def test_windows_installs(self):
        exe = self.dir / EXE
        exe.write_bytes(b"old")
        with patch.object(sys, "frozen", True, create=True), \
                patch.object(sys, "platform", "win32"), \
                patch.object(sys, "executable", str(exe)):
            mode = detect_update_mode()
        self.assertIsInstance(mode.installer, WindowsInstaller)
        self.assertEqual(mode.installer.target_path(), exe)

    def test_inherited_appimage(self):
        appimage, appdir = self._appimage_env()
        env = {"APPIMAGE": str(appimage), "APPDIR": str(appdir)}
        with patch.object(sys, "frozen", True, create=True), \
                patch.object(sys, "platform", "linux"), \
                patch.dict(os.environ, env):
            with patch.object(sys, "executable", str(self.dir / "elsewhere" / "slipcase")):
                self.assertIsNone(detect_update_mode())
            with patch.object(sys, "executable", str(appdir / "usr" / "bin" / "slipcase")):
                mode = detect_update_mode()
            self.assertIsInstance(mode.installer, AppImageInstaller)
            self.assertEqual(mode.installer.target_path(), appimage)
            # A frozen Linux build with no AppImage around it.
            with patch.dict(os.environ, {"APPIMAGE": ""}), \
                    patch.object(sys, "executable", str(appdir / "usr" / "bin" / "slipcase")):
                self.assertIsNone(detect_update_mode())
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), [APPIMAGE, "mount"],
                         "the write probe was left behind")

    def test_unwritable_target(self):
        appimage, appdir = self._appimage_env()
        env = {"APPIMAGE": str(appimage), "APPDIR": str(appdir)}
        with patch.object(sys, "frozen", True, create=True), \
                patch.object(sys, "platform", "linux"), \
                patch.dict(os.environ, env), \
                patch.object(sys, "executable", str(appdir / "usr" / "bin" / "slipcase")), \
                patch("core.update_installer.os.open", side_effect=PermissionError("ro")):
            self.assertEqual(detect_update_mode(), UpdateMode(None))


class TestSettings(_TempDir):
    """INV-2: the Updates tab."""

    def test_checkbox_disabled(self):
        _app()
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(_config(self.dir))
        self.assertFalse(dialog.update_check.isEnabled())
        self.assertEqual(dialog.update_check.toolTip(),
                         "Only the downloaded app can check for updates.")
        dialog.deleteLater()

    def test_checkbox_saves_when_available(self):
        _app()
        from ui.settings_dialog import SettingsDialog
        config = _config(self.dir)
        with patch("ui.settings_dialog.detect_update_mode", return_value=UpdateMode(None)):
            dialog = SettingsDialog(config)
        self.assertTrue(dialog.update_check.isEnabled())
        self.assertFalse(dialog.update_check.isChecked())
        dialog.update_check.setChecked(True)
        dialog._save_and_accept()
        self.assertIs(Config(self.dir / "config.json").get("updates", "check"), True)
        dialog.deleteLater()


def _response(*, redirect_to=None, headers=None, body=None, status_error=None):
    response = MagicMock(is_redirect=redirect_to is not None, is_permanent_redirect=False)
    response.headers = dict(headers or {})
    if redirect_to is not None:
        response.headers["Location"] = redirect_to
    if status_error is not None:
        response.raise_for_status.side_effect = status_error
    else:
        response.raise_for_status.return_value = None
    if body is not None:
        response.raw.read1.side_effect = [*body, b""]
    return response


class TestNetwork(_TempDir):
    """INV-5 and INV-6: api/releases.py."""

    def _session(self, *responses):
        session = MagicMock()
        session.get.side_effect = list(responses)
        return session

    def test_exact_hosts(self):
        for url in ("https://api.github.com/repos/milnet01/Slipcase/releases/latest",
                    "https://github.com/milnet01/Slipcase/releases/download/v1.4.0/x",
                    "https://release-assets.githubusercontent.com/abc"):
            self.assertTrue(releases.is_allowed_release_url(url), url)
        for url in ("https://evil.github.com/x", "https://raw.githubusercontent.com/x",
                    "http://github.com/x", "https://github.com.evil.com/x",
                    "https://github.com@evil.com/x", "https://githubusercontent.com/x",
                    "https://screenscraper.fr/x", "file:///etc/passwd", "not a url",
                    "https://github.com:8443/x"):
            self.assertFalse(releases.is_allowed_release_url(url), url)
        self.assertEqual(releases.ALLOWED_RELEASE_HOSTS, frozenset({
            "api.github.com", "github.com", "release-assets.githubusercontent.com"}))

    def test_redirect_hops_rechecked(self):
        for location in ("https://example.com/", "http://github.com/"):
            session = self._session(_response(redirect_to=location), _response(body=[b"{}"]))
            with patch("api.releases.requests.Session", return_value=session):
                with self.assertRaises(releases.ReleaseError, msg=location):
                    releases.fetch_latest_release()
            self.assertEqual(session.get.call_count, 1, location)
            self.assertIs(session.get.call_args.kwargs["allow_redirects"], False)
            self.assertIs(session.get.call_args.kwargs["verify"], True)
            session.close.assert_called_once()

            dest = self.dir / "dl"
            dest.write_bytes(b"")
            session = self._session(_response(redirect_to=location), _response(body=[b"x"]))
            with patch("api.releases.requests.Session", return_value=session):
                with self.assertRaises(releases.ReleaseError, msg=location):
                    releases.download(f"{DOWNLOADS}v1.4.0/{APPIMAGE}", dest, max_bytes=10)
            self.assertEqual(session.get.call_count, 1, location)
            self.assertFalse(dest.exists())
            session.close.assert_called_once()

    def test_allowed_redirect_is_followed(self):
        session = self._session(
            _response(redirect_to="https://release-assets.githubusercontent.com/a"),
            _response(headers={"Content-Length": "3"}, body=[b"abc"]))
        dest = self.dir / "dl"
        with patch("api.releases.requests.Session", return_value=session):
            releases.download(f"{DOWNLOADS}v1.4.0/{APPIMAGE}", dest, max_bytes=10)
        self.assertEqual(dest.read_bytes(), b"abc")
        self.assertEqual(session.get.call_args.args[0],
                         "https://release-assets.githubusercontent.com/a")

    def test_fetch_reads_json(self):
        session = self._session(_response(body=[b'{"tag_name": ', b'"v1.4.0"}']))
        with patch("api.releases.requests.Session", return_value=session):
            self.assertEqual(releases.fetch_latest_release(), {"tag_name": "v1.4.0"})
        self.assertEqual(session.get.call_args.args[0], releases.LATEST_RELEASE_URL)
        for body in ([b"not json"], [b"[]"]):
            session = self._session(_response(body=body))
            with patch("api.releases.requests.Session", return_value=session):
                with self.assertRaises(releases.ReleaseError):
                    releases.fetch_latest_release()

    def test_network_imports_confined(self):
        banned = {"requests", "urllib.request", "http.client", "socket"}
        found = []
        for folder, dirs, files in os.walk(ROOT):
            rel = Path(folder).relative_to(ROOT)
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                       ("tests", "build", "dist", "venv", "__pycache__")]
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = Path(folder) / name
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        modules = [a.name for a in node.names]
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        modules = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
                    else:
                        continue
                    for module in modules:
                        if any(module == b or module.startswith(b + ".") for b in banned):
                            found.append((rel / name).as_posix())
        self.assertTrue(found, "the scan found no network import at all; it has gone stale")
        self.assertEqual(sorted({p for p in found if not p.startswith("api/")}), [])

    def test_caps(self):
        self.assertEqual(releases.MAX_UPDATE_BYTES, 512 * 1024 * 1024)
        self.assertEqual(releases.MAX_SIGNATURE_BYTES, 64)
        self.assertEqual(releases.MAX_RELEASE_REPLY_BYTES, 1024 * 1024)
        self.assertEqual(releases.MAX_UPDATE_SECONDS, 30 * 60)
        url = f"{DOWNLOADS}v1.4.0/{APPIMAGE}"
        cases = {
            "Content-Length over the cap": _response(headers={"Content-Length": "11"},
                                                     body=[b"x" * 11]),
            "stream over the cap": _response(body=[b"x" * 6, b"x" * 6]),
            "short body": _response(headers={"Content-Length": "10"}, body=[b"x" * 5]),
            "HTTP error": _response(status_error=requests.HTTPError("404"), body=[b"x"]),
        }
        for label, response in cases.items():
            dest = self.dir / "dl"
            dest.write_bytes(b"")
            with patch("api.releases.requests.Session", return_value=self._session(response)):
                with self.assertRaises(releases.ReleaseError, msg=label):
                    releases.download(url, dest, max_bytes=10)
            self.assertFalse(dest.exists(), label)
        response = cases["Content-Length over the cap"]
        response.raw.read1.assert_not_called()

        dest = self.dir / "dl"
        with patch("api.releases.requests.Session",
                   return_value=self._session(_response(body=[b"x", b"x"]))):
            with self.assertRaises(releases.ReleaseError):
                releases.download(url, dest, max_bytes=10, should_stop=lambda: True)
        self.assertFalse(dest.exists(), "stopped")

        with patch("api.releases.requests.Session",
                   return_value=self._session(_response(body=[b"x", b"x"]))), \
                patch("api.releases.time.monotonic",
                      side_effect=[0.0, releases.MAX_UPDATE_SECONDS + 1.0, 1e9, 1e9]):
            with self.assertRaises(releases.ReleaseError):
                releases.download(url, dest, max_bytes=10)
        self.assertFalse(dest.exists(), "too slow")

        progress = []
        with patch("api.releases.requests.Session", return_value=self._session(
                _response(headers={"Content-Length": "10"}, body=[b"x" * 4, b"x" * 6]))):
            releases.download(url, dest, max_bytes=10,
                              on_progress=lambda got, total: progress.append((got, total)))
        self.assertEqual(dest.read_bytes(), b"x" * 10)
        self.assertEqual(progress, [(4, 10), (10, 10)])

        progress.clear()
        with patch("api.releases.requests.Session",
                   return_value=self._session(_response(body=[b"abc"]))):
            releases.download(url, dest, max_bytes=10,
                              on_progress=lambda got, total: progress.append((got, total)))
        self.assertEqual(progress, [(3, 0)])

        with patch("api.releases.requests.Session", return_value=self._session(
                _response(headers={"Content-Length": str(2 * 1024 * 1024)},
                          body=[b"{}"]))):
            with self.assertRaises(releases.ReleaseError):
                releases.fetch_latest_release()


class _Signed(_TempDir):
    """A throwaway key patched over the real one, and a signed blob."""

    def setUp(self):
        super().setUp()
        self.private, public = _throwaway_key()
        key = patch.object(update_key, "RELEASE_PUBLIC_KEY_B64", public)
        key.start()
        self.addCleanup(key.stop)
        self.blob = os.urandom(4096)
        self.sig = self.private.sign(self.blob)
        self.offer = UpdateOffer("1.4.0", "v1.4.0", f"{DOWNLOADS}v1.4.0/{APPIMAGE}",
                                 f"{DOWNLOADS}v1.4.0/{APPIMAGE}.sig")

    def _download(self, blob=None, sig=None):
        return _FakeDownload({self.offer.asset_url: self.blob if blob is None else blob,
                              self.offer.sig_url: self.sig if sig is None else sig})

    def _staged(self):
        return sorted(p.name for p in self.dir.glob("slipcase-update-*"))


class TestVerify(_Signed):
    """INV-6 and INV-7."""

    def setUp(self):
        super().setUp()
        self.target = self.dir / APPIMAGE
        self.target.write_bytes(b"old")
        self.installer = AppImageInstaller(self.target)

    def test_good_signature(self):
        download = self._download()
        path = download_and_verify(self.offer, self.installer, download=download)
        self.assertEqual(path.read_bytes(), self.blob)
        self.assertEqual(path.parent, self.dir)
        if os.name == "posix":
            self.assertEqual(path.stat().st_mode & 0o777, 0o755)
        self.assertNotIn(path, [dest for _, dest, _ in download.calls])
        self.assertEqual(self._staged(), [path.name])
        self.assertRegex(path.name, r"^slipcase-update-[a-z0-9_]{8}\.AppImage$")
        self.assertEqual([cap for _, _, cap in download.calls],
                         [releases.MAX_UPDATE_BYTES, releases.MAX_SIGNATURE_BYTES])
        self.assertEqual(self.target.read_bytes(), b"old")

    def test_tamper(self):
        bad_blob = bytes([self.blob[0] ^ 1]) + self.blob[1:]
        bad_sig = bytes([self.sig[0] ^ 1]) + self.sig[1:]
        for label, download in (("blob", self._download(blob=bad_blob)),
                                ("signature", self._download(sig=bad_sig))):
            with self.assertRaises(UpdateVerificationError, msg=label):
                download_and_verify(self.offer, self.installer, download=download)
            self.assertEqual(self._staged(), [], label)

    def test_signature_length(self):
        # Refused on its length, before the key is asked.
        for sig in (self.sig[:63], self.sig + b"\0", b""):
            with patch("core.updater.update_key.public_key") as key, \
                    self.assertRaises(UpdateVerificationError, msg=len(sig)):
                download_and_verify(self.offer, self.installer,
                                    download=self._download(sig=sig))
            key.assert_not_called()
            self.assertEqual(self._staged(), [])

    def test_failed_download(self):
        download = _FakeDownload({self.offer.asset_url: releases.ReleaseError("dropped"),
                                  self.offer.sig_url: self.sig})
        with self.assertRaises(UpdateDownloadError):
            download_and_verify(self.offer, self.installer, download=download)
        self.assertEqual(self._staged(), [])
        self.assertTrue(issubclass(UpdateDownloadError, UpdateError))
        self.assertTrue(issubclass(UpdateVerificationError, UpdateError))


class _WindowTest(_Signed):
    """A real MainWindow on a temporary settings file."""

    def setUp(self):
        super().setUp()
        _app()
        from ui.main_window import MainWindow
        self.config_path = self.dir / "config.json"
        self.window = MainWindow(Config(self.config_path))

    def tearDown(self):
        for attr in ("_render_worker", "_batch_worker", "_anim_worker"):
            if isinstance(getattr(self.window, attr), MagicMock):
                setattr(self.window, attr, None)
        self.window.close()
        _settle(0.05)
        super().tearDown()

    def _dialog(self, offer=None, installer=None, download=None, notify=False):
        from ui.update_dialog import UpdateDialog
        self.installer = None if notify else (installer or _FakeInstaller(self.dir))
        self.download = download or self._download()
        dialog = UpdateDialog(self.window, offer or self.offer, self.installer,
                              download=self.download)
        dialog.show()
        return dialog

    def _wait_download(self):
        worker = self.window._update_download_worker
        self.assertIsNotNone(worker, "no download started")
        self.assertTrue(worker.wait(5000))
        _settle()


class TestDialog(_WindowTest):
    """INV-7, INV-8, INV-11, INV-12, INV-13, INV-14."""

    def _offered(self, tag):
        config = Config(self.config_path)
        return check_for_update(config, UpdateMode(_FakeInstaller(self.dir)),
                                fetch=lambda: _release(tag), current="1.3.1")

    def test_skip_and_later(self):
        self.window.config.set("updates", "check", True)
        self.window._save_config()
        dialog = self._dialog()
        dialog.skip_button.click()
        self.assertFalse(dialog.isVisible())
        self.assertIsNone(self._offered("v1.4.0"))
        self.assertIsNotNone(self._offered("v1.4.1"))

        self.window.config.set("updates", "skipped_version", "")
        self.window._save_config()
        dialog = self._dialog()
        dialog.later_button.click()
        self.assertFalse(dialog.isVisible())
        self.assertEqual(self._offered("v1.4.0").version, "1.4.0")

    def test_update_installs_verified_file(self):
        dialog = self._dialog()
        dialog.update_button.click()
        self._wait_download()
        self.assertEqual(len(self.installer.applied), 1)
        self.assertEqual(self.installer.applied[0].read_bytes(), self.blob)

    def test_verify_failure_never_applies(self):
        bad_sig = bytes([self.sig[0] ^ 1]) + self.sig[1:]
        with patch("ui.update_dialog.QMessageBox") as box:
            dialog = self._dialog(download=self._download(sig=bad_sig))
            dialog.update_button.click()
            self._wait_download()
        self.assertEqual(self.installer.applied, [])
        box.warning.assert_called_once()
        self.assertIn("could not be verified, so nothing was installed",
                      box.warning.call_args.args[2])
        self.assertEqual(self._staged(), [])

    def test_open_release_page(self):
        config = _config(self.dir, check=True)
        offer = check_for_update(config, UpdateMode(None), fetch=lambda: _release("v1.4.0"),
                                 current="1.3.1")
        from PyQt6.QtCore import QUrl
        with patch("ui.update_dialog.QDesktopServices.openUrl") as open_url:
            dialog = self._dialog(offer=offer, notify=True)
            self.assertIsNone(dialog.update_button)
            dialog.release_page_button.click()
        open_url.assert_called_once_with(
            QUrl("https://github.com/milnet01/Slipcase/releases/tag/v1.4.0"))
        self.assertEqual(self.download.calls, [])
        self.assertIsNone(self.window._update_download_worker)

    def test_refused_while_busy(self):
        self.window._render_worker = MagicMock()
        self.window._render_worker.isRunning.return_value = True
        dialog = self._dialog()
        dialog.update_button.click()
        self.assertIsNone(self.window._update_download_worker)
        self.assertIn("Finish or stop the current render first", dialog.status_label.text())
        staged = self.dir / "slipcase-update-abcd1234.AppImage"
        staged.write_bytes(b"new")
        dialog._on_ready(str(staged))
        self.assertFalse(staged.exists())
        self.assertEqual(self.installer.applied, [])

    def test_apply_error_shown(self):
        installer = _FakeInstaller(self.dir, error=UpdateError("Slipcase was updated."))
        dialog = self._dialog(installer=installer)
        staged = self.dir / "slipcase-update-abcd1234.AppImage"
        staged.write_bytes(b"new")
        with patch("ui.update_dialog.QMessageBox") as box:
            dialog._on_ready(str(staged))
        self.assertEqual(installer.applied, [staged])
        box.warning.assert_called_once()
        self.assertIn("Slipcase was updated.", box.warning.call_args.args[2])

    def test_late_ready(self):
        dialog = self._dialog()
        dialog.close()
        staged = self.dir / "slipcase-update-abcd1234.AppImage"
        staged.write_bytes(b"new")
        dialog._on_ready(str(staged))
        self.assertFalse(staged.exists())
        self.assertEqual(self.installer.applied, [])

    def test_no_exec(self):
        source = (ROOT / "ui" / "update_dialog.py").read_text(encoding="utf-8")
        self.assertNotIn(".exec(", source)


class TestWindow(_WindowTest):
    """INV-2, INV-4, INV-12, INV-13."""

    def _show_with_reply(self, session):
        self.window.config.set("updates", "check", True)
        with patch("ui.main_window.detect_update_mode", return_value=UpdateMode(None)), \
                patch("api.releases.requests.Session", return_value=session):
            self.window.show()
            # The worker deletes itself when done, so wait on what it did.
            deadline = time.monotonic() + 5
            while not session.get.called and time.monotonic() < deadline:
                _settle(0.02)
            self.assertTrue(session.get.called, "no check started")
            _settle(0.3)

    def test_no_message_on_failed_check(self):
        session = MagicMock()
        session.get.side_effect = requests.ConnectionError("offline")
        with patch("ui.main_window.QMessageBox") as box, \
                patch("ui.update_dialog.QMessageBox") as dialog_box:
            self._show_with_reply(session)
        self.assertEqual(box.mock_calls, [])
        self.assertEqual(dialog_box.mock_calls, [])
        self.assertIsNone(self.window._update_dialog)
        session.get.assert_called_once()

    def test_offer_opens_dialog(self):
        session = MagicMock()
        session.get.return_value = _response(body=[b'{"tag_name": "v999.0.0"}'])
        self._show_with_reply(session)
        dialog = self.window._update_dialog
        self.assertIsNotNone(dialog)
        self.assertTrue(dialog.isVisible())
        self.assertIn("999.0.0", dialog.message_label.text())

    def test_shutdown_for_update(self):
        from ui.single_instance import SingleInstance
        lock_dir = self.dir / "run"
        lock_dir.mkdir()
        first = SingleInstance(str(lock_dir))
        self.assertTrue(first.acquire())
        from ui.main_window import MainWindow
        window = MainWindow(Config(self.config_path), release_instance=first.release)
        window.angle_slider.setValue(47)
        window.shutdown_for_update()
        self.assertEqual(Config(self.config_path).get("rendering", "angle"), 47)
        self.assertIsNone(window._front_image)
        second = SingleInstance(str(lock_dir))
        self.assertTrue(second.acquire(), "the lock was not released")
        second.release()
        window.close()

    def test_close_stops_update_workers(self):
        workers = {}
        for attr in ("_update_check_worker", "_update_download_worker"):
            worker = MagicMock()
            worker.isRunning.return_value = True
            worker.wait.return_value = True
            setattr(self.window, attr, worker)
            workers[attr] = worker
        self.window.close()
        for attr, worker in workers.items():
            worker.requestInterruption.assert_called_once()
            worker.wait.assert_called_once()
            self.assertIsNone(getattr(self.window, attr), attr)


class _Spawn:
    """Records Popen, before_exit and os._exit, in order."""

    def __init__(self, popen_error=None):
        self.order = []
        self.popen_error = popen_error
        self.popen = MagicMock(side_effect=self._popen)
        self.exit = MagicMock(side_effect=lambda code: self.order.append(("exit", code)))

    def _popen(self, *args, **kwargs):
        if self.popen_error is not None:
            raise self.popen_error
        self.order.append("spawn")
        return MagicMock()

    def before_exit(self):
        self.order.append("before_exit")


class TestAppImage(_TempDir):
    """INV-9."""

    def setUp(self):
        super().setUp()
        self.target = self.dir / "it's here.AppImage"
        self.target.write_bytes(b"old")
        self.new = self.dir / "slipcase-update-abcd1234.AppImage"
        self.new.write_bytes(b"new")
        self.installer = AppImageInstaller(self.target)

    def _apply(self, spawn, env=None, replace=None):
        patches = [patch("core.update_installer.subprocess.Popen", spawn.popen),
                   patch("core.update_installer.os._exit", spawn.exit),
                   patch("core.update_installer.config_dir", return_value=self.dir / "cfg"),
                   patch.dict(os.environ, env or {"APPIMAGE": str(self.target),
                                                  "APPDIR": str(self.dir / "mnt"), "ARGV0": "x"})]
        if replace is not None:
            patches.append(patch("core.update_installer.os.replace", replace))
        for p in patches:
            p.start()
        try:
            self.installer.apply(self.new, spawn.before_exit)
        finally:
            for p in reversed(patches):
                p.stop()

    def test_success(self):
        spawn = _Spawn()
        self._apply(spawn)
        self.assertEqual(self.target.read_bytes(), b"new")
        self.assertFalse(self.new.exists())
        argv = spawn.popen.call_args.args[0]
        kwargs = spawn.popen.call_args.kwargs
        self.assertEqual(argv[:2], ["/bin/sh", "-c"])
        self.assertEqual(argv[-2:], ["sh", str(self.target)])
        self.assertNotIn(str(self.target), argv[2])
        self.assertNotIn("it's", argv[2])
        self.assertIn('exec "$1"', argv[2])
        self.assertIs(kwargs["start_new_session"], True)
        self.assertEqual(kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"], "1")
        for name in ("APPIMAGE", "APPDIR", "ARGV0"):
            self.assertNotIn(name, kwargs["env"])
        self.assertEqual(spawn.order, ["spawn", "before_exit", ("exit", 0)])
        self.assertTrue((self.dir / "cfg" / "update-relaunch.log").exists())

    @unittest.skipUnless(os.path.exists("/bin/sh"), "needs /bin/sh")
    def test_script_parses(self):
        spawn = _Spawn()
        self._apply(spawn)
        script = spawn.popen.call_args.args[0][2]
        checked = subprocess.run(["/bin/sh", "-n", "-c", script],  # noqa: S603 -- our script
                                 capture_output=True, text=True, timeout=10)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_library_path_restored(self):
        spawn = _Spawn()
        self._apply(spawn, env={"LD_LIBRARY_PATH": "/bundle", "LD_LIBRARY_PATH_ORIG": "/orig"})
        self.assertEqual(spawn.popen.call_args.kwargs["env"]["LD_LIBRARY_PATH"], "/orig")
        self.new.write_bytes(b"new")
        spawn = _Spawn()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LD_LIBRARY_PATH_ORIG", None)
            self._apply(spawn, env={"LD_LIBRARY_PATH": "/bundle"})
        self.assertNotIn("LD_LIBRARY_PATH", spawn.popen.call_args.kwargs["env"])

    def test_failed_replace(self):
        spawn = _Spawn()
        with self.assertRaises(UpdateError):
            self._apply(spawn, replace=MagicMock(side_effect=OSError("busy")))
        self.assertEqual(self.target.read_bytes(), b"old")
        self.assertFalse(self.new.exists())
        self.assertEqual(spawn.order, [])

    def test_failed_spawn(self):
        spawn = _Spawn(popen_error=OSError("no sh"))
        with self.assertRaises(UpdateError) as caught:
            self._apply(spawn)
        self.assertEqual(str(caught.exception), "Slipcase was updated. Close it and open it again.")
        self.assertEqual(self.target.read_bytes(), b"new")
        self.assertEqual(spawn.order, [])
        spawn.exit.assert_not_called()


class TestWindows(_TempDir):
    """INV-10."""

    def setUp(self):
        super().setUp()
        folder = self.dir / "o'brien"
        folder.mkdir()
        self.target = folder / EXE
        self.target.write_bytes(b"old")
        self.new = folder / "slipcase-update-abcd1234.exe"
        self.new.write_bytes(b"new")
        self.installer = WindowsInstaller(self.target)

    def _apply(self, spawn):
        with patch("core.update_installer.subprocess.Popen", spawn.popen), \
                patch("core.update_installer.os._exit", spawn.exit), \
                patch.dict(os.environ, {"SystemRoot": "C:\\Windows"}), \
                patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True), \
                patch.object(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, create=True), \
                patch.object(subprocess, "DETACHED_PROCESS", 0x8, create=True):
            self.installer.apply(self.new, spawn.before_exit)

    def test_helper(self):
        spawn = _Spawn()
        self._apply(spawn)
        argv = spawn.popen.call_args.args[0]
        kwargs = spawn.popen.call_args.kwargs
        self.assertTrue(argv[0].endswith("powershell.exe"))
        self.assertTrue(ntpath.isabs(argv[0]), argv[0])
        self.assertEqual(argv[1:4], ["-NoProfile", "-NonInteractive", "-Command"])
        script = argv[4]
        self.assertIn("$_.Path -eq $exe", script)
        self.assertNotIn("-Id", script)
        self.assertIn("'" + str(self.target).replace("'", "''") + "'", script)
        self.assertIn("'" + str(self.new).replace("'", "''") + "'", script)
        self.assertIn("Move-Item", script)
        self.assertIn("Start-Process", script)
        self.assertEqual(kwargs["creationflags"], 0x08000000 | 0x200)
        self.assertEqual(kwargs["creationflags"] & 0x8, 0)
        self.assertEqual(kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"], "1")
        self.assertEqual(spawn.order, ["spawn", "before_exit", ("exit", 0)])
        self.assertEqual(self.target.read_bytes(), b"old", "the helper swaps, not apply")

    def test_curly_quote_doubled(self):
        target = self.dir / "o\u2019neill" / EXE
        target.parent.mkdir()
        installer = WindowsInstaller(target)
        spawn = _Spawn()
        self.installer = installer
        self._apply(spawn)
        self.assertIn("o\u2019\u2019neill", spawn.popen.call_args.args[0][4])

    def test_failed_spawn(self):
        spawn = _Spawn(popen_error=OSError("no powershell"))
        with self.assertRaises(UpdateError):
            self._apply(spawn)
        self.assertFalse(self.new.exists())
        self.assertEqual(self.target.read_bytes(), b"old")
        self.assertEqual(spawn.order, [])
        spawn.exit.assert_not_called()


class TestLeftovers(_TempDir):
    """INV-15."""

    def _file(self, name, age):
        path = self.dir / name
        path.write_bytes(b"x")
        when = time.time() - age
        os.utime(path, (when, when))
        return path

    def test_stale_removed_and_nothing_else(self):
        hours = 2 * 3600
        gone = [self._file("slipcase-update-abcd1234.AppImage", hours),
                self._file("slipcase-update-abcd1234.AppImage.sig", hours),
                self._file("slipcase-update-a_b_c_d_.AppImage", hours)]
        kept = [self._file("slipcase-update-efgh5678.AppImage", 0),
                self._file(APPIMAGE, hours),
                self._file("slipcase-update-notes.txt", hours),
                self._file("slipcase-update-abcd12345.AppImage", hours),
                self._file("slipcase-update-abcd1234.AppImage.old", hours),
                self._file("xslipcase-update-abcd1234.AppImage", hours),
                self._file("slipcase-update-abcd1234.exe", hours)]
        remove_stale_staged_updates(AppImageInstaller(self.dir / APPIMAGE))
        for path in gone:
            self.assertFalse(path.exists(), path.name)
        for path in kept:
            self.assertTrue(path.exists(), path.name)

    def test_unreadable_folder(self):
        with patch("core.updater.os.scandir", side_effect=PermissionError("no")):
            remove_stale_staged_updates(AppImageInstaller(self.dir / APPIMAGE))
        missing = self.dir / "gone"
        remove_stale_staged_updates(AppImageInstaller(missing / APPIMAGE))

    def test_failed_delete_is_ignored(self):
        self._file("slipcase-update-abcd1234.AppImage", 7200)
        with patch("core.updater.os.unlink", side_effect=PermissionError("held")):
            remove_stale_staged_updates(AppImageInstaller(self.dir / APPIMAGE))


if __name__ == "__main__":
    unittest.main()
