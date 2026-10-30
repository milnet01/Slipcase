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
from core.case_types import CASE_TYPES, KEEP_RIM_MM
from core.image_utils import CLEAR_RIM, case_edge_colours, inset_in_rim
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
        """Case colour wins; a case's plastic goes all round, clear or not;
        a case with no plastic samples the cover (SLIP-0107, amended)."""
        cover = _cover()
        ps2, switch, ps4, nes = (CASE_TYPES[n] for n in (
            "PS2 DVD Case", "Switch Case", "PS4 Blu-ray Case", "NES Cartridge Box"))
        self.assertEqual(case_edge_colours(cover, ps2, (9, 8, 7)), ((9, 8, 7),) * 3)
        self.assertEqual(case_edge_colours(cover, ps2, None), (BLACK,) * 3)
        self.assertEqual(case_edge_colours(cover, ps4, None), (BLUE_TINT,) * 3)
        self.assertEqual(case_edge_colours(cover, switch, None), (CLEAR_RIM,) * 3)
        self.assertEqual(case_edge_colours(cover, nes, None),
                         ((200, 0, 0), (0, 0, 200), (200, 0, 0)))

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


class TestRim(unittest.TestCase):
    """A keep case's plastic rim frames the cover on the top, bottom and
    opening side; a cardboard box and a jewel case have none."""

    RED = (200, 0, 0)

    def _model(self, name, *, case_color=None, back=False):
        cover = Image.new("RGB", (540, 760), self.RED)
        return build_box_model(
            cover, cover if back else None, CASE_TYPES[name], title="Game",
            serial="", platform="PS5", spine_color=(200, 0, 0),
            case_color=case_color, spine_left_offset=0, spine_right_offset=0,
            full_cover=False, show_texture=False,
        )

    def _rim_px(self, face, name):
        return round(KEEP_RIM_MM * face.height / CASE_TYPES[name].height)

    def test_every_keep_case_has_a_rim(self):
        names = [*TABLE, "PS2 Platinum Case (PAL)", "PS2 DVD Case (clear)"]
        for name in names:
            with self.subTest(case=name):
                self.assertEqual(CASE_TYPES[name].rim_mm, KEEP_RIM_MM)

    def test_boxes_and_jewel_cases_have_no_rim(self):
        for name in ("NES Cartridge Box", "SNES Cartridge Box", "Universal Cart Case",
                     "PS1 Jewel Case (PAL)", "CD Jewel Case"):
            with self.subTest(case=name):
                self.assertEqual(CASE_TYPES[name].rim_mm, 0)

    def test_front_rim_on_three_sides_only(self):
        name = "PS5 Blu-ray Case"
        front = self._model(name).front.convert("RGB")
        w, h = front.size
        self.assertEqual(front.getpixel((w // 2, 0)), BLUE_TINT)
        self.assertEqual(front.getpixel((w // 2, h - 1)), BLUE_TINT)
        self.assertEqual(front.getpixel((w - 1, h // 2)), BLUE_TINT)
        # The hinge side has no lip: the art runs to the spine.
        self.assertEqual(front.getpixel((0, h // 2)), self.RED)
        rim = self._rim_px(front, name)
        self.assertEqual(front.getpixel((w // 2, rim + 2)), self.RED)
        self.assertEqual(front.getpixel((w - rim - 3, h // 2)), self.RED)

    def test_back_rim_is_on_its_opening_side(self):
        """Seen from behind, the opening side is on the left."""
        back = self._model("PS5 Blu-ray Case", back=True).back.convert("RGB")
        w, h = back.size
        self.assertEqual(back.getpixel((0, h // 2)), BLUE_TINT)
        self.assertEqual(back.getpixel((w - 1, h // 2)), self.RED)

    def test_spine_rim_on_top_and_bottom_only(self):
        spine = self._model("PS5 Blu-ray Case").spine.convert("RGB")
        w, h = spine.size
        self.assertEqual(spine.getpixel((w // 2, 0)), BLUE_TINT)
        self.assertEqual(spine.getpixel((w // 2, h - 1)), BLUE_TINT)
        # Neither side has a lip: the spine's own art reaches both.
        self.assertNotEqual(spine.getpixel((0, h // 2)), BLUE_TINT)
        self.assertNotEqual(spine.getpixel((w - 1, h // 2)), BLUE_TINT)

    def test_art_is_shrunk_into_the_rim_not_cropped(self):
        """Marks narrower than the rim, at the top, bottom and far edges, all
        survive; drawing the lip over the art, or cropping, would lose them."""
        ct = CASE_TYPES["PS5 Blu-ray Case"]
        cover = Image.new("RGB", (540, 760), self.RED)
        cover.paste((0, 255, 0), (536, 0, 540, 760))
        cover.paste((0, 255, 0), (0, 0, 540, 4))
        cover.paste((0, 255, 0), (0, 756, 540, 760))
        framed = np.array(inset_in_rim(cover.convert("RGBA"), ct, None, "right"))
        rim = round(KEEP_RIM_MM * 760 / ct.height)
        inner = framed[rim:760 - rim, :540 - rim]
        for label, band in (("far", inner[100:-100, -2:]), ("top", inner[:2, 100:-100]),
                            ("bottom", inner[-2:, 100:-100])):
            with self.subTest(edge=label):
                self.assertTrue((band[..., 1] > band[..., 0]).all())

    def test_lip_has_an_inner_wall_in_shade(self):
        ct = CASE_TYPES["PS5 Blu-ray Case"]
        framed = inset_in_rim(Image.new("RGBA", (540, 760), (*self.RED, 255)), ct, None, "right")
        rim = round(KEEP_RIM_MM * 760 / ct.height)
        wall = framed.getpixel((270, rim - 1))[:3]
        self.assertEqual(wall, tuple(round(c * 0.6) for c in BLUE_TINT))

    def test_transparent_art_leaves_no_hole_in_the_frame(self):
        """A cover with clear corners: the case behind it is still solid."""
        ct = CASE_TYPES["PS5 Blu-ray Case"]
        clear = inset_in_rim(Image.new("RGBA", (540, 760), (0, 0, 0, 0)), ct, None, "right")
        self.assertEqual(np.array(clear)[..., 3].min(), 255)

    def test_a_tiny_face_keeps_its_plastic_colour(self):
        ct = CASE_TYPES["PS5 Blu-ray Case"]
        tiny = inset_in_rim(Image.new("RGBA", (40, 50), (*self.RED, 255)), ct, None, "right")
        self.assertEqual(tiny.getpixel((20, 0))[:3], BLUE_TINT)
        self.assertEqual(tiny.getpixel((20, 25))[:3], self.RED)
        # Too small for any art inside the lip: left alone, not blanked.
        sliver = Image.new("RGBA", (10, 2), (*self.RED, 255))
        self.assertIs(inset_in_rim(sliver, ct, None, "right"), sliver)

    def test_case_colour_paints_the_rim(self):
        front = self._model("PS5 Blu-ray Case", case_color=(9, 8, 7)).front.convert("RGB")
        self.assertEqual(front.getpixel((front.width // 2, 0)), (9, 8, 7))

    def test_a_box_keeps_its_art_to_the_edge(self):
        front = self._model("NES Cartridge Box").front.convert("RGB")
        self.assertEqual(front.getpixel((front.width // 2, 0)), self.RED)
        self.assertEqual(front.getpixel((front.width - 1, front.height // 2)), self.RED)

    def test_render_draws_the_rim_on_the_far_edge(self):
        """The flat render, front and back: the opening side reads as plastic."""
        cover = Image.new("RGB", (540, 760), self.RED)
        renderer = BoxRenderer(CASE_TYPES["PS5 Blu-ray Case"], angle=30, output_width=512,
                               show_reflection=False, show_shadow=False, show_texture=False)
        front = np.array(renderer.render(cover, title="Game", full_cover=False))
        back = np.array(renderer.render(cover, back_image=cover, view="back", title="Game",
                                        full_cover=False))
        for label, image, column in (("front", front, -3), ("back", back, 2)):
            with self.subTest(view=label):
                r, _, b, _ = image[image.shape[0] // 2, column]
                self.assertGreater(int(b), int(r))

    def test_render_frames_front_and_spine_with_the_case_colour(self):
        ct = CASE_TYPES["PS5 Blu-ray Case"]
        renderer = BoxRenderer(ct, angle=30, output_width=128, show_reflection=False,
                               show_shadow=False, show_texture=False)
        with patch("core.renderer.inset_in_rim", wraps=inset_in_rim) as framed:
            renderer.render(Image.new("RGB", (540, 760), self.RED), title="Game",
                            full_cover=False, case_color=(9, 8, 7))
        self.assertEqual([c.args[1:] + (c.kwargs["opening"],) for c in framed.call_args_list],
                         [(ct, (9, 8, 7), "right"), (ct, (9, 8, 7), None)])


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
