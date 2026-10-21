"""SLIP-0113: the case list shows only the chosen platform's cases."""

import os
import tempfile
import unittest

from core.case_types import (ALL_PLATFORMS, CASE_TYPES, PLATFORM_CASE_MAP,
                             REGIONAL_CASES, cases_for_platform)


class TestCasesForPlatform(unittest.TestCase):

    def test_every_case_is_offered_somewhere(self):
        offered = {name for p in ALL_PLATFORMS for name in cases_for_platform(p)}
        self.assertEqual(offered, set(CASE_TYPES))

    def test_default_first_then_regional(self):
        for platform in ALL_PLATFORMS:
            names = cases_for_platform(platform)
            self.assertEqual(names[0], PLATFORM_CASE_MAP[platform], platform)
            self.assertEqual(len(names), len(set(names)), platform)
            for (p, _region), name in REGIONAL_CASES.items():
                if p == platform:
                    self.assertIn(name, names)

    def test_other_consoles_cases_left_out(self):
        self.assertNotIn("PS2 DVD Case", cases_for_platform("PS1"))
        self.assertNotIn("PS1 Jewel Case (PAL)", cases_for_platform("Dreamcast"))


class TestEditionCases(unittest.TestCase):
    """Edition cases: the standard case's size in another plastic."""

    def test_edition_matches_its_standard_case(self):
        from core.case_types import EDITIONS
        self.assertTrue(EDITIONS)
        for name, base in EDITIONS.items():
            with self.subTest(case=name):
                case, standard = CASE_TYPES[name], CASE_TYPES[base]
                self.assertEqual(case.name, name)
                self.assertEqual((case.width, case.height, case.depth),
                                 (standard.width, standard.height, standard.depth))
                self.assertEqual(case.texture, standard.texture)
                self.assertEqual(case.platforms, ())
                self.assertIn(name, cases_for_platform(standard.platforms[0]))

    def test_named_editions(self):
        self.assertIn("PS2 Platinum Case (PAL)", cases_for_platform("PS2"))
        self.assertFalse(CASE_TYPES["PS3 Greatest Hits Case"].clear)
        self.assertTrue(CASE_TYPES["Xbox 360 Kinect Case"].clear)


class TestCaseCombo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def _window(self, d, **ui):
        from PyQt6 import sip
        from core.config import Config
        from ui.main_window import MainWindow
        config = Config(config_path=os.path.join(d, "c.json"))
        for key, value in ui.items():
            config.set("ui", key, value)
        window = MainWindow(config)
        self.addCleanup(sip.delete, window)
        return window

    def _items(self, window):
        return [window.case_combo.itemText(i) for i in range(window.case_combo.count())]

    def test_list_follows_platform(self):
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d)
            window.platform_combo.setCurrentText("PS1")
            self.assertEqual(self._items(window), cases_for_platform("PS1"))
            self.assertEqual(window.case_combo.currentText(), "PS1 Jewel Case (NTSC-U)")
            window.platform_combo.setCurrentText("PS2")
            self.assertEqual(self._items(window), cases_for_platform("PS2"))
            self.assertEqual(window.case_combo.currentText(), "PS2 DVD Case")

    def test_restore_keeps_saved_pair(self):
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d, last_platform="PS1",
                                  last_case_type="PS1 Jewel Case (PAL)")
            self.assertEqual(window.platform_combo.currentText(), "PS1")
            self.assertEqual(window.case_combo.currentText(), "PS1 Jewel Case (PAL)")

    def test_restore_case_from_another_platform(self):
        """A saved case the saved platform does not offer brings its own platform."""
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d, last_platform="PS2",
                                  last_case_type="Dreamcast Jewel Case (PAL)")
            self.assertEqual(window.platform_combo.currentText(), "Dreamcast")
            self.assertEqual(window.case_combo.currentText(), "Dreamcast Jewel Case (PAL)")


if __name__ == "__main__":
    unittest.main()
