"""Only one copy of the app runs at a time (SLIP-0049).

Two copies each held their own settings in memory and whichever saved last
overwrote the other, losing credentials entered in the first. A second
launch now hands over to the running copy and exits.

Both "instances" live in this process, each with its own lock and socket
path in a temporary directory, so nothing touches the real runtime folder.
"""

import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

from ui.single_instance import SingleInstance


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
        first, second = self._instance(), self._instance()
        shown = []
        self.assertTrue(first.acquire(on_activate=lambda: shown.append(True)))
        self.assertFalse(second.acquire())
        self.assertTrue(second.activate_running())
        self.assertTrue(_wait_for(lambda: shown), "the first copy was never told")

    def test_a_copy_can_start_after_the_first_has_closed(self):
        first = self._instance()
        self.assertTrue(first.acquire())
        first.release()
        self.assertTrue(self._instance().acquire())

    def test_a_lock_left_by_a_crashed_copy_does_not_block_startup(self):
        # QLockFile writes the owner's pid; a pid that is no longer running
        # marks the lock stale. Simulate a dead owner.
        lock_path = os.path.join(self._dir.name, "slipcase.lock")
        with open(lock_path, "w") as f:
            f.write("999999999\nslipcase\n" + os.uname().nodename + "\n")
        self.assertTrue(self._instance().acquire())


if __name__ == "__main__":
    unittest.main()
