"""Tests for core/box_file.py: the box file RetroDB loads (SLIP-0104)."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

import core.box_file as box_file
from core.box_file import BoxFileError, box_paths, read_box_file, write_box_file
from core.box_model import BoxModel, build_box_model
from core.case_types import CASE_TYPES
from core.version import __version__


def _noise(w: int, h: int, seed: int, mode: str = "RGB") -> Image.Image:
    rng = np.random.default_rng(seed)
    bands = len(mode)
    arr = rng.integers(0, 256, (h, w, bands), dtype=np.uint8)
    return Image.fromarray(arr, mode)


def _model(back: bool = True) -> BoxModel:
    return BoxModel(
        case_type=CASE_TYPES["PS2 DVD Case"],
        top=(0x1C, 0x2B, 0xAA), bottom=(1, 2, 3), edge=(0xFF, 0xEE, 0x0D),
        front=_noise(135, 190, 1), spine=_noise(14, 190, 2),
        back=_noise(135, 190, 3) if back else None,
    )


def _jewel_model() -> BoxModel:
    """A CD Jewel Case model from a red booklet, so art-sampled colours show."""
    return build_box_model(
        Image.new("RGB", (240, 240), (220, 20, 20)), None, CASE_TYPES["CD Jewel Case"],
        title="Game", serial="", platform="Saturn", spine_color=None,
        case_color=None, spine_left_offset=0, spine_right_offset=0,
        full_cover=None, show_texture=True,
    )


class TestWriting(unittest.TestCase):

    def test_written_file_matches_schema(self):
        """INV-1."""
        for with_back in (True, False):
            with self.subTest(back=with_back), tempfile.TemporaryDirectory() as d:
                path = write_box_file(_model(with_back), d, "Game")
                self.assertEqual(path, os.path.join(d, "Game.box.json"))
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                self.assertEqual(data, {
                    "format": "slipcase-box",
                    "version": 1,
                    "generator": f"Slipcase {__version__}",
                    "case": {"name": "PS2 DVD Case", "width_mm": 135,
                             "height_mm": 190, "depth_mm": 14},
                    "colours": {"top": "#1C2BAA", "bottom": "#010203",
                                "edge": "#FFEE0D"},
                    "faces": {"front": "Game.front.png", "spine": "Game.spine.png",
                              "back": "Game.back.png" if with_back else None,
                              "edge": None, "top": None, "bottom": None},
                })
                expected = {"Game.box.json", "Game.front.png", "Game.spine.png"}
                if with_back:
                    expected.add("Game.back.png")
                self.assertEqual(set(os.listdir(d)), expected)

    def test_box_paths(self):
        self.assertEqual(box_paths("/out", "G"), [
            os.path.join("/out", "G.box.json"), os.path.join("/out", "G.front.png"),
            os.path.join("/out", "G.spine.png"), os.path.join("/out", "G.back.png"),
            os.path.join("/out", "G.edge.png"), os.path.join("/out", "G.top.png"),
            os.path.join("/out", "G.bottom.png"),
        ])

    def test_top_and_bottom_faces(self):
        """SLIP-0110: a PAL PS1 box writes its moulded top and bottom; a box
        without them writes null, and a file without the keys still reads."""
        pal = build_box_model(
            Image.new("RGB", (240, 240), (220, 20, 20)), None,
            CASE_TYPES["PS1 Jewel Case (PAL)"], title="Game", serial="",
            platform="PS1", spine_color=None, case_color=None,
            spine_left_offset=0, spine_right_offset=0, full_cover=None,
            show_texture=True,
        )
        with tempfile.TemporaryDirectory() as d:
            path = write_box_file(pal, d, "Game")
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual((data["faces"]["top"], data["faces"]["bottom"]),
                             ("Game.top.png", "Game.bottom.png"))
            got = read_box_file(path)
            for face in ("top_face", "bottom_face"):
                self.assertTrue(np.array_equal(np.array(getattr(got, face)),
                                               np.array(getattr(pal, face)) & 0xFE))

            del data["faces"]["top"], data["faces"]["bottom"]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            got = read_box_file(path)
            self.assertIsNone(got.top_face)
            self.assertIsNone(got.bottom_face)

            path = write_box_file(_jewel_model(), d, "Game")
            with open(path, encoding="utf-8") as f:
                faces = json.load(f)["faces"]
            self.assertIsNone(faces["top"])
            self.assertIsNone(faces["bottom"])
            self.assertFalse(os.path.exists(os.path.join(d, "Game.top.png")))

    def test_edge_face_written(self):
        """SLIP-0104 INV-13: a jewel box writes its edge face; a wrap box clears it."""
        with tempfile.TemporaryDirectory() as d:
            jewel = _jewel_model()
            path = write_box_file(jewel, d, "Game")
            with open(path, encoding="utf-8") as f:
                self.assertEqual(json.load(f)["faces"]["edge"], "Game.edge.png")
            got = read_box_file(path).edge_face
            self.assertTrue(np.array_equal(np.array(got),
                                           np.array(jewel.edge_face) & 0xFE))

            path = write_box_file(_model(), d, "Game")
            with open(path, encoding="utf-8") as f:
                faces = json.load(f)["faces"]
            self.assertIn("edge", faces)
            self.assertIsNone(faces["edge"])
            self.assertFalse(os.path.exists(os.path.join(d, "Game.edge.png")))

    def test_failed_face_leaves_no_json(self):
        """INV-3: a failed face leaves neither the old box file nor new faces."""
        real_save = box_file.save_optimized_png

        def save(image, path, compress_level=6):
            if path.endswith(".spine.png"):
                raise OSError("disk full")
            real_save(image, path, compress_level=compress_level)

        with tempfile.TemporaryDirectory() as d:
            write_box_file(_model(), d, "Game")
            with patch.object(box_file, "save_optimized_png", side_effect=save):
                with self.assertRaises(OSError):
                    write_box_file(_model(), d, "Game")
            self.assertEqual(os.listdir(d), [])

    def test_face_limits(self):
        """INV-4: faces are RGB, at most 1600 px, never enlarged."""
        ct = CASE_TYPES["PS2 DVD Case"]
        for size in ((3000, 4200), (100, 140)):
            with self.subTest(size=size), tempfile.TemporaryDirectory() as d:
                front = _noise(*size, seed=5, mode="RGBA")
                model = build_box_model(
                    front, _noise(*size, seed=6, mode="RGBA"), ct,
                    title="Game", serial="", platform="", spine_color=None,
                    case_color=None, spine_left_offset=0, spine_right_offset=0,
                    full_cover=False, show_texture=True,
                )
                write_box_file(model, d, "Game")
                for face in ("front", "spine", "back"):
                    with Image.open(os.path.join(d, f"Game.{face}.png")) as img:
                        img.load()
                        self.assertEqual(img.mode, "RGB", face)
                        self.assertLessEqual(max(img.size), 1600, face)
                        if face != "spine":
                            self.assertLessEqual(img.size[0], size[0], face)
                            self.assertLessEqual(img.size[1], size[1], face)
                with Image.open(os.path.join(d, "Game.front.png")) as img:
                    if size == (3000, 4200):
                        self.assertEqual(max(img.size), 1600)

    def test_stem_cannot_escape(self):
        """INV-10: a stem whose face names fail the name rule writes nothing."""
        for stem in ("../../evil", "a/b", "a\\b", ".x", ""):
            with self.subTest(stem=stem), tempfile.TemporaryDirectory() as d:
                inner = os.path.join(d, "out")
                os.mkdir(inner)
                with self.assertRaises(BoxFileError):
                    write_box_file(_model(), inner, stem)
                self.assertEqual(os.listdir(inner), [])
                self.assertEqual(os.listdir(d), ["out"])


class TestReading(unittest.TestCase):

    def test_round_trip(self):
        """INV-2: the reader accepts what the writer wrote."""
        for with_back in (True, False):
            with self.subTest(back=with_back), tempfile.TemporaryDirectory() as d:
                written = _model(with_back)
                model = read_box_file(write_box_file(written, d, "Game"))
                ct = CASE_TYPES["PS2 DVD Case"]
                self.assertEqual(
                    (model.case_type.name, model.case_type.width,
                     model.case_type.height, model.case_type.depth),
                    (ct.name, ct.width, ct.height, ct.depth),
                )
                self.assertEqual(model.case_type.platforms, ())
                self.assertEqual((model.top, model.bottom, model.edge),
                                 (written.top, written.bottom, written.edge))
                for face in ("front", "spine", "back"):
                    src, got = getattr(written, face), getattr(model, face)
                    if src is None:
                        self.assertIsNone(got)
                        continue
                    self.assertEqual(got.mode, "RGB")
                    self.assertTrue(np.array_equal(np.array(got),
                                                   np.array(src) & 0xFE), face)

    def test_reader_refuses(self):
        """INV-2: one fixture per reading rule."""
        def faces(**kw):
            return lambda data: data["faces"].update(kw)

        def case(**kw):
            return lambda data: data["case"].update(kw)

        fixtures = {
            "format foo": lambda data: data.update(format="foo"),
            "version 2": lambda data: data.update(version=2),
            "version true": lambda data: data.update(version=True),
            "../x.png": faces(front="../x.png"),
            "a/b.png": faces(front="a/b.png"),
            "a\\b.png": faces(front="a\\b.png"),
            "..": faces(front=".."),
            ".hidden.png": faces(front=".hidden.png"),
            "null front": faces(front=None),
            "missing spine file": lambda data: os.remove(
                os.path.join(self._dir, "Game.spine.png")),
            "back names a missing file": faces(back="missing.png"),
            "edge names a missing file": faces(edge="missing.png"),
            "depth_mm 0": case(depth_mm=0),
            "width_mm 5000": case(width_mm=5000),
            "colour red": lambda data: data["colours"].update(top="red"),
        }
        for label, mutate in fixtures.items():
            with self.subTest(fixture=label), tempfile.TemporaryDirectory() as d:
                self._dir = d
                path = write_box_file(_model(), d, "Game")
                # Valid pictures under every name a careless reader could
                # reach, so only the name rule can refuse. On Windows a
                # backslash is a separator, so a\b.png lands in folder a.
                os.mkdir(os.path.join(d, "a"))
                decoys = ["x.png", "b.png", os.path.join("a", "b.png"),
                          ".hidden.png"]
                if os.sep == "/":
                    decoys.append("a\\b.png")
                for name in decoys:
                    _noise(4, 4, 7).save(os.path.join(d, name))
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                mutate(data)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                with self.assertRaises(BoxFileError):
                    read_box_file(path)


    def test_v1_reader_without_edge(self):
        """SLIP-0104 INV-14: a jewel box file reads whole without faces.edge."""
        with tempfile.TemporaryDirectory() as d:
            path = write_box_file(_jewel_model(), d, "Game")
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            del data["faces"]["edge"]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            model = read_box_file(path)
            self.assertIsNone(model.edge_face)
            self.assertEqual(model.edge, CASE_TYPES["CD Jewel Case"].plastic)


class TestExportPng(unittest.TestCase):
    """§ 4.4: Export PNG writes the shown render's box file beside the PNG."""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def _window(self, d):
        from PyQt6 import sip
        from core.config import Config
        from ui.main_window import MainWindow
        window = MainWindow(Config(config_path=os.path.join(d, "c.json")))
        self.addCleanup(sip.delete, window)
        return window

    def test_export_writes_the_paired_model(self):
        from PyQt6.QtWidgets import QMessageBox
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d)
            png = os.path.join(d, "Game 3D Boxart.png")

            window._export_box_file(png)  # no render on show: nothing to pair
            self.assertFalse(os.path.exists(os.path.join(d, "Game.box.json")))

            window._box_model = _model()
            window._export_box_file(png)
            self.assertTrue(os.path.isfile(os.path.join(d, "Game.box.json")))

            # An existing box file is replaced only on Yes.
            os.remove(os.path.join(d, "Game.back.png"))
            with patch.object(QMessageBox, "question",
                              return_value=QMessageBox.StandardButton.No) as ask:
                window._export_box_file(png)
            ask.assert_called_once()
            self.assertFalse(os.path.exists(os.path.join(d, "Game.back.png")))

            window.config.set("export", "box_file", False)
            os.remove(os.path.join(d, "Game.box.json"))
            window._export_box_file(png)
            self.assertFalse(os.path.exists(os.path.join(d, "Game.box.json")))

    def test_compare_and_3d_view_exclude_each_other(self):
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d)
            window.view_3d_btn.setChecked(True)
            self.assertEqual(window.preview_stack.currentIndex(), 2)
            window.compare_check.setChecked(True)
            self.assertFalse(window.view_3d_btn.isChecked())
            self.assertEqual(window.preview_stack.currentIndex(), 1)
            window._toggle_3d_view()
            self.assertFalse(window.compare_check.isChecked())
            self.assertEqual(window.preview_stack.currentIndex(), 2)


class TestBatchStems(unittest.TestCase):

    def test_batch_does_not_overwrite(self):
        """INV-6: stems avoid existing box files and each other."""
        from ui.workers import pick_output_stems
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out")
            os.mkdir(out)
            open(os.path.join(out, "game.box.json"), "w").close()
            stems = pick_output_stems(
                [os.path.join(d, "A", "game.png"), os.path.join(d, "B", "game.png")],
                out,
            )
            self.assertEqual(len(stems), 2)
            self.assertNotEqual(stems[0], stems[1])
            self.assertNotIn("game", stems)

    def test_batch_writes_the_box_file_with_the_png_stem(self):
        """INV-6's other half, through BatchWorker itself."""
        from core.renderer import BoxRenderer
        from ui.workers import BatchWorker
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, "src"))
            src = os.path.join(d, "src", "game.png")
            Image.new("RGB", (135, 190), (200, 50, 50)).save(src)
            out = os.path.join(d, "out")
            os.mkdir(out)
            open(os.path.join(out, "game.box.json"), "w").close()
            worker = BatchWorker([src], out,
                                 BoxRenderer(CASE_TYPES["PS2 DVD Case"], output_width=128),
                                 box_file=True)
            errors = []
            worker.error.connect(errors.append)
            worker.run()
            self.assertEqual(errors, [])
            self.assertEqual(set(os.listdir(out)), {
                "game.box.json", "game (1).png", "game (1).box.json",
                "game (1).front.png", "game (1).spine.png",
            })


if __name__ == "__main__":
    unittest.main()
