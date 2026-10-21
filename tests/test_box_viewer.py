"""Tests for ui/box_viewer.py and the model RenderWorker emits (SLIP-0104)."""

import math
import unittest
from unittest.mock import patch

from PIL import Image

from core.box_model import BoxModel
from core.case_types import CASE_TYPES
from core.renderer import BoxRenderer


def _destroy_now(widget) -> None:
    """Destroy a test's widget at once, on the main thread (see
    test_regressions._destroy_now for why deleteLater is not enough)."""
    from PyQt6 import sip
    sip.delete(widget)


def _model(back: bool = True) -> BoxModel:
    return BoxModel(
        case_type=CASE_TYPES["DVD Case"],
        top=(40, 40, 40), bottom=(40, 40, 40), edge=(40, 40, 40),
        front=Image.new("RGB", (135, 190), (200, 60, 60)),
        spine=Image.new("RGB", (14, 190), (60, 200, 60)),
        back=Image.new("RGB", (135, 190), (60, 60, 200)) if back else None,
    )


class _ViewerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def _viewer(self, model=None, angle=30.0):
        from ui.box_viewer import BoxViewer
        viewer = BoxViewer()
        self.addCleanup(_destroy_now, viewer)
        viewer.resize(300, 300)
        viewer.set_model(model if model is not None else _model(), angle=angle)
        return viewer


class TestVisibleFaces(_ViewerTest):

    def test_visible_faces(self):
        """INV-7."""
        viewer = self._viewer()
        for (yaw, pitch), faces in {
            (0, 0): {"front"},
            (30, 10): {"front", "spine", "top"},
            (180, 0): {"back"},
        }.items():
            with self.subTest(yaw=yaw, pitch=pitch):
                viewer.set_view(yaw, pitch)
                self.assertEqual(viewer.visible_faces(), faces)


class TestLimitsAndReset(_ViewerTest):

    def test_limits_and_reset(self):
        """INV-8."""
        viewer = self._viewer(angle=25.0)
        self.assertEqual((viewer.yaw, viewer.pitch), (25.0, 10.0))
        fitted = viewer.distance

        for _ in range(100):
            viewer.turn(0, 7)
        self.assertEqual(viewer.pitch, 89.0)
        viewer.turn(0, -1000)
        self.assertEqual(viewer.pitch, -89.0)

        viewer.zoom_by(1e-6)  # out
        self.assertEqual(viewer.distance, viewer.max_distance)
        viewer.zoom_by(1e6)  # in
        self.assertEqual(viewer.distance, viewer.min_distance)
        ct = CASE_TYPES["DVD Case"]
        half_diagonal = math.sqrt(ct.width ** 2 + ct.height ** 2 + ct.depth ** 2) / 2
        self.assertGreater(viewer.min_distance, half_diagonal,
                           "the camera can move inside the box")

        viewer.turn(400, 0)
        viewer.reset_view()
        self.assertEqual((viewer.yaw, viewer.pitch, viewer.distance),
                         (25.0, 10.0, fitted))


class TestModelFromWorker(_ViewerTest):

    def test_model_from_worker(self):
        """INV-9: RenderWorker builds the model; the viewer converts once."""
        from ui.workers import RenderWorker
        import ui.box_viewer as box_viewer

        worker = RenderWorker(
            renderer=BoxRenderer(CASE_TYPES["DVD Case"], output_width=128),
            front=Image.new("RGB", (135, 190), (200, 60, 60)), back=None,
            title="Game", serial="", platform="PS2", spine_color=None,
        )
        models = []
        worker.model_ready.connect(models.append)
        worker.run()
        self.assertEqual(len(models), 1)
        self.assertIsInstance(models[0], BoxModel)

        real = box_viewer._to_qimage
        with patch.object(box_viewer, "_to_qimage", side_effect=real) as convert:
            viewer = self._viewer(models[0])
            converted = convert.call_count
            self.assertEqual(converted, 2)  # front and spine; no back cover
            viewer.grab()
            viewer.grab()
            self.assertEqual(convert.call_count, converted)


class TestBackgroundTransparent(_ViewerTest):

    def test_background_transparent(self):
        """INV-12: the viewer paints nothing outside the box."""
        from PyQt6.QtCore import QPoint
        from PyQt6.QtGui import QColor, QImage, QRegion
        from PyQt6.QtWidgets import QWidget

        viewer = self._viewer()
        image = QImage(300, 300, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor(0, 0, 0, 0))
        viewer.render(image, QPoint(), QRegion(), QWidget.RenderFlag(0))
        for x, y in ((0, 0), (299, 0), (0, 299), (299, 299)):
            self.assertEqual(image.pixelColor(x, y).alpha(), 0, (x, y))
        self.assertGreater(image.pixelColor(150, 150).alpha(), 0)


if __name__ == "__main__":
    unittest.main()
