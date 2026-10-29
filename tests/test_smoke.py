"""`main.py --smoke` checks the parts a packaged build can lose (SLIP-0018).

A bundle can be built with the resources folder missing, a Qt plugin left
out, or a batch worker that re-launches the window instead of rendering, and
still start without an error. The self-check exercises each and reports one
line; the packaging scripts run it against every build they produce.

Run as a separate process, the way the packaging scripts run it, so the
argument handling and the exit code are part of what is tested.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.version import __version__

ROOT = Path(__file__).resolve().parent.parent


class TestSmoke(unittest.TestCase):

    def _run(self, *args: str, scratch: str) -> subprocess.CompletedProcess:
        # A private config and runtime folder: a self-check must never read
        # or write the settings of the person running it.
        # APPDATA is where Windows keeps them; the XDG pair is Linux and macOS.
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", APPDATA=scratch,
                   XDG_CONFIG_HOME=scratch, XDG_RUNTIME_DIR=scratch)
        return subprocess.run(  # noqa: S603 -- our own interpreter and script
            [sys.executable, str(ROOT / "main.py"), *args],
            env=env, capture_output=True, text=True, timeout=120,
        )

    def test_smoke_passes_and_reports_the_version(self):
        with tempfile.TemporaryDirectory() as scratch:
            report = Path(scratch) / "report.txt"
            result = self._run(f"--smoke={report}", scratch=scratch)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            expected = f"slipcase smoke OK {__version__}"
            self.assertEqual(report.read_text(encoding="utf-8").strip(), expected)
            self.assertIn(expected, result.stdout)

    def test_smoke_leaves_no_settings_behind(self):
        with tempfile.TemporaryDirectory() as scratch:
            result = self._run("--smoke", scratch=scratch)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((Path(scratch) / "slipcase").exists(),
                             "the self-check created a settings folder")

    def test_smoke_fails_without_the_release_key(self):
        """SLIP-0030 INV-6: a build that cannot load the release public key
        must not report OK, whether the import fails at start-up or inside
        the check. The build scripts look for the OK line."""
        wrapper = ("import runpy, sys; sys.modules['core.update_key'] = None; "
                   f"sys.argv = ['main.py', '--smoke']; sys.path.insert(0, {str(ROOT)!r}); "
                   f"runpy.run_path({str(ROOT / 'main.py')!r}, run_name='__main__')")
        with tempfile.TemporaryDirectory() as scratch:
            env = dict(os.environ, QT_QPA_PLATFORM="offscreen", APPDATA=scratch,
                       XDG_CONFIG_HOME=scratch, XDG_RUNTIME_DIR=scratch)
            result = subprocess.run(  # noqa: S603 -- our own interpreter
                [sys.executable, "-c", wrapper], cwd=ROOT,
                env=env, capture_output=True, text=True, timeout=120)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("slipcase smoke OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
