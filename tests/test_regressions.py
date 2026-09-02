"""Regression tests for defects found by the 2026-09-01 code review.

Each test locks one fixed defect. Named for the behaviour, not the finding,
so they stay readable once the review is forgotten.
"""

import json
import math
import os
import pathlib
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image

from core.case_types import CASE_TYPES, PLATFORM_CASE_MAP, get_case_for_platform
from core.config import Config
from core.image_utils import generate_reflection
from core.png_utils import save_optimized_png
from core.renderer import BoxRenderer
from ui.workers import unique_output_path


def _cover(width=700, height=1000):
    """A cover whose top and bottom halves differ, so a mirrored strip is
    identifiable."""
    img = Image.new("RGBA", (width, height), (255, 0, 0, 255))
    for y in range(height // 2, height):
        for x in range(width):
            img.putpixel((x, y), (0, 0, 255, 255))
    return img


class TestRenderAspectRatio(unittest.TestCase):
    """A render must keep the case's real-world proportions.

    The final downscale previously divided height by the supersample factor
    while pinning width to output_width, and the canvas is not
    output_width * supersample wide -- so every render came out 12-14% too
    wide.
    """

    def _expected_ratio(self, case, angle):
        a = math.radians(angle)
        visible_w = case.width * math.cos(a) + case.depth * math.sin(a)
        return visible_w / case.height

    def test_proportions_hold_across_output_widths(self):
        case = CASE_TYPES["DVD Case"]
        expected = self._expected_ratio(case, 30.0)
        for width in (512, 800, 1200):
            with self.subTest(output_width=width):
                out = BoxRenderer(
                    case_type=case, angle=30.0, output_width=width,
                    show_reflection=False, show_shadow=False, supersample=2,
                ).render(front_image=_cover(), title="T")
                actual = out.size[0] / out.size[1]
                # 5% tolerance: the top-face overhang legitimately adds height.
                self.assertAlmostEqual(actual / expected, 1.0, delta=0.05)

    def test_proportions_hold_across_case_types(self):
        for name in ("DVD Case", "Blu-ray Case", "CD Jewel Case"):
            with self.subTest(case=name):
                case = CASE_TYPES[name]
                out = BoxRenderer(
                    case_type=case, angle=30.0, output_width=512,
                    show_reflection=False, show_shadow=False, supersample=2,
                ).render(front_image=_cover(), title="T")
                ratio = (out.size[0] / out.size[1]) / self._expected_ratio(case, 30.0)
                self.assertAlmostEqual(ratio, 1.0, delta=0.05)

    def test_supersample_does_not_change_proportions(self):
        case = CASE_TYPES["DVD Case"]
        ratios = []
        for ss in (1, 2):
            out = BoxRenderer(
                case_type=case, angle=30.0, output_width=512,
                show_reflection=False, show_shadow=False, supersample=ss,
            ).render(front_image=_cover(), title="T")
            ratios.append(out.size[0] / out.size[1])
        self.assertAlmostEqual(ratios[0], ratios[1], delta=0.03)


class TestReflection(unittest.TestCase):
    """The reflection mirrors the BOTTOM of the image, not the top."""

    def test_reflection_takes_the_bottom_of_the_source(self):
        # Top half red, bottom half blue. The reflection sits directly under
        # the image, so its FIRST row must be the source's LAST row: blue.
        img = _cover(40, 100)
        refl = generate_reflection(img, height_fraction=0.25, start_opacity=1.0)
        r, g, b, _a = refl.getpixel((20, 0))
        self.assertGreater(b, r, "reflection starts with the top of the image")

    def test_reflection_is_not_blank_in_a_render(self):
        out = BoxRenderer(
            case_type=CASE_TYPES["DVD Case"], angle=30.0, output_width=512,
            show_reflection=True, show_shadow=False, supersample=2,
        ).render(front_image=_cover(), title="T")
        w, h = out.size
        strip = out.crop((0, int(h * 0.82), w, h))
        opaque = sum(1 for px in strip.convert("RGBA").getchannel("A").tobytes() if px > 0)
        self.assertGreater(opaque, 100, "reflection region is empty")


class TestBatchOutputPaths(unittest.TestCase):
    """Batch rendering must not overwrite anything."""

    def test_same_stem_from_different_folders_does_not_collide(self):
        out = pathlib.Path(tempfile.mkdtemp())
        first = unique_output_path(str(out), "cover", "/library/A/cover.png")
        pathlib.Path(first).write_bytes(b"x")
        second = unique_output_path(str(out), "cover", "/library/B/cover.png")
        self.assertNotEqual(first, second)

    def test_source_image_is_never_its_own_output(self):
        out = pathlib.Path(tempfile.mkdtemp())
        source = out / "cover.png"
        source.write_bytes(b"original")
        result = unique_output_path(str(out), "cover", str(source))
        self.assertNotEqual(pathlib.Path(result).resolve(), source.resolve())
        self.assertEqual(source.read_bytes(), b"original")


class TestConfigDurability(unittest.TestCase):
    """Credentials must survive a failed read and an interrupted write."""

    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.path = self.dir / "config.json"

    def test_config_file_is_owner_only(self):
        cfg = Config(config_path=self.path)
        cfg.set("api", "screenscraper", "password", "hunter2")
        cfg.save()
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_unreadable_config_is_never_overwritten(self):
        self.path.write_text('{"api": {"screenscraper": {"password": "REAL"')
        cfg = Config(config_path=self.path)
        self.assertTrue(cfg.load_failed)
        with self.assertRaises(OSError):
            cfg.save()
        self.assertIn("REAL", self.path.read_text())

    def test_empty_config_is_writable(self):
        # An empty file holds nothing to protect, so it is not a failed read.
        self.path.write_text("")
        cfg = Config(config_path=self.path)
        self.assertFalse(cfg.load_failed)
        cfg.set("api", "screenscraper", "username", "u")
        cfg.save()
        self.assertEqual(
            Config(config_path=self.path).get("api", "screenscraper", "username"), "u"
        )

    def test_non_utf8_config_does_not_raise(self):
        self.path.write_bytes(b"\xff\xfe\x00garbage")
        cfg = Config(config_path=self.path)
        self.assertTrue(cfg.load_failed)

    def test_save_leaves_no_temp_files(self):
        cfg = Config(config_path=self.path)
        cfg.save()
        self.assertEqual(list(self.dir.glob(".config-*")), [])


class TestPngExport(unittest.TestCase):
    def test_save_leaves_no_temp_files(self):
        d = pathlib.Path(tempfile.mkdtemp())
        target = d / "out.png"
        save_optimized_png(Image.new("RGBA", (8, 8), (1, 2, 3, 255)), str(target))
        self.assertTrue(target.exists())
        self.assertEqual(list(d.glob("*.tmp")), [])

    def test_compress_level_is_honoured(self):
        d = pathlib.Path(tempfile.mkdtemp())
        img = _cover(200, 200)
        fast, small = d / "fast.png", d / "small.png"
        save_optimized_png(img, str(fast), compress_level=0)
        save_optimized_png(img, str(small), compress_level=9)
        self.assertLess(small.stat().st_size, fast.stat().st_size)


class TestPlatformCaseMapping(unittest.TestCase):
    def test_each_platform_maps_to_exactly_one_case(self):
        seen: dict[str, str] = {}
        for case_name, case in CASE_TYPES.items():
            for platform in case.platforms:
                self.assertNotIn(
                    platform, seen,
                    f"{platform} claimed by both {seen.get(platform)} and {case_name}",
                )
                seen[platform] = case_name

    def test_pc_maps_to_the_dvd_case(self):
        self.assertEqual(get_case_for_platform("PC").name, "DVD Case")
        self.assertEqual(PLATFORM_CASE_MAP["PC"], "DVD Case")


if __name__ == "__main__":
    unittest.main()


class TestVersionIsNotDuplicated(unittest.TestCase):
    """The version is defined once and read everywhere it is shown.

    The About dialog previously spelled its own version literal, so a bump
    updated core/version.py and left the dialog behind. Asserted by source
    inspection rather than by opening the dialog: importing ui.main_window
    pulls in QtWidgets, which needs desktop libraries a CI runner may not
    have, and the defect is a duplicated literal rather than a runtime one.
    """

    def _main_window_source(self):
        root = pathlib.Path(__file__).resolve().parent.parent
        return (root / "ui" / "main_window.py").read_text(encoding="utf-8")

    def test_about_dialog_reads_the_shared_version(self):
        self.assertIn("from core.version import __version__", self._main_window_source())

    def test_about_dialog_spells_no_version_of_its_own(self):
        literals = re.findall(r"Slipcase v[0-9]", self._main_window_source())
        self.assertEqual(literals, [], f"hard-coded version in the About text: {literals}")

    def test_the_bump_recipe_points_at_the_version_module(self):
        root = pathlib.Path(__file__).resolve().parent.parent
        recipe = json.loads((root / ".claude" / "bump.json").read_text(encoding="utf-8"))
        self.assertEqual(recipe["version_source"], "core/version.py")
        self.assertEqual([f["path"] for f in recipe["files"]], ["core/version.py"])
