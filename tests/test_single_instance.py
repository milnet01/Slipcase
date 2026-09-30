"""Only one copy of the app runs at a time (SLIP-0049).

Two copies each held their own settings in memory and whichever saved last
overwrote the other, losing credentials entered in the first. A second
launch now hands over to the running copy and exits.

Each test uses its own lock and socket path in a temporary directory, so
nothing touches the real runtime folder. The competing "instances" live in
this process; the second launch that sends the wake-up is a real one.
"""

import os
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QCoreApplication, QLockFile
from PyQt6.QtWidgets import QApplication

from ui.single_instance import SingleInstance


_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# What a second launch does, as its own process: argv is the project root
# and the runtime directory. Exits 0 if the running copy answered.
_SECOND_LAUNCH = """
import sys
sys.path.insert(0, sys.argv[1])
from PyQt6.QtCore import QCoreApplication
app = QCoreApplication([])
from ui.single_instance import SingleInstance
sys.exit(0 if SingleInstance(sys.argv[2]).activate_running() else 1)
"""


def _wait_for(condition, seconds=3.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


class TestSingleInstance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # QApplication, not QCoreApplication: whichever test creates the
        # app first decides its kind for the whole run, and the window tests
        # abort under a core-only app when test order is shuffled.
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)

    def _instance(self):
        inst = SingleInstance(self._dir.name)
        self.addCleanup(inst.release)
        return inst

    def test_the_first_copy_runs_and_a_second_does_not(self):
        first, second = self._instance(), self._instance()
        self.assertTrue(first.acquire())
        self.assertFalse(second.acquire())

    def test_a_second_launch_asks_the_first_to_show_itself(self):
        first = self._instance()
        shown = []
        self.assertTrue(first.acquire(on_activate=lambda: shown.append(True)))
        self.assertFalse(self._instance().acquire())
        # The second launch is a separate process, as it is in use. It has to
        # be on Windows: the two ends of a named pipe cannot both be served
        # from one thread, so an in-process sender never finishes its write.
        second = subprocess.Popen(  # noqa: S603 -- our own interpreter and code
            [sys.executable, "-c", _SECOND_LAUNCH, _ROOT, self._dir.name])
        self.addCleanup(second.kill)
        self.assertTrue(_wait_for(lambda: shown, seconds=15),
                        "the first copy was never told")
        self.assertEqual(second.wait(timeout=15), 0, "the second launch got no answer")

    def test_a_copy_can_start_after_the_first_has_closed(self):
        first = self._instance()
        self.assertTrue(first.acquire())
        first.release()
        self.assertTrue(self._instance().acquire())

    def test_a_lock_left_by_a_crashed_copy_does_not_block_startup(self):
        # QLockFile writes the owner's pid; a pid that is no longer running
        # marks the lock stale. Simulate a dead owner.
        lock_path = os.path.join(self._dir.name, "slipcase.lock")
        # The host name as QLockFile itself writes it, read back from a real
        # lock: on Windows that is not the spelling QSysInfo reports, and a
        # lock naming any other host is never treated as stale.
        probe = QLockFile(os.path.join(self._dir.name, "probe.lock"))
        self.assertTrue(probe.tryLock(0))
        host = probe.getLockInfo()[2]
        probe.unlock()
        # newline="\n": Qt reads the lines as written, and Windows' "\r\n"
        # would make the host name a different one, which is never stale.
        with open(lock_path, "w", newline="\n") as f:
            f.write("999999999\nslipcase\n" + host + "\n")
        self.assertTrue(self._instance().acquire())


if __name__ == "__main__":
    unittest.main()
