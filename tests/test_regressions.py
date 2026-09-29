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
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

from core.case_types import CASE_TYPES, PLATFORM_CASE_MAP, get_case_for_platform
from core.config import DEFAULT_CONFIG, Config
from core.image_utils import apply_directional_shading, generate_reflection
from core.png_utils import save_optimized_png
from core.spine_generator import CASE_COLORS_ERROR, _load_case_colors
from core.renderer import MAX_OUTPUT_WIDTH, BoxRenderer
from ui.main_window import MainWindow
from ui.workers import unique_output_path


def _cover(width=700, height=1000):
    """A cover whose top and bottom halves differ, so a mirrored strip is
    identifiable."""
    img = Image.new("RGBA", (width, height), (255, 0, 0, 255))
    for y in range(height // 2, height):
        for x in range(width):
            img.putpixel((x, y), (0, 0, 255, 255))
    return img


def _destroy_now(widget) -> None:
    """Destroy a test's Qt widget at once, on this (the main) thread.

    deleteLater() needs an event loop these tests never run, so the widget
    lingered until the garbage collector freed it -- its signal lambdas form
    reference cycles -- and the collector can run on a render worker thread.
    A Qt widget destroyed off the GUI thread crashed the whole test run under
    some shuffled orders.
    """
    from PyQt6 import sip
    sip.delete(widget)


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



class TestCaseColoursDegradeGracefully(unittest.TestCase):
    """A damaged colour file must not stop the application starting.

    The table is read at import, before any window exists, so a bare
    json.load meant a truncated file raised during import with no in-app
    route to recovery; a missing file left the table empty and every spine
    fell back to grey with nothing said (SLIP-0053).
    """

    def test_a_good_file_loads_with_no_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "case_colors.json"
            path.write_text('{"PS2": {"brand": "#003791"}}', encoding="utf-8")
            colors, error = _load_case_colors(path)
        self.assertEqual(colors, {"PS2": {"brand": "#003791"}})
        self.assertIsNone(error)

    def test_a_truncated_file_reports_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "case_colors.json"
            path.write_text('{"PS2": {"brand": "#0037', encoding="utf-8")
            colors, error = _load_case_colors(path)
        self.assertEqual(colors, {})
        self.assertIsNotNone(error)

    def test_a_missing_file_reports_instead_of_going_quiet(self):
        with tempfile.TemporaryDirectory() as d:
            colors, error = _load_case_colors(pathlib.Path(d) / "absent.json")
        self.assertEqual(colors, {})
        self.assertIn("missing", error)

    def test_the_shipped_file_actually_loads(self):
        self.assertIsNone(CASE_COLORS_ERROR, "resources/case_colors.json is unreadable")

class TestPersistedKeysAreDeclared(unittest.TestCase):
    """Every ui key the window writes has a declared default.

    ui.auto_filename and ui.last_export_directory were written by
    main_window and appeared in neither DEFAULT_CONFIG nor the STANDARDS
    schema. Harmless at runtime, because every read passes a default -- but
    a setting nothing declares is a setting nobody can find (SLIP-0076).
    """

    def test_the_window_writes_no_undeclared_ui_key(self):
        root = pathlib.Path(__file__).resolve().parent.parent
        source = (root / "ui" / "main_window.py").read_text(encoding="utf-8")
        written = set(re.findall(r'config\.set\(\s*"ui",\s*"([a-z_]+)"', source))
        self.assertTrue(written, "found no ui keys; the search pattern has gone stale")
        undeclared = sorted(written - set(DEFAULT_CONFIG["ui"]))
        self.assertEqual(undeclared, [], f"persisted but undeclared: {undeclared}")

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


class TestExportBaseName(unittest.TestCase):
    """One derivation, and a filesystem root no longer produces a blank name.

    The name was derived at three call sites and only one guarded an empty
    parent folder, so an image loaded from a drive root exported as
    " 3D Boxart.png" (SLIP-0063). Called against a stand-in rather than a real
    window: the logic reads three widgets and building the whole UI to check
    it would test Qt rather than the rule.
    """

    def _window(self, auto, path, title):
        stand_in = SimpleNamespace(
            auto_filename_check=SimpleNamespace(isChecked=lambda: auto),
            _front_image_path=path,
            title_input=SimpleNamespace(text=lambda: title),
        )
        return MainWindow._export_base_name(stand_in, "Untitled")

    def test_auto_filename_prefers_the_source_folder(self):
        self.assertEqual(
            self._window(True, "/games/Chrono Trigger/front.png", ""),
            "Chrono Trigger",
        )

    def test_a_file_at_a_filesystem_root_falls_through(self):
        # "/front.png".parent.name is "", which used to be used verbatim.
        self.assertEqual(self._window(True, "/front.png", ""), "front")

    def test_a_root_file_with_a_title_uses_the_title(self):
        self.assertEqual(self._window(True, "/front.png", "  Halo  "), "Halo")

    def test_the_title_wins_when_auto_filename_is_off(self):
        self.assertEqual(
            self._window(False, "/games/Chrono Trigger/front.png", "Chrono"),
            "Chrono",
        )

    def test_nothing_loaded_falls_back(self):
        self.assertEqual(self._window(False, None, ""), "Untitled")


class TestShadingRobustness(unittest.TestCase):
    """apply_directional_shading is public, and both holes were silent.

    An unrecognised direction returned the image unshaded with no error, and
    an intensity above 1.0 made the gradient factor negative, so the uint8
    cast wrapped to bright values instead of clamping to black (SLIP-0055).
    """

    def _flat(self):
        return Image.new("RGBA", (32, 32), (200, 200, 200, 255))

    def test_an_unrecognised_direction_is_refused(self):
        with self.assertRaises(ValueError):
            apply_directional_shading(self._flat(), direction="sideways")

    def test_every_documented_direction_is_accepted(self):
        for direction in ("left", "right", "top", "bottom"):
            with self.subTest(direction=direction):
                out = apply_directional_shading(self._flat(), direction=direction)
                self.assertEqual(out.size, (32, 32))

    def test_an_intensity_above_one_darkens_rather_than_wrapping(self):
        out = apply_directional_shading(self._flat(), direction="left", intensity=4.0)
        darkest = int(np.array(out)[:, :, 0].min())
        self.assertLessEqual(darkest, 5, "clamped intensity should reach near-black")


class TestReflectionAcceptsRgb(unittest.TestCase):
    """generate_reflection split() a 4-band image without saying it needed one.

    Every current caller passes RGBA, so this was latent -- but the function
    is public and its signature was silent about the requirement (SLIP-0056).
    """

    def test_an_rgb_image_is_converted_rather_than_raising(self):
        out = generate_reflection(Image.new("RGB", (40, 60), (10, 20, 30)))
        self.assertEqual(out.mode, "RGBA")

    def test_an_rgba_image_still_works(self):
        out = generate_reflection(Image.new("RGBA", (40, 60), (10, 20, 30, 255)))
        self.assertEqual(out.mode, "RGBA")


class TestDegenerateRenderIsRefused(unittest.TestCase):
    """A width too small to project raises something a caller can act on.

    Without the guard the numpy path raised LinAlgError("Singular matrix")
    and the OpenCV path produced a garbage matrix instead of failing. Not
    reachable from the spinner's minimum, but BoxRenderer takes any width and
    the batch and animation paths construct one directly (SLIP-0057).
    """

    def test_a_width_too_small_to_project_names_the_problem(self):
        renderer = BoxRenderer(CASE_TYPES["DVD Case"], output_width=1, angle=30)
        with self.assertRaises(ValueError) as caught:
            renderer.render(Image.new("RGBA", (700, 1000), (255, 0, 0, 255)))
        self.assertIn("too small", str(caught.exception))

    def test_a_usable_width_still_renders(self):
        renderer = BoxRenderer(CASE_TYPES["DVD Case"], output_width=64, angle=30)
        out = renderer.render(Image.new("RGBA", (700, 1000), (255, 0, 0, 255)))
        self.assertGreater(out.size[0], 1)


class TestOutputWidthIsBounded(unittest.TestCase):
    """A width beyond the documented range cannot exhaust memory.

    The spinner ran to 8192 and the renderer multiplies by the supersample
    factor, so the working canvas reached roughly 16k x 21k RGBA -- about
    1.4 GB per layer with several alive at once. Image.MAX_IMAGE_PIXELS
    guards decoding, not Image.new, so it never covered this (SLIP-0037).
    """

    def test_a_width_past_the_ceiling_is_clamped(self):
        renderer = BoxRenderer(CASE_TYPES["DVD Case"], output_width=8192)
        self.assertEqual(renderer.output_width, MAX_OUTPUT_WIDTH)

    def test_a_width_inside_the_range_is_untouched(self):
        for width in (128, 512, 1200, MAX_OUTPUT_WIDTH):
            with self.subTest(width=width):
                renderer = BoxRenderer(CASE_TYPES["DVD Case"], output_width=width)
                self.assertEqual(renderer.output_width, width)

    def test_the_ceiling_covers_every_documented_target(self):
        # STANDARDS.md section 4: RetroArch max 512px, LaunchBox 800-1200px.
        self.assertGreaterEqual(MAX_OUTPUT_WIDTH, 1200)


class TestWindowGeometry(unittest.TestCase):
    """The window crept by the title-bar height on every restart, and could
    reopen on a monitor that was gone (SLIP-0040)."""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def test_geometry_round_trips_through_the_config_value(self):
        from PyQt6.QtWidgets import QWidget
        from ui.main_window import _geometry_for_config, _restore_geometry
        first = QWidget()
        first.setGeometry(40, 60, 700, 500)
        value = _geometry_for_config(first)
        self.assertIsInstance(value, str)  # JSON-safe
        second = QWidget()
        self.assertTrue(_restore_geometry(second, value))
        self.assertEqual(second.size(), first.size())

    def test_a_bad_stored_value_is_ignored(self):
        from PyQt6.QtWidgets import QWidget
        from ui.main_window import _restore_geometry
        for value in (None, [10, 10, 800, 600], "not base64 !!", "", 42):
            with self.subTest(value=value):
                self.assertFalse(_restore_geometry(QWidget(), value))

    def test_the_old_rectangle_is_cleared_by_the_version_2_upgrade(self):
        import json
        from core.config import Config
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "config.json")
            with open(path, "w") as f:
                json.dump({"version": 1, "ui": {
                    "window_geometry": [10, 10, 800, 600], "theme": "Nord",
                }}, f)
            cfg = Config(config_path=path)
        self.assertIsNone(cfg.get("ui", "window_geometry"))
        self.assertEqual(cfg.get("ui", "theme"), "Nord")
        self.assertGreaterEqual(cfg.get("version"), 2)



class TestSpineRefinement(unittest.TestCase):
    """Stage 2 of spine detection (STANDARDS.md section 5)."""

    CASE = CASE_TYPES["DVD Case"]

    def _cover(self, h=400):
        # A full-cover canvas of the case's full-cover aspect ratio.
        from core.image_utils import _geometric_spine_bounds
        w = round(h * (2 * self.CASE.width + self.CASE.depth) / self.CASE.height)
        geo_left, geo_right, _ = _geometric_spine_bounds(w, h, self.CASE)
        return np.full((h, w, 3), 128, dtype=np.uint8), geo_left, geo_right

    def test_a_faint_edge_does_not_move_a_boundary_that_sees_no_detail(self):
        # geo_score is 0 on a uniform region, so "20% better" was cleared by
        # any non-zero score, however faint (SLIP-0058).
        from core.image_utils import detect_spine_bounds
        # Both steps move by the same amount so the 85-115% width check,
        # which would also reject the nudge, stays out of the way.
        arr, geo_left, geo_right = self._cover()
        arr[:, geo_left + 3:] += 3  # steps far below a real fold
        arr[:, geo_right + 3:] += 3
        bounds = detect_spine_bounds(Image.fromarray(arr), self.CASE)
        self.assertEqual(bounds, (geo_left, geo_right))

    def test_a_real_fold_near_the_estimate_is_still_found(self):
        from core.image_utils import detect_spine_bounds
        arr, geo_left, geo_right = self._cover()
        arr[:, geo_left + 3:geo_right + 3] = (200, 40, 40)  # spine panel
        arr[:, geo_right + 3:] = (40, 40, 200)  # front panel
        left, right = detect_spine_bounds(Image.fromarray(arr), self.CASE)
        self.assertLessEqual(abs(left - (geo_left + 3)), 1)
        self.assertLessEqual(abs(right - (geo_right + 3)), 1)

    def test_an_analysis_failure_falls_back_and_says_so(self):
        # A blanket except hid every failure, bugs included (SLIP-0054).
        from unittest.mock import patch
        from core import image_utils
        arr, geo_left, geo_right = self._cover()
        with patch.object(image_utils, "_refine_spine_bounds",
                          side_effect=ValueError("degenerate")), \
                self.assertLogs("core.image_utils", level="WARNING") as logs:
            bounds = image_utils.detect_spine_bounds(Image.fromarray(arr), self.CASE)
        self.assertEqual(bounds, (geo_left, geo_right))
        self.assertIn("degenerate", logs.output[0])

    def test_a_bug_in_the_analysis_is_not_swallowed(self):
        from unittest.mock import patch
        from core import image_utils
        arr, _, _ = self._cover()
        with patch.object(image_utils, "_refine_spine_bounds",
                          side_effect=TypeError("a real bug")):
            with self.assertRaises(TypeError):
                image_utils.detect_spine_bounds(Image.fromarray(arr), self.CASE)

    def test_a_search_window_with_no_room_keeps_the_estimate(self):
        # Handled directly, not by the catch: an empty window made
        # np.percentile raise.
        from core.image_utils import _refine_spine_bounds
        img = Image.new("RGB", (12, 40), (90, 90, 90))
        self.assertEqual(_refine_spine_bounds(img, 2, 9, 7), (2, 9))


class TestProgressBarOwnership(unittest.TestCase):
    """Batch and animation share one progress bar (SLIP-0059)."""

    def _window(self):
        from functools import partial
        from unittest.mock import MagicMock
        w = MagicMock()
        w._progress_owner = None
        w._start_progress = partial(MainWindow._start_progress, w)
        w._finish_progress = partial(MainWindow._finish_progress, w)
        return w

    def test_a_job_that_does_not_own_the_bar_leaves_it_visible(self):
        from unittest.mock import patch
        w = self._window()
        w._start_progress("batch", 10)
        w.progress_bar.hide.reset_mock()
        with patch("ui.main_window.QMessageBox"):
            MainWindow._on_anim_error(w, "boom")
            w.progress_bar.hide.assert_not_called()
            MainWindow._on_batch_done(w, 10)
        w.progress_bar.hide.assert_called_once()

    def test_animation_progress_sets_the_bar_to_the_workers_own_total(self):
        # The worker counts rendered frames; bounce reuses them, so the
        # file's frame count would leave the bar stuck halfway.
        w = self._window()
        MainWindow._on_anim_progress(w, 3, 12)
        w.progress_bar.setMaximum.assert_called_with(12)
        w.progress_bar.setValue.assert_called_with(3)


class TestWorkersGetTheirOwnImage(unittest.TestCase):
    """A worker thread must not share the window's PIL image (SLIP-0060)."""

    def test_render_worker_gets_a_copy_of_the_cover(self):
        from unittest.mock import MagicMock, patch
        w = MagicMock()
        cover = Image.new("RGB", (40, 60), (10, 20, 30))
        w._front_image = cover
        w._back_image = None
        w._reject_if_busy.return_value = False
        with patch("ui.main_window.RenderWorker") as worker_cls:
            MainWindow._generate(w)
        given = worker_cls.call_args.kwargs["front"]
        self.assertIsNot(given, cover)
        self.assertEqual(given.tobytes(), cover.tobytes())


class TestVisibleTextIsTranslatable(unittest.TestCase):
    """User-visible literals in the window builders go through tr()
    (SLIP-0041; the global Qt language standard makes it an idiom)."""

    BUILDERS = {"_build_menu", "_build_ui", "_build_left_panel",
                "_build_spine_adjustment", "_build_right_panel", "_build_statusbar"}
    CALLS = {"QAction", "QPushButton", "QLabel", "QGroupBox", "QCheckBox",
             "QRadioButton", "setToolTip", "setText", "setPlaceholderText",
             "setTitle", "setWindowTitle", "addMenu", "addRow", "setStatusTip",
             "showMessage", "setAccessibleName"}
    # Numbers the code overwrites at once; not text.
    NOT_TEXT = {"0 px", "30\u00b0"}

    def test_no_bare_literal_reaches_a_visible_text_call(self):
        import ast
        src = pathlib.Path(__file__).resolve().parent.parent / "ui" / "main_window.py"
        tree = ast.parse(src.read_text())
        bare = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef) and node.name in self.BUILDERS):
                continue
            for call in ast.walk(node):
                if not (isinstance(call, ast.Call) and call.args):
                    continue
                f = call.func
                name = getattr(f, "id", None) or getattr(f, "attr", "")
                arg = call.args[0]
                if (name in self.CALLS and isinstance(arg, ast.Constant)
                        and isinstance(arg.value, str) and arg.value.strip()
                        and arg.value not in self.NOT_TEXT):
                    bare.append(f"{node.name}:{call.lineno} {arg.value!r}")
        self.assertEqual(bare, [])


class TestFieldsAreNamedForScreenReaders(unittest.TestCase):
    """Every labelled field is linked to its label and carries a name a
    screen reader can announce (SLIP-0046)."""

    FIELDS = ("platform_combo", "case_combo", "title_input", "serial_input",
              "color_btn", "case_color_btn", "spine_left_slider",
              "spine_right_slider", "angle_slider", "width_spin", "bg_combo")

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def test_each_field_has_a_linked_label_and_an_accessible_name(self):
        from PyQt6.QtWidgets import QLabel
        with tempfile.TemporaryDirectory() as d:
            window = MainWindow(Config(config_path=os.path.join(d, "c.json")))
            self.addCleanup(_destroy_now, window)
            buddies = {id(lbl.buddy()) for lbl in window.findChildren(QLabel)
                       if lbl.buddy() is not None}
            for name in self.FIELDS:
                control = getattr(window, name)
                with self.subTest(field=name):
                    self.assertTrue(control.accessibleName(), "no accessible name")
                    self.assertIn(id(control), buddies, "no label is linked to it")

    def test_the_search_box_has_an_accessible_name(self):
        from ui.search_dialog import SearchDialog
        with tempfile.TemporaryDirectory() as d:
            dialog = SearchDialog(Config(config_path=os.path.join(d, "c.json")))
            self.addCleanup(_destroy_now, dialog)
            self.assertTrue(dialog.search_input.accessibleName())
            self.assertTrue(dialog.preview_label.wordWrap())


class TestSpineFontIsLoadedOnce(unittest.TestCase):
    """_fit_text's search parsed the font file on every probe (SLIP-0047)."""

    def test_repeat_spines_reuse_loaded_fonts(self):
        from unittest.mock import patch
        from PIL import ImageFont
        from core.spine_generator import generate_spine
        generate_spine(title="Warm Up", spine_width=60, spine_height=900)
        # Both loaders: which one runs depends on the fonts installed.
        with patch("core.spine_generator.ImageFont.truetype",
                   side_effect=ImageFont.truetype) as tt, \
                patch("core.spine_generator.ImageFont.load_default",
                      side_effect=ImageFont.load_default) as ld:
            for _ in range(5):
                generate_spine(title="Warm Up", spine_width=60, spine_height=900)
        self.assertEqual(tt.call_count + ld.call_count, 0, "fonts were parsed again")


class TestPreviewRescaleIsCoalesced(unittest.TestCase):
    """Every resize event re-scaled the full image on the GUI thread
    (SLIP-0047)."""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def test_a_burst_of_resizes_scales_once(self):
        import time
        from unittest.mock import patch
        from PyQt6.QtCore import QCoreApplication
        from ui.preview_widget import PreviewWidget
        # Patched before construction: the timer connects to the method then.
        with patch.object(PreviewWidget, "_update_display") as update:
            w = PreviewWidget()
            self.addCleanup(_destroy_now, w)
            w.set_image(Image.new("RGBA", (400, 600), (255, 0, 0, 255)))
            update.reset_mock()
            from PyQt6.QtCore import QSize
            from PyQt6.QtGui import QResizeEvent
            for size in range(300, 340):
                w.resizeEvent(QResizeEvent(QSize(size, size), QSize(size - 1, size - 1)))
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                QCoreApplication.processEvents()
                time.sleep(0.01)
        self.assertEqual(update.call_count, 1)


class TestSpineFontDiscovery(unittest.TestCase):
    """Fonts are found by name in the system font folders, not only at a
    few fixed Linux paths (SLIP-0070). On openSUSE, DejaVu lives at a path
    the old list did not name, so spines fell back to Pillow's font."""

    def setUp(self):
        from core import spine_generator
        self.sg = spine_generator
        self._saved = dict(spine_generator._font_path_cache)
        spine_generator._font_path_cache.clear()
        self.addCleanup(lambda: (spine_generator._font_path_cache.clear(),
                                 spine_generator._font_path_cache.update(self._saved)))

    def test_a_font_named_only_by_file_name_is_found(self):
        import glob
        from unittest.mock import patch
        found = sorted(glob.glob("/usr/share/fonts/**/*.ttf", recursive=True))
        if not found:
            self.skipTest("no TrueType fonts installed to search for")
        name = os.path.basename(found[0])
        with patch.dict(self.sg._FONT_CANDIDATES, {True: ["NoSuchFont.ttf", name]}):
            self.sg._get_font(12, bold=True)
        self.assertTrue(self.sg._font_path_cache[True])
        self.assertEqual(os.path.basename(self.sg._font_path_cache[True]), name)

    def test_nothing_found_still_falls_back_at_the_requested_size(self):
        from unittest.mock import patch
        with patch.dict(self.sg._FONT_CANDIDATES, {True: ["NoSuchFont.ttf"]}):
            font = self.sg._get_font(40, bold=True)
        self.assertIsNone(self.sg._font_path_cache[True])
        self.assertGreater(font.getbbox("Hg")[3], 20)


class TestSpineSliderStaysCheap(unittest.TestCase):
    """Each slider step re-ran the whole spine detector on the GUI thread,
    though its result does not depend on the offsets (SLIP-0067)."""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def _window_with_full_cover(self, d):
        case = CASE_TYPES["DVD Case"]
        h = 300
        w = round(h * (2 * case.width + case.depth) / case.height)
        window = MainWindow(Config(config_path=os.path.join(d, "c.json")))
        self.addCleanup(_destroy_now, window)
        window.case_combo.setCurrentText("DVD Case")
        window._set_front_image(Image.new("RGB", (w, h), (90, 120, 200)))
        return window

    def test_the_detector_runs_once_for_many_offsets(self):
        from unittest.mock import patch
        from core import image_utils
        import ui.main_window as mw
        real = image_utils.detect_spine_bounds
        with tempfile.TemporaryDirectory() as d:
            window = self._window_with_full_cover(d)
            # Counted wherever it is called from: the window's own import or
            # split_full_cover's.
            with patch.object(image_utils, "detect_spine_bounds", wraps=real) as a, \
                    patch.object(mw, "detect_spine_bounds", wraps=real) as b:
                window._spine_bounds = None
                for offset in range(-5, 6):
                    window.spine_left_slider.setValue(offset)
                    window._update_split_preview()
            self.assertEqual(a.call_count + b.call_count, 1)

    def test_a_slider_drag_updates_the_preview_once(self):
        import time
        from unittest.mock import patch
        from PyQt6.QtCore import QCoreApplication
        with tempfile.TemporaryDirectory() as d:
            window = self._window_with_full_cover(d)
            with patch.object(window, "_update_split_preview") as update:
                for offset in range(1, 30):
                    window.spine_left_slider.setValue(offset)
                deadline = time.monotonic() + 1.0
                while time.monotonic() < deadline:
                    QCoreApplication.processEvents()
                    time.sleep(0.01)
            self.assertEqual(update.call_count, 1)


class TestBatchHonoursCompressLevel(unittest.TestCase):
    """Batch saved every PNG at the default level, ignoring the
    rendering.compress_level setting (SLIP-0091)."""

    def test_both_batch_paths_pass_the_level_to_the_saver(self):
        from unittest.mock import patch
        import ui.workers as workers
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "Cover.png")
            Image.new("RGB", (100, 140), (200, 50, 50)).save(src)
            renderer = BoxRenderer(CASE_TYPES["DVD Case"], output_width=128)
            worker = workers.BatchWorker([src], d, renderer, compress_level=9)

            with patch("core.png_utils.save_optimized_png") as save:
                workers._render_single_image(worker._args_for(src))
            self.assertEqual(save.call_args.kwargs.get("compress_level"), 9)

            with patch.object(workers, "save_optimized_png") as save:
                worker._run_sequential(1)
            self.assertEqual(save.call_args.kwargs.get("compress_level"), 9)


class TestFullCoverCanBeOverruled(unittest.TestCase):
    """A landscape front-only image inside the full-cover aspect band was
    always split, two thirds discarded, with no way to say no (SLIP-0051)."""

    CASE = CASE_TYPES["DVD Case"]

    def _wide(self):
        h = 300
        w = round(h * (2 * self.CASE.width + self.CASE.depth) / self.CASE.height)
        return Image.new("RGB", (w, h), (90, 120, 200))

    def test_the_renderer_can_be_told_it_is_not_a_full_cover(self):
        from unittest.mock import patch
        import core.renderer as renderer_mod
        r = BoxRenderer(self.CASE, output_width=128)
        with patch.object(renderer_mod, "split_full_cover",
                          wraps=renderer_mod.split_full_cover) as split:
            r.render(self._wide(), full_cover=False)
            self.assertEqual(split.call_count, 0)
            r.render(self._wide())  # unset: detected as before
            self.assertEqual(split.call_count, 1)

    def test_unticking_the_box_reaches_the_render(self):
        from unittest.mock import patch
        from PyQt6.QtWidgets import QApplication
        # Kept: an application nobody references is freed at once.
        self._app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as d:
            window = MainWindow(Config(config_path=os.path.join(d, "c.json")))
            self.addCleanup(_destroy_now, window)
            window.case_combo.setCurrentText("DVD Case")
            window._set_front_image(self._wide())
            self.assertTrue(window.full_cover_check.isChecked())
            window.full_cover_check.setChecked(False)
            with patch("ui.main_window.RenderWorker") as worker_cls:
                window._generate()
            self.assertIs(worker_cls.call_args.kwargs.get("full_cover"), False)


class TestBackView(unittest.TestCase):
    """The box can be rendered from behind: back cover with the spine
    beside it (SLIP-0033, by the user's choice on 2026-09-29)."""

    CASE = CASE_TYPES["DVD Case"]
    RED, GREEN, BLUE = (220, 30, 30), (30, 200, 30), (30, 30, 220)

    def _wrap(self):
        # back | spine | front, at the case's full-cover proportions.
        from core.image_utils import _geometric_spine_bounds
        h = 400
        w = round(h * (2 * self.CASE.width + self.CASE.depth) / self.CASE.height)
        left, right, _ = _geometric_spine_bounds(w, h, self.CASE)
        arr = np.zeros((h, w, 3), dtype=np.uint8)
        arr[:, :left] = self.RED
        arr[:, left:right] = self.GREEN
        arr[:, right:] = self.BLUE
        return Image.fromarray(arr)

    def _render(self, **kw):
        r = BoxRenderer(self.CASE, output_width=300, show_reflection=False,
                        show_shadow=False, show_texture=False)
        return np.array(r.render(self._wrap(), **kw).convert("RGB")).astype(int)

    def _mostly(self, pixels, colour):
        return np.all(np.abs(pixels - colour) < 90, axis=-1).mean()

    def test_the_back_view_shows_the_back_with_the_spine_on_the_right(self):
        img = self._render(view="back")
        mid = img[img.shape[0] // 2]
        opaque = mid[mid.sum(axis=1) > 0]
        self.assertGreater(self._mostly(opaque, self.RED), 0.6)
        self.assertLess(self._mostly(opaque, self.BLUE), 0.05)
        right_edge = opaque[-max(3, len(opaque) // 20):]
        self.assertGreater(self._mostly(right_edge, self.GREEN), 0.5)

    def test_the_front_view_is_unchanged(self):
        img = self._render()
        mid = img[img.shape[0] // 2]
        opaque = mid[mid.sum(axis=1) > 0]
        self.assertGreater(self._mostly(opaque, self.BLUE), 0.6)
        self.assertGreater(self._mostly(opaque[:len(opaque) // 20], self.GREEN), 0.5)

    def test_a_loaded_back_cover_is_used_for_a_front_only_image(self):
        r = BoxRenderer(self.CASE, output_width=200, show_reflection=False,
                        show_shadow=False, show_texture=False)
        front = Image.new("RGB", (270, 380), self.BLUE)
        back = Image.new("RGB", (270, 380), self.RED)
        img = np.array(r.render(front, back_image=back, view="back").convert("RGB")).astype(int)
        mid = img[img.shape[0] // 2]
        self.assertGreater(self._mostly(mid[mid.sum(axis=1) > 0], self.RED), 0.6)

    def test_a_back_view_without_a_back_cover_says_so(self):
        r = BoxRenderer(self.CASE, output_width=200)
        with self.assertRaisesRegex(ValueError, "back cover"):
            r.render(Image.new("RGB", (270, 380), self.BLUE), view="back")


class TestBackViewChoice(unittest.TestCase):
    """The View choice is offered only when there is a back cover to show,
    and reaches the render (SLIP-0033)."""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def _window(self, d):
        window = MainWindow(Config(config_path=os.path.join(d, "c.json")))
        self.addCleanup(_destroy_now, window)
        window.case_combo.setCurrentText("DVD Case")
        window._set_front_image(Image.new("RGB", (270, 380), (30, 30, 220)))
        return window

    def test_no_back_cover_means_no_back_view(self):
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d)
            self.assertFalse(window.view_combo.isEnabled())

    def test_a_loaded_back_cover_allows_the_back_view_and_reaches_the_render(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d)
            window._set_back_image(Image.new("RGB", (270, 380), (220, 30, 30)))
            self.assertTrue(window.view_combo.isEnabled())
            window.view_combo.setCurrentIndex(1)
            with patch("ui.main_window.RenderWorker") as worker_cls:
                window._generate()
            self.assertEqual(worker_cls.call_args.kwargs.get("view"), "back")
            window._clear_back()
            self.assertFalse(window.view_combo.isEnabled())
            self.assertEqual(window.view_combo.currentIndex(), 0)

if __name__ == "__main__":
    unittest.main()


class TestConfigDirectoryFollowsXdg(unittest.TestCase):
    """The config directory honours XDG_CONFIG_HOME (SLIP-0050, STANDARDS.md
    § 7): an absolute value is used, and an unset, empty or relative one falls
    back to ~/.config. The single-instance lock's fallback is the same
    directory, so the two cannot drift apart."""

    def _dir_with(self, value):
        from unittest.mock import patch
        from core.config import config_dir
        env = dict(os.environ)
        env.pop("XDG_CONFIG_HOME", None)
        if value is not None:
            env["XDG_CONFIG_HOME"] = value
        with patch.dict(os.environ, env, clear=True):
            return config_dir()

    def test_an_absolute_value_is_used(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self._dir_with(d), pathlib.Path(d) / "slipcase")

    def test_unset_empty_or_relative_falls_back(self):
        fallback = pathlib.Path.home() / ".config" / "slipcase"
        for value in (None, "", "relative/dir"):
            with self.subTest(value=value):
                self.assertEqual(self._dir_with(value), fallback)

    def test_the_lock_fallback_is_the_config_directory(self):
        from unittest.mock import patch
        import ui.single_instance as si
        with tempfile.TemporaryDirectory() as d, \
                patch.dict(os.environ, {"XDG_CONFIG_HOME": d}), \
                patch.object(si.QStandardPaths, "writableLocation", return_value=""):
            self.assertEqual(si.default_runtime_dir(), os.path.join(d, "slipcase"))


class TestLeftColumnFitsASmallScreen(unittest.TestCase):
    """With a full cover loaded, the left column's minimum height outgrew an
    800-pixel window, so Qt squashed the spine panel: "Reset to Auto" was
    clipped and the split thumbnails were cut off (SLIP-0095). The column
    now scrolls instead, so it no longer sets the window's minimum height."""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def test_the_window_fits_800_pixels_with_the_spine_panel_shown(self):
        with tempfile.TemporaryDirectory() as d:
            window = MainWindow(Config(config_path=os.path.join(d, "c.json")))
            self.addCleanup(_destroy_now, window)
            window.spine_adjust_group.show()
            self.assertLessEqual(window.minimumSizeHint().height(), 800)
