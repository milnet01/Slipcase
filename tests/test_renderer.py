"""Unit tests for the 3D box renderer."""

import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from PIL import Image

from core.case_types import CASE_TYPES, get_case_for_platform, ALL_PLATFORMS
from core.renderer import BoxRenderer
from core.spine_generator import generate_spine
from core.image_utils import (
    extract_dominant_edge_color,
    generate_reflection,
    apply_directional_shading,
)
from core.config import Config


class TestCaseTypes(unittest.TestCase):
    def test_all_case_types_defined(self):
        self.assertGreaterEqual(len(CASE_TYPES), 15)

    def test_platform_mapping(self):
        self.assertEqual(get_case_for_platform("PS2").name, "DVD Case")
        self.assertEqual(get_case_for_platform("PS4").name, "Blu-ray Case")
        self.assertEqual(get_case_for_platform("Switch").name, "Switch Case")

    def test_all_platforms_list(self):
        self.assertIn("PS2", ALL_PLATFORMS)
        self.assertIn("NES", ALL_PLATFORMS)

    def test_case_aspect_ratio(self):
        dvd = CASE_TYPES["DVD Case"]
        self.assertAlmostEqual(dvd.aspect_ratio, 135 / 190, places=3)

    def test_case_depth_ratio(self):
        dvd = CASE_TYPES["DVD Case"]
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


class TestSpineGenerator(unittest.TestCase):
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
        case_type = CASE_TYPES["DVD Case"]
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
        case_type = CASE_TYPES["Blu-ray Case"]
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
        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as f:
            result.save(f.name, "PNG")
            saved = Image.open(f.name)
            self.assertEqual(saved.mode, "RGBA")


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


if __name__ == "__main__":
    unittest.main()
