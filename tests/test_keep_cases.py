"""Tests for keep and handheld cases per console and region (SLIP-0107)."""

import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw

import core.case_texture as case_texture
from core.box_model import build_box_model
from core.case_texture import generate_front_texture, generate_spine_texture
from core.case_types import CASE_TYPES
from core.image_utils import case_edge_colours
from core.renderer import BoxRenderer

BLACK, WHITE = (0x14, 0x14, 0x14), (0xEE, 0xEE, 0xEE)
BLUE_TINT, GREEN_TINT = (0x2A, 0x6C, 0xD0), (0x2E, 0x9E, 0x3A)

# § 4.1: name -> (W, H, D, plastic, clear, texture).
TABLE = {
    "PS2 DVD Case": (135, 190, 14, BLACK, False, "dvd"),
    "PS2 DVD Case (PAL)": (135, 190, 14, (0x1F, 0x4E, 0xA8), False, "dvd"),
    "Wii DVD Case": (135, 190, 14, WHITE, False, "dvd"),
    "GameCube DVD Case": (135, 190, 14, BLACK, False, "dvd"),
    "GameCube Case (NTSC-J)": (107, 149, 17, None, True, "dvd"),
    "PC DVD Case": (135, 190, 14, BLACK, False, "dvd"),
    "Xbox Case": (129, 189, 13, (0x5C, 0xB0, 0x2E), False, "dvd"),
    "Xbox 360 Case": (133, 187, 13, (0x6C, 0xC0, 0x40), True, "dvd"),
    "PS3 Blu-ray Case": (135, 171.5, 13, (0xF0, 0xF0, 0xF0), True, "bluray"),
    "PS4 Blu-ray Case": (135, 171.5, 13, BLUE_TINT, True, "bluray"),
    "PS5 Blu-ray Case": (135, 171.5, 13, BLUE_TINT, True, "bluray"),
    "Xbox One Case": (135, 171.5, 13, GREEN_TINT, True, "bluray"),
    "Xbox Series X Case": (135, 171.5, 13, GREEN_TINT, True, "bluray"),
    "DS Case": (122, 135, 15, BLACK, False, "ds"),
    "DS Case (PAL)": (122, 135, 20, None, True, "ds"),
    "3DS Case": (122, 135, 12, WHITE, False, "ds"),
    "PSP Case": (99, 168, 14, None, True, "psp"),
    "PS Vita Case": (105, 135, 12, (0x1E, 0x50, 0xB4), False, "psp"),
    "Switch Case": (104, 170, 10, None, True, "switch"),
}


def _cover() -> Image.Image:
    """Red above, blue below, so sampled edge colours show."""
    cover = Image.new("RGB", (270, 380), (200, 0, 0))
    cover.paste((0, 0, 200), (0, 190, 270, 380))
    return cover


class TestCaseData(unittest.TestCase):

    def test_case_table(self):
        """INV-2: each case matches § 4.1's tables."""
        for name, (w, h, d, plastic, clear, texture) in TABLE.items():
            with self.subTest(case=name):
                ct = CASE_TYPES[name]
                self.assertEqual((ct.width, ct.height, ct.depth), (w, h, d))
                self.assertEqual((ct.plastic, ct.clear, ct.texture), (plastic, clear, texture))
        self.assertNotIn("DVD Case", CASE_TYPES)
        self.assertNotIn("Blu-ray Case", CASE_TYPES)


class TestEdgeColours(unittest.TestCase):

    def test_edge_colour_rules(self):
        """§ 4.2: case colour wins; opaque plastic all round; clear samples
        the cover, tinted."""
        cover = _cover()
        ps2, switch, ps4 = (CASE_TYPES[n] for n in
                            ("PS2 DVD Case", "Switch Case", "PS4 Blu-ray Case"))
        self.assertEqual(case_edge_colours(cover, ps2, (9, 8, 7)), ((9, 8, 7),) * 3)
        self.assertEqual(case_edge_colours(cover, ps2, None), (BLACK,) * 3)
        self.assertEqual(case_edge_colours(cover, switch, None),
                         ((200, 0, 0), (0, 0, 200), (200, 0, 0)))
        # 200 + (0x2A - 200) * 0.3 = 152.6, and so on.
        top, _bottom, edge = case_edge_colours(cover, ps4, None)
        self.assertEqual(top, (153, 32, 62))
        self.assertEqual(edge, top)

    def test_edge_colours_agree(self):
        """INV-3: render's top colour and the box model's top agree."""
        cover = _cover()
        for name in ("PS2 DVD Case", "Switch Case", "PS4 Blu-ray Case", "NES Cartridge Box"):
            for case_color in (None, (9, 8, 7)):
                with self.subTest(case=name, case_color=case_color):
                    ct = CASE_TYPES[name]
                    renderer = BoxRenderer(ct, angle=30, output_width=256)
                    with patch.object(renderer, "_render_faces",
                                      wraps=renderer._render_faces) as faces:
                        renderer.render(cover, case_color=case_color, full_cover=False)
                    model = build_box_model(
                        cover, None, ct, title="Game", serial="", platform="PS2",
                        spine_color=None, case_color=case_color,
                        spine_left_offset=0, spine_right_offset=0,
                        full_cover=False, show_texture=False,
                    )
                    expected = case_edge_colours(cover, ct, case_color)
                    self.assertEqual(faces.call_args.kwargs["top_color"], expected[0])
                    self.assertEqual(model.top, expected[0])


class TestOverlays(unittest.TestCase):

    def test_clear_case_shines(self):
        """INV-4: a clear case's front is brighter at its top-left than an
        opaque case's of the same family."""
        clear = generate_front_texture(CASE_TYPES["GameCube Case (NTSC-J)"], 200, 280)
        opaque = generate_front_texture(CASE_TYPES["PS2 DVD Case"], 200, 280)
        self.assertGreater(clear.getpixel((40, 50))[3], opaque.getpixel((40, 50))[3])

    def test_overlay_by_family(self):
        """INV-5: each family draws the overlay its old entry drew."""
        def drawn(draw_fn, w, h):
            image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw_fn(ImageDraw.Draw(image), w, h)
            return np.array(image)

        w, h = 200, 280
        fronts = {"PS2 DVD Case": case_texture._draw_dvd_front,
                  "NES Cartridge Box": case_texture._draw_cardboard_front,
                  "DS Case": case_texture._draw_ds_front,
                  "PS Vita Case": case_texture._draw_psp_front}
        spines = {"PS2 DVD Case": case_texture._draw_dvd_spine,
                  "PS4 Blu-ray Case": case_texture._draw_bluray_spine,
                  "NES Cartridge Box": case_texture._draw_cardboard_spine,
                  "Switch Case": case_texture._draw_keepcase_spine,
                  "DS Case": case_texture._draw_keepcase_spine,
                  "PS Vita Case": case_texture._draw_keepcase_spine}
        for name, fn in fronts.items():
            with self.subTest(front=name):
                self.assertTrue(np.array_equal(
                    np.array(generate_front_texture(CASE_TYPES[name], w, h)), drawn(fn, w, h)))
        for name, fn in spines.items():
            with self.subTest(spine=name):
                self.assertTrue(np.array_equal(
                    np.array(generate_spine_texture(CASE_TYPES[name], 20, h)),
                    drawn(fn, 20, h)))


class TestSavedCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def test_removed_case_name_restores(self):
        """INV-7: a saved "DVD Case" restores the saved platform's case."""
        from PyQt6 import sip

        from core.config import Config
        from ui.main_window import MainWindow
        with tempfile.TemporaryDirectory() as d:
            config = Config(config_path=os.path.join(d, "c.json"))
            config.set("ui", "last_platform", "Wii")
            config.set("ui", "last_case_type", "DVD Case")
            window = MainWindow(config)
            self.addCleanup(sip.delete, window)
            self.assertEqual(window.case_combo.currentText(), "Wii DVD Case")


if __name__ == "__main__":
    unittest.main()
