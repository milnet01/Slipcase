"""Unit tests for the 3D box renderer."""

import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from dataclasses import replace
from unittest.mock import patch

import numpy as np
from PIL import Image

from core.case_types import CASE_TYPES, get_case_for_platform, ALL_PLATFORMS
from core.renderer import BoxRenderer
from core.spine_generator import generate_spine
from core.image_utils import (
    extract_dominant_edge_color,
    generate_reflection,
    apply_directional_shading,
    apply_uniform_shading,
)
from core.config import Config


class TestCaseTypes(unittest.TestCase):
    def test_all_case_types_defined(self):
        self.assertGreaterEqual(len(CASE_TYPES), 15)

    def test_platform_mapping(self):
        self.assertEqual(get_case_for_platform("PS2").name, "PS2 DVD Case")
        self.assertEqual(get_case_for_platform("PS4").name, "PS4 Blu-ray Case")
        self.assertEqual(get_case_for_platform("Switch").name, "Switch Case")

    def test_all_platforms_list(self):
        self.assertIn("PS2", ALL_PLATFORMS)
        self.assertIn("NES", ALL_PLATFORMS)

    def test_case_aspect_ratio(self):
        dvd = CASE_TYPES["PS2 DVD Case"]
        self.assertAlmostEqual(dvd.aspect_ratio, 135 / 190, places=3)

    def test_case_depth_ratio(self):
        dvd = CASE_TYPES["PS2 DVD Case"]
        self.assertAlmostEqual(dvd.depth_ratio, 14 / 135, places=3)


class TestImageUtils(unittest.TestCase):
    def _make_test_image(self, w=200, h=300, color=(128, 64, 32)):
        img = Image.new("RGBA", (w, h), (*color, 255))
        return img

    def test_extract_dominant_edge_color(self):
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        color = extract_dominant_edge_color(img, edge="left")
        self.assertEqual(color[0], 255)
        self.assertEqual(color[1], 0)

    def test_generate_reflection(self):
        img = self._make_test_image()
        refl = generate_reflection(img, height_fraction=0.3)
        self.assertEqual(refl.mode, "RGBA")
        self.assertGreater(refl.size[1], 0)

    def test_apply_directional_shading(self):
        img = self._make_test_image()
        shaded = apply_directional_shading(img, direction="left", intensity=0.3)
        self.assertEqual(shaded.size, img.size)
        self.assertEqual(shaded.mode, "RGBA")

    def test_directional_shading_darkens_the_named_side(self):
        img = self._make_test_image(w=50, h=50, color=(200, 200, 200))
        for direction, dark, light in (
            ("left", (0, 25), (49, 25)), ("right", (49, 25), (0, 25)),
            ("top", (25, 0), (25, 49)), ("bottom", (25, 49), (25, 0)),
        ):
            shaded = apply_directional_shading(img, direction=direction, intensity=0.5)
            self.assertEqual(shaded.getpixel(dark)[0], 100, direction)
            self.assertEqual(shaded.getpixel(light)[0], 200, direction)

    def test_uniform_shading_clamps_intensity(self):
        # Above 1.0 the factor went negative and uint8 wrapped to bright.
        img = self._make_test_image(color=(200, 200, 200))
        self.assertEqual(apply_uniform_shading(img, 1.5).getpixel((0, 0))[:3], (0, 0, 0))
        self.assertEqual(apply_uniform_shading(img, -0.5).getpixel((0, 0))[:3],
                         (200, 200, 200))


class TestCaseTexture(unittest.TestCase):
    def test_every_case_type_gets_a_front_and_spine_texture(self):
        # The dispatch fell through to a fully transparent overlay for six
        # case types, silently (SLIP-0034). getbbox() is None only for an
        # image with nothing drawn on it.
        from core.case_texture import generate_front_texture, generate_spine_texture
        for name, case_type in CASE_TYPES.items():
            with self.subTest(case=name):
                front = generate_front_texture(case_type, 300, 420)
                spine = generate_spine_texture(case_type, 40, 420)
                self.assertIsNotNone(front.getbbox(), "front overlay is empty")
                self.assertIsNotNone(spine.getbbox(), "spine overlay is empty")


class TestSpineGenerator(unittest.TestCase):
    def _drawn_text(self, *args, **kwargs):
        """Each text generate_spine draws: {text: (font, colour)}."""
        import core.spine_generator as sg
        drawn = {}
        real = sg._render_rotated_text

        def spy(text, font, color):
            drawn[text] = (font, color)
            return real(text, font, color)

        with patch.object(sg, "_render_rotated_text", spy):
            generate_spine(*args, **kwargs)
        return drawn

    def test_generated_spine_prints_like_a_real_one(self):
        """SLIP-0118: capitals, the console spelled out, a bold legible serial."""
        import core.spine_generator as sg
        drawn = self._drawn_text("Time Crisis", 70, 880, platform="PS1", serial="SCES-00657")
        self.assertEqual(set(drawn), {"PlayStation", "TIME CRISIS", "SCES", "00657"})
        self.assertEqual(drawn["TIME CRISIS"][1], (255, 255, 255, 255))
        self.assertIs(drawn["SCES"][0], drawn["00657"][0], "one serial size")
        for part in ("SCES", "00657"):
            self.assertEqual(drawn[part][1][3], sg._SERIAL_ALPHA)
            self.assertIs(drawn[part][0], sg._get_font(drawn[part][0].size, bold=True), "bold")
        self.assertGreater(sg._SERIAL_ALPHA, 200, "not faded")

    def test_every_playstation_spells_its_name(self):
        for platform, name in (("PS2", "PlayStation 2"), ("PS3", "PlayStation 3"),
                               ("PS4", "PlayStation 4"), ("PS5", "PlayStation 5")):
            with self.subTest(platform=platform):
                self.assertIn(name, self._drawn_text("A", 70, 880, platform=platform))
        self.assertIn("GAMECUBE", self._drawn_text("A", 70, 880, platform="GameCube"))

    def test_serial_font_fits_its_widest_part(self):
        """SLIP-0118: a serial's parts share a size, fitted to the part that
        draws widest. Equal letter counts hid "MWMW" behind "1234"."""
        drawn = self._drawn_text("A", 70, 880, platform="PS1", serial="1234-MWMW")
        font = drawn["MWMW"][0]
        bbox = font.getbbox("MWMW")
        self.assertLess(bbox[2] - bbox[0], int(880 * .08) // 2)

    def test_short_title_keeps_a_printed_size(self):
        """SLIP-0118: a short title takes about half the spine's width: not the
        largest size that fits, and not small print."""
        spine = np.asarray(generate_spine("Go", 70, 880, platform="PS1"))
        body = spine[200:800, :, :3].max(axis=2) > 128
        columns = np.flatnonzero(body[:, 2:-2].any(axis=0))
        self.assertLessEqual(columns[-1] - columns[0] + 1, 35)
        self.assertGreaterEqual(columns[-1] - columns[0] + 1, 20)

    def test_small_render_keeps_text_in_its_zone(self):
        """SLIP-0118: at the smallest font a long name is scaled down, not cut
        off at the strip's ends or painted over the title."""
        height = 190
        spine = np.asarray(generate_spine("A", 12, height, platform="PS2"))
        strip_end = int(height * .15)
        text = spine[..., :3].max(axis=2) > 128
        self.assertFalse(text[0, 2:-2].any(), "cut off at the top")
        self.assertFalse(text[strip_end - 1, 2:-2].any(), "cut off at the foot")
        long_title = "A Very Long Game Title Indeed: The Sequel Part Two Edition"
        spine = np.asarray(generate_spine(long_title, 12, height))
        self.assertFalse((spine[-1, 2:-2, :3].max(axis=1) > 128).any(), "off the spine")

    def test_black_spines_draw_black(self):
        """SLIP-0118: no reference GameCube spine is purple, no PS1 one grey."""
        for platform in ("PS1", "GameCube"):
            with self.subTest(platform=platform):
                spine = np.asarray(generate_spine("", 70, 880, platform=platform))
                self.assertEqual(tuple(spine[500, 30, :3]), (0, 0, 0), "body")
                self.assertEqual(tuple(spine[3, 3, :3]), (0, 0, 0), "brand strip")

    def test_generate_spine_basic(self):
        spine = generate_spine("Test Game", spine_width=30, spine_height=400)
        self.assertEqual(spine.size, (30, 400))
        self.assertEqual(spine.mode, "RGBA")

    def test_generate_spine_with_platform(self):
        spine = generate_spine("My Game", spine_width=25, spine_height=350, platform="PS4")
        self.assertEqual(spine.size, (25, 350))

    def test_generate_spine_custom_color(self):
        spine = generate_spine("Custom", spine_width=30, spine_height=400,
                              bg_color=(255, 0, 0))
        self.assertEqual(spine.size, (30, 400))


class TestRenderer(unittest.TestCase):
    def _make_cover(self, w=400, h=560):
        img = Image.new("RGBA", (w, h), (50, 100, 200, 255))
        return img

    def test_basic_render(self):
        case_type = CASE_TYPES["PS2 DVD Case"]
        renderer = BoxRenderer(
            case_type=case_type,
            angle=30,
            output_width=256,
            show_reflection=False,
            show_shadow=False,
            supersample=1,
        )
        result = renderer.render(self._make_cover(), title="Test Game")
        self.assertEqual(result.mode, "RGBA")
        self.assertGreater(result.size[0], 0)
        self.assertGreater(result.size[1], 0)

    def test_render_with_effects(self):
        case_type = CASE_TYPES["PS3 Blu-ray Case"]
        renderer = BoxRenderer(
            case_type=case_type,
            angle=25,
            output_width=512,
            show_reflection=True,
            show_shadow=True,
            supersample=2,
        )
        result = renderer.render(self._make_cover(), title="Effect Test")
        self.assertEqual(result.mode, "RGBA")

    def test_render_different_case_types(self):
        cover = self._make_cover()
        for name, case_type in CASE_TYPES.items():
            renderer = BoxRenderer(
                case_type=case_type,
                angle=30,
                output_width=128,
                show_reflection=False,
                show_shadow=False,
                supersample=1,
            )
            result = renderer.render(cover, title=name)
            self.assertEqual(result.mode, "RGBA", f"Failed for {name}")

    def test_shadow_fades_out_instead_of_being_cut_off(self):
        # The shadow was placed 2x its blur too far right and down, past the
        # canvas edge, so the render's outer column and row held it at full
        # strength -- a square cut (SLIP-0032). A soft shadow fades to near
        # nothing at the edge. Full strength is _SHADOW_OPACITY * 255 = 102.
        import numpy as np
        for name in ("PS2 DVD Case", "Game Boy Box"):
            for angle in (5, 30, 60):
                renderer = BoxRenderer(
                    case_type=CASE_TYPES[name],
                    angle=angle,
                    output_width=512,
                    show_reflection=False,
                    show_shadow=True,
                    show_texture=False,
                )
                alpha = np.array(renderer.render(self._make_cover()))[:, :, 3]
                with self.subTest(case=name, angle=angle):
                    self.assertLess(alpha[:, -1].max(), 20)
                    self.assertLess(alpha[-1, :].max(), 20)

    def test_render_saves_as_png(self):
        case_type = CASE_TYPES["Switch Case"]
        renderer = BoxRenderer(
            case_type=case_type,
            angle=30,
            output_width=256,
            show_reflection=True,
            show_shadow=True,
            supersample=1,
        )
        result = renderer.render(self._make_cover(), title="Save Test")
        # A folder, not NamedTemporaryFile: Windows will not let a second
        # writer open a file the first still holds open.
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "save.png")
            result.save(path, "PNG")
            with Image.open(path) as saved:
                self.assertEqual(saved.mode, "RGBA")

    def test_render_ignores_shape(self):
        """SLIP-0125 INV-7: the still render does not use the shape."""
        ps5 = CASE_TYPES["PS5 Blu-ray Case"]
        self.assertIsNotNone(ps5.shape)
        out = [np.array(BoxRenderer(case_type=case, output_width=200).render(
                   self._make_cover(), title="Shape"))
               for case in (ps5, replace(ps5, shape=None))]
        self.assertTrue(np.array_equal(out[0], out[1]))


    def test_loaded_spine_picture_is_drawn(self):
        """A loaded spine picture replaces the generated spine in the still
        render (SLIP-0129): a green spine turns the left of the box green."""
        renderer = BoxRenderer(CASE_TYPES["PS2 DVD Case"], angle=30,
                               output_width=300, show_texture=False,
                               show_reflection=False, show_shadow=False)
        red = Image.new("RGB", (270, 380), (220, 0, 0))

        def spine_green(**kw) -> float:
            out = np.asarray(renderer.render(red, title="Game", full_cover=False,
                                             **kw).convert("RGBA")).astype(int)
            cols = np.nonzero(out[:, :, 3].max(axis=0) > 0)[0]
            # At 30 degrees the spine is about 6% of the box's width.
            band = out[:, cols[0]:cols[0] + max(2, len(cols) // 25)]
            band = band[band[:, :, 3] > 0]
            return float((band[:, 1] - band[:, 0]).mean())

        green = Image.new("RGB", (20, 380), (0, 220, 0))
        self.assertGreater(spine_green(spine_image=green), 50)
        self.assertLess(spine_green(), 50)


class TestConfig(unittest.TestCase):
    def test_config_defaults(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=True) as f:
            cfg = Config(config_path=f.name)
            self.assertEqual(cfg.get("rendering", "angle"), 30.0)
            self.assertEqual(cfg.get("rendering", "output_width"), 512)
            self.assertTrue(cfg.get("rendering", "reflection"))

    def test_config_set_and_get(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=True) as f:
            cfg = Config(config_path=f.name)
            cfg.set("rendering", "angle", 45.0)
            self.assertEqual(cfg.get("rendering", "angle"), 45.0)

    def test_config_save_load(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            cfg = Config(config_path=path)
            cfg.set("api", "screenscraper", "username", "testuser")
            cfg.save()

            cfg2 = Config(config_path=path)
            self.assertEqual(cfg2.get("api", "screenscraper", "username"), "testuser")
        finally:
            os.unlink(path)


class TestConfigVersion(unittest.TestCase):
    """The settings file carries a version, and an older file is upgraded
    step by step on load (SLIP-0042)."""

    def _write(self, data):
        import json
        d = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(d))
        path = os.path.join(d, "config.json")
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def _saved(self, path):
        import json
        with open(path) as f:
            return json.load(f)

    def test_a_file_without_a_version_is_stamped_current_on_save(self):
        from core import config as config_mod
        path = self._write({"rendering": {"angle": 40.0}})
        cfg = Config(config_path=path)
        self.assertEqual(cfg.get("rendering", "angle"), 40.0)
        cfg.save()
        self.assertEqual(self._saved(path)["version"], config_mod.CONFIG_VERSION)

    def test_a_newer_file_keeps_its_version(self):
        # Saving from an older app must not mark the file as older than it is.
        from core import config as config_mod
        newer = config_mod.CONFIG_VERSION + 5
        path = self._write({"version": newer, "future": {"key": 1}})
        cfg = Config(config_path=path)
        cfg.save()
        saved = self._saved(path)
        self.assertEqual(saved["version"], newer)
        self.assertEqual(saved["future"], {"key": 1})

    def test_each_upgrade_step_runs_in_order_on_the_stored_values(self):
        from unittest.mock import patch
        from core import config as config_mod
        steps = []

        def step(n):
            def run(data):
                steps.append(n)
                data.setdefault("rendering", {})["angle"] = float(n)
                return data
            return run

        path = self._write({"version": 1, "rendering": {"angle": 10.0}})
        with patch.object(config_mod, "CONFIG_VERSION", 4), \
                patch.object(config_mod, "_MIGRATIONS", {n: step(n) for n in range(4)}):
            cfg = Config(config_path=path)
        self.assertEqual(steps, [1, 2, 3])
        self.assertEqual(cfg.get("rendering", "angle"), 3.0)
        self.assertEqual(cfg.get("version"), 4)

    def test_a_file_that_is_not_a_settings_object_is_not_overwritten(self):
        path = self._write([1, 2, 3])
        cfg = Config(config_path=path)
        self.assertTrue(cfg.load_failed)
        with self.assertRaises(OSError):
            cfg.save()


if __name__ == "__main__":
    unittest.main()
