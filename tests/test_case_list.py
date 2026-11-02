"""SLIP-0113: the case list shows only the chosen platform's cases."""

import os
import tempfile
import unittest
from dataclasses import replace

import numpy as np
from PIL import Image

from api.libretro import LIBRETRO_SYSTEMS
from api.screenscraper import SCREENSCRAPER_SYSTEMS
from api.thegamesdb import THEGAMESDB_PLATFORMS
from core.case_texture import generate_front_texture, generate_lid_shine
from core.case_types import (ALL_PLATFORMS, CASE_TYPES, PLATFORM_CASE_MAP,
                             REGIONAL_CASES, cases_for_platform)
from core.renderer import RETRODB_ANGLE, RETRODB_CAMERA_DISTANCE, BoxRenderer


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


class TestCartridgeBoxShape(unittest.TestCase):
    """SLIP-0108: US and PAL SNES and N64 boxes lie landscape; the Japanese
    Super Famicom and N64 boxes stand portrait (docs/research/
    SLIP-0108-cartridge-boxes.md)."""

    def test_shapes_by_region(self):
        from core.case_types import case_for
        for platform in ("SNES", "N64"):
            with self.subTest(platform=platform):
                for region in ("NTSC-U", "PAL"):
                    ct = case_for(platform, region)
                    self.assertGreater(ct.width, ct.height)
                jp = case_for(platform, "NTSC-J")
                self.assertLess(jp.width, jp.height)
                self.assertIn(jp.name, cases_for_platform(platform))

    def test_measured_sizes(self):
        from core.case_types import case_for
        self.assertEqual((CASE_TYPES["SNES Cartridge Box"].width,
                          CASE_TYPES["SNES Cartridge Box"].height), (178, 127))
        sfc = case_for("SNES", "NTSC-J")
        self.assertEqual((sfc.width, sfc.height, sfc.depth), (105, 190, 30))
        n64j = case_for("N64", "NTSC-J")
        self.assertEqual((n64j.width, n64j.height, n64j.depth), (138, 190, 30))


class TestSnesViewFromBelow(unittest.TestCase):
    """SLIP-0108: the SNES box shows its long bottom edge under the front, not
    its short left end, as RetroDB's boxes and the user's reference do."""

    RED, BLUE, YELLOW = (220, 30, 30), (30, 30, 220), (230, 220, 30)

    def _cover(self):
        """Red over the top left, blue over the top right, yellow below."""
        cover = Image.new("RGB", (356, 254), self.YELLOW)
        cover.paste(self.RED, (0, 0, 178, 127))
        cover.paste(self.BLUE, (178, 0, 356, 127))
        return cover

    def _render(self, *images, **kw):
        render_args = {k: kw.pop(k) for k in ("view", "full_cover", "spine_color")
                       if k in kw}
        args = dict(output_width=600, show_reflection=False, show_shadow=False,
                    show_texture=False)
        args.update(kw)
        return BoxRenderer(CASE_TYPES["SNES Cartridge Box"], **args).render(
            *(images or (self._cover(),)), title="Game", platform="SNES",
            **render_args)

    @staticmethod
    def _opaque_span(row):
        solid = np.where(row[:, 3] > 200)[0]
        return solid[0], solid[-1]

    def test_only_the_snes_box_has_it(self):
        below = {name for name, ct in CASE_TYPES.items() if ct.view_from_below}
        self.assertEqual(below, {"SNES Cartridge Box"})

    def test_art_stays_upright_and_unmirrored(self):
        pixels = np.asarray(self._render())
        height, width = pixels.shape[:2]
        self.assertGreater(pixels[height // 6, width // 3, 0], 150)   # red, left
        self.assertGreater(pixels[height // 6, width * 2 // 3, 2], 150)  # blue, right
        self.assertGreater(pixels[height // 2, width // 2, 1], 150)   # yellow, below

    def test_no_spine_on_the_left(self):
        """Halfway up the front, the first thing from the left is the cover."""
        pixels = np.asarray(self._render(Image.new("RGB", (356, 254), self.YELLOW)))
        row = pixels[pixels.shape[0] // 2]
        left, _ = self._opaque_span(row)
        self.assertGreater(row[left + 3, 1], 120)

    def _edge_middle(self, cover, **kw):
        """The bottom edge's colour, halfway up it and at its far right."""
        pixels = np.asarray(self._render(cover, **kw))
        row = pixels[int(pixels.shape[0] * 0.92)]
        _, right = self._opaque_span(row)
        return row[right - 25]

    def test_bottom_edge_takes_the_covers_bottom_colour(self):
        edge = self._edge_middle(Image.new("RGB", (356, 254), self.YELLOW))
        self.assertGreater(edge[0], 100)
        self.assertGreater(edge[1], 100)
        self.assertLess(edge[2], 80)

    def test_chosen_spine_colour_wins(self):
        edge = self._edge_middle(Image.new("RGB", (356, 254), self.YELLOW),
                                 spine_color=self.BLUE)
        self.assertGreater(edge[2], edge[0] + 50)

    def test_bottom_edge_runs_under_the_front(self):
        pixels = np.asarray(self._render(Image.new("RGB", (356, 254), self.YELLOW),
                                         spine_color=(10, 10, 10)))
        yellow = (pixels[:, :, 1] > 120) & (pixels[:, :, 0] > 120) & (pixels[:, :, 2] < 90)
        last_front_row = np.where(yellow.any(axis=1))[0][-1]
        band = pixels[last_front_row + 4:]
        self.assertGreater(band.shape[0], pixels.shape[0] * 0.08)
        left, right = self._opaque_span(band[band.shape[0] // 2])
        self.assertGreater(right - left, pixels.shape[1] * 0.9)
        self.assertFalse(yellow[last_front_row + 4:].any())

    def test_far_edge_matches_retrodb(self):
        pixels = np.asarray(self._render(
            angle=RETRODB_ANGLE, camera_distance=RETRODB_CAMERA_DISTANCE))
        solid = pixels[:, :, 3] > 200
        widths = solid.sum(axis=1)
        rows = np.where(widths)[0]
        self.assertAlmostEqual(widths[rows[3]] / widths.max(), 0.775, delta=0.02)
        # RetroDB's box is 1.84 wide for each unit of height.
        self.assertAlmostEqual(
            pixels.shape[1] / pixels.shape[0], 1.84, delta=0.15)

    def test_fills_the_output_width(self):
        width = self._render().width
        self.assertGreater(width, 540)
        self.assertLessEqual(width, 600)

    def test_frames_of_a_turn_share_one_scale(self):
        widths = {angle: self._render(angle=angle, fit_angle=45).width
                  for angle in (15, 30, 45)}
        self.assertLess(max(widths.values()) - min(widths.values()), 4)

    def test_back_view_shows_the_back_cover(self):
        back = Image.new("RGB", (356, 254), (30, 200, 60))
        pixels = np.asarray(self._render(self._cover(), back, view="back"))
        self.assertGreater(pixels[pixels.shape[0] // 3, pixels.shape[1] // 2, 1], 120)
        with self.assertRaises(ValueError):
            self._render(view="back")

    def test_full_cover_uses_its_front_panel(self):
        wrap = Image.new("RGB", (776, 254), (30, 200, 60))
        wrap.paste(self.YELLOW, (420, 0, 776, 254))
        pixels = np.asarray(self._render(wrap, full_cover=True))
        centre = pixels[pixels.shape[0] // 3, pixels.shape[1] // 2]
        self.assertGreater(centre[0], 120)
        self.assertLess(centre[2], 90)

    def test_shadow_and_reflection_still_drawn(self):
        plain = self._render()
        self.assertGreater(self._render(show_reflection=True).height,
                           plain.height + plain.height // 6)
        shadowed = np.asarray(self._render(show_shadow=True))
        self.assertTrue(((shadowed[:, :, 3] > 0) & (shadowed[:, :, 3] < 200)).any())


class TestCardboardBoxSizes(unittest.TestCase):
    """SLIP-0108: sizes from docs/research/SLIP-0108-cartridge-boxes.md. US and
    PAL Game Boy boxes are square; the Japanese ones stand portrait, and the
    Japanese GBA box lies landscape."""

    @staticmethod
    def _size(ct):
        return ct.width, ct.height, ct.depth

    def test_western_sizes(self):
        self.assertEqual(self._size(CASE_TYPES["NES Cartridge Box"]), (127, 180, 24))
        self.assertEqual(self._size(CASE_TYPES["Game Boy Box"]), (126, 126, 23))
        self.assertEqual(self._size(CASE_TYPES["GBA Box"]), (126, 126, 23))

    def test_japanese_sizes_by_region(self):
        from core.case_types import case_for
        for platform in ("Game Boy", "Game Boy Color"):
            with self.subTest(platform=platform):
                ct = case_for(platform, "NTSC-J")
                self.assertEqual(self._size(ct), (89, 102, 19))
                self.assertIn(ct.name, cases_for_platform(platform))
                self.assertEqual(case_for(platform, "PAL").name, "Game Boy Box")
        gba = case_for("GBA", "NTSC-J")
        self.assertEqual(self._size(gba), (137, 87, 21))
        self.assertIn(gba.name, cases_for_platform("GBA"))
        self.assertEqual(case_for("GBA", "NTSC-U").name, "GBA Box")


class TestSegaClamshells(unittest.TestCase):
    """SLIP-0108: Genesis, Mega Drive and Master System games came in the same
    black plastic case, with a hanging tab above the top edge."""

    CASES = ("Genesis Clamshell", "Master System Case")

    def _render(self, name, **kw):
        args = dict(output_width=400, show_reflection=False, show_shadow=False)
        args.update(kw)
        return BoxRenderer(CASE_TYPES[name], **args).render(
            Image.new("RGB", (300, 420), (200, 40, 40)), title="Game")

    def test_size_and_plastic(self):
        for name in self.CASES:
            with self.subTest(case=name):
                ct = CASE_TYPES[name]
                self.assertEqual((ct.width, ct.height, ct.depth), (128, 179, 26))
                self.assertEqual(ct.plastic, (0x14, 0x14, 0x14))
                self.assertFalse(ct.clear)
                self.assertGreater(ct.rim_mm, 0)
                self.assertTrue(ct.hanging_tab)

    def test_platforms(self):
        self.assertEqual(PLATFORM_CASE_MAP["Master System"], "Master System Case")
        self.assertEqual(PLATFORM_CASE_MAP["Mega Drive"], "Genesis Clamshell")
        self.assertIn("Universal Cart Case", cases_for_platform("Master System"))

    def test_master_system_can_be_searched(self):
        self.assertEqual(LIBRETRO_SYSTEMS["Master System"],
                         "Sega - Master System - Mark III")
        self.assertEqual(SCREENSCRAPER_SYSTEMS["Master System"], 2)
        self.assertEqual(THEGAMESDB_PLATFORMS["Master System"], 35)

    def test_tab_stands_above_the_box(self):
        with_tab = self._render("Genesis Clamshell")
        without = BoxRenderer(
            replace(CASE_TYPES["Genesis Clamshell"], hanging_tab=False),
            output_width=400, show_reflection=False, show_shadow=False,
        ).render(Image.new("RGB", (300, 420), (200, 40, 40)), title="Game")
        self.assertEqual(with_tab.width, without.width)
        self.assertGreater(with_tab.height, without.height)
        # The box below the tab is unchanged in size.
        added = with_tab.height - without.height
        tab = np.asarray(with_tab)[:added, :, 3] > 128
        columns = np.where(tab.any(axis=0))[0]
        # About 50 of the case's 128 mm wide, so a good part of the render.
        self.assertGreater(columns.size, with_tab.width * 0.2)
        self.assertLess(columns.size, with_tab.width * 0.5)

    def test_tab_has_a_slot_to_hang_from(self):
        image = np.asarray(self._render("Genesis Clamshell"))[:, :, 3] > 128
        without = BoxRenderer(
            replace(CASE_TYPES["Genesis Clamshell"], hanging_tab=False),
            output_width=400, show_reflection=False, show_shadow=False,
        ).render(Image.new("RGB", (300, 420), (200, 40, 40)), title="Game")
        tab = image[:image.shape[0] - without.height]
        columns = np.where(tab.any(axis=0))[0]
        middle = image[:, (columns[0] + columns[-1]) // 2]
        solid = np.where(middle)[0]
        # A gap in the middle column, between the tab's top and the box below.
        self.assertLess(middle[solid[0]:solid[-1] + 1].sum(), solid[-1] + 1 - solid[0])

    def test_tab_takes_the_case_colour(self):
        ct = CASE_TYPES["Genesis Clamshell"]
        cover = Image.new("RGB", (300, 420), (200, 40, 40))

        def tab_red(**kw):
            """The red of the tab's top rows, the first solid ones down."""
            image = np.asarray(BoxRenderer(
                ct, output_width=400, show_reflection=False, show_shadow=False,
            ).render(cover, title="Game", **kw))
            solid = np.where((image[:, :, 3] > 200).any(axis=1))[0][:3]
            rows = image[solid]
            return rows[rows[:, :, 3] > 200][:, 0].mean()

        self.assertLess(tab_red(), 40)
        self.assertGreater(tab_red(case_color=(220, 30, 30)), 120)

    def test_match_retrodb_draws_no_tab(self):
        """RetroDB's own Sega boxes have none, so they stay side by side."""
        camera = dict(angle=RETRODB_ANGLE, camera_distance=RETRODB_CAMERA_DISTANCE)
        with_tab = self._render("Genesis Clamshell", **camera)
        without = BoxRenderer(
            replace(CASE_TYPES["Genesis Clamshell"], hanging_tab=False),
            output_width=400, show_reflection=False, show_shadow=False, **camera,
        ).render(Image.new("RGB", (300, 420), (200, 40, 40)), title="Game")
        self.assertEqual(with_tab.size, without.size)
        self.assertEqual(with_tab.tobytes(), without.tobytes())

    def test_other_cases_have_no_tab(self):
        tabbed = {name for name, ct in CASE_TYPES.items() if ct.hanging_tab}
        self.assertEqual(tabbed, set(self.CASES))

    def test_clear_sleeve_shines_without_cardboard_folds(self):
        for name in self.CASES:
            with self.subTest(case=name):
                sleeve = generate_front_texture(CASE_TYPES[name], 200, 280)
                expected = Image.new("RGBA", (200, 280), (0, 0, 0, 0))
                expected.alpha_composite(generate_lid_shine(200, 280))
                self.assertEqual(sleeve.tobytes(), expected.tobytes())


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
