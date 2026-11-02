"""Tests for core/region.py and case_for: the case a cover's region picks (SLIP-0106)."""

import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from core.case_types import case_for
from core.region import (_DREAMCAST_HEADER, _PLAYSTATION_FOOTER, NTSC_J, NTSC_U, PAL,
                         artwork_can_tell, cover_region, detect_region,
                         region_from_artwork, region_from_name)


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


def _strip(mark: tuple[int, ...], width: int, height: int) -> np.ndarray:
    """A strip whose columns are bright by `mark`'s amounts, on nothing."""
    columns = np.interp(np.linspace(0, len(mark) - 1, width), range(len(mark)), mark)
    return np.arange(height)[:, None] * 100 < columns[None, :] * height


def ps1_cover(footer: bool = True) -> Image.Image:
    """A square cover of mid-grey art, with PAL's black footer and wordmark."""
    art = np.full((512, 512, 3), 120, dtype=np.uint8)
    if footer:
        art[int(512 * .88):] = 0
        top = int(512 * .895)
        art[top:top + 40, 60:460][_strip(_PLAYSTATION_FOOTER, 400, 40)] = 255
    return Image.fromarray(art)


def _dc_cover(header: bool = True, ground: tuple[int, int, int] = (40, 80, 180)) -> Image.Image:
    """A square cover with a coloured head band, PAL's wordmark and swirl on it
    when `header`."""
    art = np.full((512, 512, 3), 120, dtype=np.uint8)
    art[:int(512 * .12)] = ground
    if header:
        art[10:10 + 44, :500][_strip(_DREAMCAST_HEADER, 500, 44)] = 255
    return Image.fromarray(art)


class TestRegionFromArtwork(unittest.TestCase):
    """SLIP-0119. Real covers cannot live in this repository, so these are
    drawn from the same column profiles. The real-cover results are on the
    roadmap item."""

    def test_marks_found(self):
        self.assertEqual(region_from_artwork(ps1_cover(), "PS1"), PAL)
        self.assertEqual(region_from_artwork(_dc_cover(), "Dreamcast"), PAL)

    def test_no_mark_no_region(self):
        self.assertIsNone(region_from_artwork(ps1_cover(footer=False), "PS1"))
        self.assertIsNone(region_from_artwork(_dc_cover(header=False), "Dreamcast"))

    def test_black_foot_alone_is_not_the_footer(self):
        """Dark art with bright detail at the foot, as on many US and Japanese
        covers, reaches the match and fails it."""
        art = np.full((512, 512, 3), 120, dtype=np.uint8)
        art[int(512 * .88):] = 0
        speckle = np.random.default_rng(1).random(art.shape[:2]) > .9
        art[int(512 * .88):][speckle[int(512 * .88):]] = 255
        self.assertIsNone(region_from_artwork(Image.fromarray(art), "PS1"))

    def test_wordmark_needs_the_dark_foot(self):
        """A wordmark-shaped title on bright art is not the footer."""
        art = np.asarray(ps1_cover()).copy()
        foot = art[int(512 * .88):]
        foot[foot[..., 0] == 0] = 200
        art[int(512 * .895):int(512 * .895) + 40, 60:460][
            ~_strip(_PLAYSTATION_FOOTER, 400, 40)] = 90
        self.assertIsNone(region_from_artwork(Image.fromarray(art), "PS1"))

    def test_only_cover_shapes_are_read(self):
        """A wrap holds no tested layout, and a sliver must not be blown up:
        at 512 wide a tall one would need billions of pixels. Small slivers
        here, so that losing the limit fails this test and not the machine."""
        wrap = Image.new("RGB", (1024, 512))
        wrap.paste(ps1_cover(), (512, 0))
        self.assertIsNone(region_from_artwork(wrap, "PS1"))
        self.assertIsNone(region_from_artwork(ps1_cover().resize((1024, 512)), "PS1"))
        sliver, wide = Image.new("RGB", (1, 100)), Image.new("RGB", (100, 1))
        with patch("core.region.Image.new") as flatten:
            self.assertIsNone(region_from_artwork(sliver, "PS1"))
            self.assertIsNone(region_from_artwork(wide, "PS1"))
        flatten.assert_not_called()

    def test_wordmark_needs_the_blue_ground(self):
        """Rippin' Riders and others: a title fits the shape on other art."""
        self.assertIsNone(region_from_artwork(_dc_cover(ground=(150, 40, 30)), "Dreamcast"))

    def test_only_its_own_platform(self):
        self.assertIsNone(region_from_artwork(ps1_cover(), "PS2"))
        self.assertIsNone(region_from_artwork(_dc_cover(), "PS1"))
        self.assertTrue(artwork_can_tell("PS1"))
        self.assertFalse(artwork_can_tell("PS2"))

    def test_transparent_ground_reads_as_black(self):
        """libretro boxarts carry alpha: a clear foot over bright pixels must
        read as the black behind it, not as those pixels."""
        cover = np.asarray(ps1_cover().convert("RGBA")).copy()
        clear = cover[..., 0] == 0
        cover[clear] = (255, 255, 255, 0)
        self.assertEqual(region_from_artwork(Image.fromarray(cover), "PS1"), PAL)

    def test_file_name_beats_artwork(self):
        self.assertEqual(cover_region("Game (USA).png", ps1_cover(), "PS1"), NTSC_U)
        self.assertEqual(cover_region("Game (Japan).png", ps1_cover(), "PS1"), NTSC_J)

    def test_artwork_decides_a_silent_name(self):
        self.assertEqual(cover_region("1234_ss_boxart.webp", ps1_cover(), "PS1"), PAL)
        self.assertEqual(cover_region("1234_ss_boxart.webp", ps1_cover(False), "PS1"), NTSC_U)
        self.assertEqual(cover_region("1234_ss_boxart.webp", None, "PS1"), NTSC_U)

    def test_name_region_none_when_silent(self):
        self.assertIsNone(region_from_name("1234_ss_boxart.webp"))


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
            ("Saturn", PAL): "Sega Long Box",
            ("Saturn", NTSC_J): "CD Jewel Case",
        }
        for (platform, region), name in expected.items():
            with self.subTest(platform=platform, region=region):
                self.assertEqual(case_for(platform, region).name, name)
        self.assertIsNone(case_for("No Such Platform", PAL))


if __name__ == "__main__":
    unittest.main()
