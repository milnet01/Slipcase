"""The Match RetroDB view: a level, true perspective camera (SLIP-0120)."""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PIL import Image
from PyQt6 import sip
from PyQt6.QtWidgets import QApplication

from core.case_types import CASE_TYPES
from core.config import Config
from core.renderer import (
    RETRODB_ANGLE,
    RETRODB_CAMERA_DISTANCE,
    BoxRenderer,
    visible_width_mm,
)
import ui.main_window as main_window
from ui.main_window import MainWindow
from ui.workers import AnimationWorker, BatchWorker

_app = QApplication.instance() or QApplication([])


def _silhouette(case_name, **kw):
    """Far-edge share, spine share, height over width, and both edge slopes."""
    args = dict(angle=RETRODB_ANGLE, camera_distance=RETRODB_CAMERA_DISTANCE,
                output_width=800, show_reflection=False, show_shadow=False,
                show_texture=False)
    args.update(kw)
    image = BoxRenderer(CASE_TYPES[case_name], **args).render(
        Image.new("RGB", (400, 560), (200, 40, 40)), title="Game")
    mask = np.asarray(image)[:, :, 3] > 128
    # A faint first or last column is not part of the box.
    mask = mask[:, np.where(mask.any(axis=0))[0]]
    top = mask.argmax(axis=0).astype(float)
    bottom = mask.shape[0] - mask[::-1].argmax(axis=0).astype(float)
    heights = bottom - top
    near = int(np.argmax(heights))
    xs = np.arange(near + 3, mask.shape[1] - 2)
    top_line = np.polyfit(xs, top[xs], 1)
    bottom_line = np.polyfit(xs, bottom[xs], 1)
    near_h = np.polyval(bottom_line, near) - np.polyval(top_line, near)
    far_h = (np.polyval(bottom_line, mask.shape[1] - 1)
             - np.polyval(top_line, mask.shape[1] - 1))
    return dict(far=far_h / near_h, spine=near / mask.shape[1],
                ratio=near_h / mask.shape[1], top=top_line[0],
                bottom=bottom_line[0], width=image.width)


class TestRetrodbCamera(unittest.TestCase):
    def test_a_dvd_case_matches_the_figures_measured_from_retrodb(self):
        """RetroDB's DVD renders: far edge 0.773, spine 0.09, ratio 2.02."""
        shape = _silhouette("PS2 DVD Case")
        self.assertAlmostEqual(shape["far"], 0.775, delta=0.01)
        self.assertAlmostEqual(shape["spine"], 0.09, delta=0.015)
        self.assertAlmostEqual(shape["ratio"], 2.02, delta=0.05)

    def test_the_camera_is_level(self):
        """The top falls as far as the bottom rises."""
        shape = _silhouette("PS2 DVD Case")
        self.assertAlmostEqual(shape["top"], -shape["bottom"], delta=0.01)
        self.assertGreater(shape["top"], 0.2)

    def test_a_level_camera_draws_no_top_or_bottom_face(self):
        with patch.object(BoxRenderer, "_render_faces") as faces:
            _silhouette("PS2 DVD Case")
        faces.assert_not_called()

    def test_nothing_is_drawn_see_through_across_the_cover(self):
        """The default view's bottom edge lines belong on its bottom face."""
        image = BoxRenderer(
            CASE_TYPES["PS2 DVD Case"], angle=RETRODB_ANGLE,
            camera_distance=RETRODB_CAMERA_DISTANCE, output_width=800,
            show_reflection=False, show_shadow=False, show_texture=False,
        ).render(Image.new("RGB", (400, 560), (200, 40, 40)), title="Game")
        column = np.asarray(image)[:, image.width * 2 // 3, 3]
        solid = np.where(column == 255)[0]
        # Resampling near the edges leaves a little under 255; a line is far less.
        self.assertGreater(column[solid[0]:solid[-1] + 1].min(), 240)

    def test_the_reflection_meets_the_box_at_its_far_edge(self):
        """The bottom edge climbs towards the far side; the reflection must
        climb with it, in both views."""
        for view, far in (("front", -6), ("back", 5)):
            with self.subTest(view=view):
                args = dict(angle=RETRODB_ANGLE, output_width=800,
                            camera_distance=RETRODB_CAMERA_DISTANCE,
                            show_shadow=False, show_texture=False)
                cover = Image.new("RGB", (400, 560), (200, 40, 40))
                case = CASE_TYPES["PS2 DVD Case"]
                bare = np.asarray(BoxRenderer(case, show_reflection=False, **args)
                                  .render(cover, cover, title="Game", view=view))[:, :, 3]
                full = np.asarray(BoxRenderer(case, show_reflection=True, **args)
                                  .render(cover, cover, title="Game", view=view))[:, :, 3]
                self.assertEqual(bare.shape[1], full.shape[1])
                for column in (far, bare.shape[1] // 2):
                    box_end = np.where(bare[:, column] > 128)[0][-1]
                    # Past the box's own soft edge, which fades over a few rows.
                    soft_edge = 4
                    below = np.where(full[box_end + soft_edge:, column] > 8)[0]
                    self.assertGreater(below.size, 0, "no reflection in that column")
                    self.assertLess(int(below[0]), bare.shape[0] * 0.03)

    def test_every_case_shape_keeps_the_far_edge(self):
        """RetroDB's far edge is the same on every box, whatever its width."""
        for name in ("PS1 Jewel Case (PAL)", "N64 Cartridge Box",
                     "Genesis Clamshell", "Game Boy Box"):
            with self.subTest(case=name):
                self.assertAlmostEqual(_silhouette(name)["far"], 0.775, delta=0.015)

    def test_the_box_is_framed_as_the_normal_view_frames_it(self):
        matched = _silhouette("PS2 DVD Case")["width"]
        normal = _silhouette("PS2 DVD Case", angle=30, camera_distance=None)["width"]
        self.assertAlmostEqual(matched, normal, delta=normal * 0.02)

    def test_the_faces_are_sized_for_the_view_through_the_camera(self):
        """Sized for the flat view they come out too small, then get scaled up."""
        case = CASE_TYPES["PS2 DVD Case"]
        renderer = BoxRenderer(case, angle=RETRODB_ANGLE,
                               camera_distance=RETRODB_CAMERA_DISTANCE)
        visible = visible_width_mm(case, RETRODB_ANGLE, RETRODB_CAMERA_DISTANCE)
        self.assertEqual(
            renderer._compute_box_dimensions(1000, RETRODB_ANGLE)["front_w"],
            int(case.width * 850 / visible))

    def test_the_normal_view_still_has_its_own_far_edge(self):
        """No camera_distance: the old shrink, which never reached 0.78."""
        self.assertGreater(
            _silhouette("PS2 DVD Case", angle=30, camera_distance=None)["far"], 0.85)

    def test_the_visible_width_counts_the_camera(self):
        case = CASE_TYPES["PS2 DVD Case"]
        self.assertLess(visible_width_mm(case, 35, RETRODB_CAMERA_DISTANCE),
                        visible_width_mm(case, 35))


class TestEveryExportUsesTheCamera(unittest.TestCase):
    def test_batch_passes_it_to_its_worker_processes(self):
        renderer = BoxRenderer(CASE_TYPES["PS2 DVD Case"], angle=RETRODB_ANGLE,
                               camera_distance=RETRODB_CAMERA_DISTANCE)
        with tempfile.TemporaryDirectory() as d:
            worker = BatchWorker([], d, renderer)
            self.addCleanup(worker.deleteLater)
        self.assertEqual(worker._renderer_kwargs["camera_distance"],
                         RETRODB_CAMERA_DISTANCE)

    def test_an_animation_draws_every_frame_with_it(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "spin.png")
            worker = AnimationWorker(
                case_type=CASE_TYPES["PS2 DVD Case"],
                front_image=Image.new("RGB", (200, 280), (200, 40, 40)),
                back_image=None, title="", serial="", platform="",
                spine_color=None, case_color=None, spine_left_offset=0,
                spine_right_offset=0, output_path=out, output_width=128,
                start_angle=20, end_angle=40, frame_count=2, frame_delay=50,
                bounce=False, fmt="APNG", show_reflection=False,
                show_shadow=False, background="transparent",
                camera_distance=RETRODB_CAMERA_DISTANCE,
            )
            errors = []
            worker.error.connect(errors.append)
            worker.run()
            self.assertEqual(errors, [])
            with Image.open(out) as first:
                first.seek(first.n_frames - 1)
                last_frame_alpha = np.asarray(first.convert("RGBA"))[:, :, 3]
        cols = np.where((last_frame_alpha > 128).any(axis=0))[0]
        heights = (last_frame_alpha[:, cols] > 128).sum(axis=0)
        self.assertLess(heights[-2] / heights.max(), 0.84)


class TestMatchRetrodbButton(unittest.TestCase):
    def _window(self, folder):
        window = MainWindow(Config(config_path=os.path.join(folder, "c.json")))
        self.addCleanup(sip.delete, window)
        return window

    def test_off_by_default_and_the_slider_rules(self):
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d)
            renderer = window._get_renderer()
        self.assertFalse(window.match_retrodb_btn.isChecked())
        self.assertIsNone(renderer.camera_distance)
        self.assertEqual(renderer.angle, window.angle_slider.value())

    def test_on_it_sets_the_camera_and_leaves_the_slider_value(self):
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d)
            window.angle_slider.setValue(45)
            window.match_retrodb_btn.setChecked(True)
            renderer = window._get_renderer()
            self.assertEqual(renderer.angle, RETRODB_ANGLE)
            self.assertEqual(renderer.camera_distance, RETRODB_CAMERA_DISTANCE)
            self.assertFalse(window.angle_slider.isEnabled())
            self.assertEqual(window.angle_label.text(), f"{RETRODB_ANGLE}°")

            window.match_retrodb_btn.setChecked(False)
            self.assertTrue(window.angle_slider.isEnabled())
            self.assertEqual(window.angle_slider.value(), 45)
            self.assertEqual(window.angle_label.text(), "45°")

    def test_the_button_reaches_an_animation_export(self):
        params = dict(fmt="APNG", output_width=128, start_angle=20, end_angle=40,
                      frame_count=2, frame_delay=50, bounce=False)
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d)
            window._front_image = Image.new("RGB", (40, 56))
            window.match_retrodb_btn.setChecked(True)
            with patch.object(main_window, "AnimationDialog") as dialog, \
                    patch.object(main_window.QFileDialog, "getSaveFileName",
                                 return_value=(os.path.join(d, "a.png"), "")), \
                    patch.object(main_window, "AnimationWorker") as worker:
                dialog.return_value.exec.return_value = dialog.DialogCode.Accepted
                dialog.return_value.get_params.return_value = params
                window._export_animation()
        self.assertEqual(worker.call_args.kwargs["camera_distance"],
                         RETRODB_CAMERA_DISTANCE)

    def test_the_setting_survives_a_restart(self):
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d)
            window.match_retrodb_btn.setChecked(True)
            window._save_state()
            again = self._window(d)
            self.assertTrue(again.match_retrodb_btn.isChecked())
            self.assertFalse(again.angle_slider.isEnabled())


if __name__ == "__main__":
    unittest.main()
