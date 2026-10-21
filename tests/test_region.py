"""Tests for core/region.py and case_for: the case a cover's region picks (SLIP-0106)."""

import unittest

from core.case_types import case_for
from core.region import NTSC_J, NTSC_U, PAL, detect_region


class TestDetectRegion(unittest.TestCase):

    def test_detect_region(self):
        """INV-1: the first whole known word, in any group, decides."""
        expected = {
            "Ridge Racer Type 4 (Europe).png": PAL,
            "Game (USA, Europe).png": NTSC_U,
            "Tomb Raider (PSX) (USA).png": NTSC_U,
            # Only reading every group, not the first alone, finds Japan.
            "Game (PSX) (Japan).png": NTSC_J,
            "Game (France) (Rev 1).png": PAL,
            "Game (En,Fr,De).png": NTSC_U,
            "Europa (Demo).png": NTSC_U,
            # A substring match finds "EU" in "Europa" and calls this PAL.
            "Game (Europa Demo).png": NTSC_U,
            "Game.png": NTSC_U,
        }
        for name, region in expected.items():
            with self.subTest(name=name):
                self.assertEqual(detect_region(name), region)


class TestCaseFor(unittest.TestCase):

    def test_case_for(self):
        """INV-2 (SLIP-0106), INV-6 (SLIP-0107): a regional variant where one
        exists, else the default."""
        expected = {
            ("PS1", PAL): "PS1 Jewel Case (PAL)",
            ("PS1", NTSC_U): "PS1 Jewel Case (NTSC-U)",
            ("Dreamcast", NTSC_J): "Dreamcast Jewel Case (NTSC-J)",
            ("PS2", PAL): "PS2 DVD Case (PAL)",
            ("PS2", NTSC_U): "PS2 DVD Case",
            ("DS", PAL): "DS Case (PAL)",
            ("GameCube", NTSC_J): "GameCube Case (NTSC-J)",
            ("GameCube", PAL): "GameCube DVD Case",
            ("Saturn", PAL): "CD Jewel Case",
        }
        for (platform, region), name in expected.items():
            with self.subTest(platform=platform, region=region):
                self.assertEqual(case_for(platform, region).name, name)
        self.assertIsNone(case_for("No Such Platform", PAL))


if __name__ == "__main__":
    unittest.main()
