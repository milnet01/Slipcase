"""Tests for jewel cases: case data, faces, the window's case choice (SLIP-0106)."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

import core.box_model as box_model
import core.jewel as jewel
import core.renderer as renderer
from core.box_file import read_box_file
from core.box_model import build_box_model
from core.case_texture import SHINE_ALPHA, generate_front_texture, generate_lid_shine
from core.case_types import CASE_TYPES
from core.image_utils import wrap_panels_mm
from core.jewel import back_has_strips, jewel_faces, split_back_card
from core.renderer import BoxRenderer
from core.spine_generator import generate_spine

JEWEL_CASES = [ct for ct in CASE_TYPES.values() if ct.layout == "jewel"]
BLACK_TRAY = (0x10, 0x10, 0x10)
RED, GREEN, BLUE = (255, 0, 0), (0, 255, 0), (0, 0, 255)


def _noise(w: int, h: int, seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    return Image.fromarray(rng.integers(0, 256, (h, w, 3), dtype=np.uint8), "RGB")


def _bands(widths: list[int], colours: list[tuple[int, int, int]], h: int) -> Image.Image:
    """Solid vertical bands, left to right."""
    img = Image.new("RGB", (sum(widths), h))
    x = 0
    for width, colour in zip(widths, colours, strict=True):
        img.paste(colour, (x, 0, x + width, h))
        x += width
    return img


def _card(ct, colours, px_per_mm: int = 10) -> Image.Image:
    """A back card of `ct` drawn left strip | middle | right strip."""
    card_w, card_h = ct.jewel.back_card
    strip = round(ct.jewel.strip * px_per_mm)
    middle = round(card_w * px_per_mm) - 2 * strip
    return _bands([strip, middle, strip], colours, round(card_h * px_per_mm))


def _faces(front, back, case, **overrides):
    kwargs = dict(
        title="Game", serial="", platform="PS1", spine_color=None,
        spine_left_offset=0, spine_right_offset=0, full_cover=None,
        back_strips=None,
    )
    kwargs.update(overrides)
    return jewel_faces(front, back, CASE_TYPES[case], **kwargs)


def _centre(image: Image.Image) -> tuple[int, int, int]:
    return image.convert("RGB").getpixel((image.width // 2, image.height // 2))


def _same(a: Image.Image, b: Image.Image) -> bool:
    return a.size == b.size and np.array_equal(np.array(a), np.array(b))


class TestCaseData(unittest.TestCase):

    def test_back_has_strips(self):
        """INV-4: the nearer of the two card ratios wins."""
        expected = {
            ("PS1 Jewel Case (PAL)", (1580, 1180)): True,
            ("PS1 Jewel Case (PAL)", (1310, 1180)): False,
            ("CD Jewel Case", (1500, 1180)): True,
            # 1.169, within 8.7% of the with-strips 1.271: only the
            # nearest-ratio rule calls this a card without strips.
            ("CD Jewel Case", (1380, 1180)): False,
        }
        for (case, size), has in expected.items():
            with self.subTest(case=case, size=size):
                self.assertIs(back_has_strips(Image.new("RGB", size), CASE_TYPES[case]), has)

    def test_wrap_layout_unchanged(self):
        """INV-9: a wrap case's panels are today's arithmetic, and it has no edge face."""
        for ct in CASE_TYPES.values():
            if ct.layout != "wrap":
                continue
            with self.subTest(case=ct.name):
                self.assertEqual(wrap_panels_mm(ct), (ct.width, ct.depth, ct.width, ct.height))
        model = build_box_model(
            _noise(135, 190, 1), None, CASE_TYPES["DVD Case"], title="Game",
            serial="", platform="PS2", spine_color=None, case_color=None,
            spine_left_offset=0, spine_right_offset=0, full_cover=None,
            show_texture=False,
        )
        self.assertIsNone(model.edge_face)

    def test_split_survives_extremes(self):
        """INV-10: any scan and any slider offsets give three non-empty parts."""
        image = Image.new("RGB", (3, 3), (200, 10, 10))
        for case in ("CD Jewel Case", "PS1 Jewel Case (PAL)"):
            for offsets in ((0, 0), (1000, 1000), (-1000, -1000),
                            (1000, -1000), (-1000, 1000)):
                with self.subTest(case=case, offsets=offsets):
                    parts = split_back_card(image, CASE_TYPES[case], *offsets)
                    self.assertEqual(sum(p.width for p in parts), 3)
                    for part in parts:
                        self.assertGreaterEqual(part.width, 1)

    def test_jewel_overlays(self):
        """INV-11: every jewel entry gets the jewel overlay, with the lid shine."""
        self.assertTrue(JEWEL_CASES)
        for ct in JEWEL_CASES:
            with self.subTest(case=ct.name):
                overlay = generate_front_texture(ct, 284, 250)
                # 25 mm in: over the booklet on every jewel case.
                self.assertGreater(overlay.getpixel((50, 10))[3],
                                   overlay.getpixel((274, 240))[3])
        shine = generate_lid_shine(284, 250)
        self.assertEqual(shine.getpixel((0, 0))[3], SHINE_ALPHA)
        self.assertEqual(shine.getpixel((283, 249))[3], 0)

    def test_matte_hinge_strip(self):
        """The PS1 PAL hinge strip is matte: no gloss on it from the front,
        though the back's clear base and the NTSC-U lid still shine there."""
        pal = CASE_TYPES["PS1 Jewel Case (PAL)"]
        at = (10, 10)  # 5 mm in: on the hinge strip, clear of the rim
        self.assertEqual(generate_front_texture(pal, 284, 250).getpixel(at)[3], 0)
        self.assertGreater(generate_front_texture(pal, 284, 250, back=True).getpixel(at)[3], 0)
        ntsc = CASE_TYPES["PS1 Jewel Case (NTSC-U)"]
        self.assertGreater(generate_front_texture(ntsc, 284, 250).getpixel(at)[3], 0)


class TestFaces(unittest.TestCase):

    def test_strips_go_to_their_sides(self):
        """INV-5: right strip to the hinge, left to the opening, middle to the back."""
        ct = CASE_TYPES["PS1 Jewel Case (PAL)"]
        card = _card(ct, [RED, GREEN, BLUE])
        booklet = Image.new("RGB", (1200, 1200), (128, 128, 128))
        faces = _faces(booklet, card, ct.name)
        self.assertEqual(_centre(faces.hinge), BLUE)
        self.assertEqual(_centre(faces.opening), RED)
        self.assertEqual(_centre(faces.back), GREEN)

        base = split_back_card(card, ct)[0].width
        self.assertEqual(split_back_card(card, ct, left_offset=20)[0].width, base + 20)
        with patch.object(jewel, "split_back_card", wraps=jewel.split_back_card) as split:
            _faces(booklet, card, ct.name, spine_left_offset=20, spine_right_offset=-5)
        self.assertEqual(split.call_args.kwargs["left_offset"], 20)
        self.assertEqual(split.call_args.kwargs["right_offset"], -5)

    def test_front_layout_and_colours(self):
        """INV-6: hinge strip of plastic, booklet in its area, plastic top and edges."""
        ct = CASE_TYPES["PS1 Jewel Case (PAL)"]
        booklet = Image.new("RGB", (1200, 1200), RED)

        def model(case_color):
            return build_box_model(
                booklet, None, ct, title="Game", serial="", platform="PS1",
                spine_color=None, case_color=case_color, spine_left_offset=0,
                spine_right_offset=0, full_cover=None, show_texture=False,
            )

        m = model(None)
        px = m.front.width / ct.width
        self.assertEqual(m.front.getpixel((round(9 * px), m.front.height // 2)), BLACK_TRAY)
        # Booklet area: 2.5 mm margins top, bottom and right, 120 x 120 mm.
        self.assertEqual(m.front.getpixel((round(79.5 * px), round(62.5 * px))), RED)
        self.assertEqual((m.top, m.bottom, m.edge), (BLACK_TRAY,) * 3)
        self.assertEqual((model(BLUE).top, model(BLUE).bottom, model(BLUE).edge), (BLUE,) * 3)

    def test_rendered_top_stands_apart_from_the_border(self):
        """A render's top face is lit lighter than the front's plastic border,
        so the two do not merge into one thick band (the user, 2026-10-21)."""
        r = BoxRenderer(CASE_TYPES["PS1 Jewel Case (PAL)"], output_width=1000, angle=40,
                        show_reflection=False, show_shadow=False, show_texture=False)
        img = np.array(r.render(Image.new("RGB", (1200, 1200), RED), platform="PS1"))
        col = img[:, img.shape[1] // 2]
        top = np.argmax(col[:, 3] > 0)
        booklet = np.argmax((col[:, 0] > 150) & (col[:, 1] < 80))
        self.assertGreater(col[top:booklet, :3].max(), BLACK_TRAY[0] + 30)

    def test_face_sources(self):
        """INV-7: § 4.4's priority table."""
        case = "CD Jewel Case"
        booklet = _noise(1200, 1200, 3)

        def generated(face):
            return generate_spine(
                title="Game", spine_width=face.width, spine_height=face.height,
                platform="PS1", serial="", bg_color=None,
            ).convert("RGBA")

        faces = _faces(booklet, None, case)
        self.assertIsNone(faces.back)
        self.assertTrue(_same(faces.hinge, generated(faces.hinge)))
        self.assertTrue(_same(faces.opening, generated(faces.opening)))

        # A wrap: back middle | hinge strip | booklet, 10 px per mm.
        yellow = (255, 255, 0)
        wrap = _bands([1380, 60, 1200], [GREEN, yellow, RED], 1180)
        faces = _faces(wrap, None, case)
        self.assertEqual(_centre(faces.hinge), yellow)
        self.assertEqual(_centre(faces.back), GREEN)
        self.assertTrue(_same(faces.opening, generated(faces.opening)))

        # A wrap plus a card with strips: the card supplies back and both sides.
        magenta, cyan, orange = (255, 0, 255), (0, 255, 255), (255, 128, 0)
        faces = _faces(wrap, _card(CASE_TYPES[case], [magenta, cyan, orange]), case)
        self.assertEqual(_centre(faces.back), cyan)
        self.assertEqual(_centre(faces.hinge), orange)
        self.assertEqual(_centre(faces.opening), magenta)

    def test_render_and_model_share_faces(self):
        """INV-8: one jewel_faces call each, with the same arguments."""
        ct = CASE_TYPES["PS1 Jewel Case (PAL)"]
        front = _noise(1200, 1200, 4)
        back = _card(ct, [RED, GREEN, BLUE])
        common = dict(
            title="Game", serial="SCES-01234", platform="PS1",
            spine_color=(1, 2, 3), spine_left_offset=7, spine_right_offset=-3,
            full_cover=False, back_strips=True,
        )
        with patch.object(renderer, "jewel_faces", wraps=jewel.jewel_faces) as r_call, \
                patch.object(box_model, "jewel_faces", wraps=jewel.jewel_faces) as m_call:
            BoxRenderer(ct, output_width=128, show_reflection=False,
                        show_shadow=False).render(front, back, **common)
            build_box_model(front, back, ct, case_color=None, show_texture=True, **common)
        self.assertEqual(r_call.call_count, 1)
        self.assertEqual(m_call.call_count, 1)
        self.assertEqual(r_call.call_args, m_call.call_args)


class TestCompatibility(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def test_old_jewel_name_still_loads(self):
        """INV-12: an old box file and an old setting naming CD Jewel Case."""
        from PyQt6 import sip
        from core.config import Config
        from ui.main_window import MainWindow
        with tempfile.TemporaryDirectory() as d:
            for face, size in (("front", (125, 142)), ("spine", (10, 142))):
                Image.new("RGB", size).save(os.path.join(d, f"Old.{face}.png"))
            path = os.path.join(d, "Old.box.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "format": "slipcase-box", "version": 1,
                    "case": {"name": "CD Jewel Case", "width_mm": 125,
                             "height_mm": 142, "depth_mm": 10.4},
                    "colours": {"top": "#000000", "bottom": "#000000",
                                "edge": "#000000"},
                    "faces": {"front": "Old.front.png", "spine": "Old.spine.png",
                              "back": None},
                }, f)
            model = read_box_file(path)
            self.assertEqual(model.case_type.width, 125)
            self.assertIsNone(model.edge_face)

            config = Config(config_path=os.path.join(d, "c.json"))
            config.set("ui", "last_case_type", "CD Jewel Case")
            window = MainWindow(config)
            self.addCleanup(sip.delete, window)
            self.assertEqual(window.case_combo.currentText(), "CD Jewel Case")


class TestCardCase(unittest.TestCase):
    """SLIP-0111: the back card's proportions choose between regional cases."""

    def test_card_case(self):
        ntsc, pal = CASE_TYPES["PS1 Jewel Case (NTSC-U)"], CASE_TYPES["PS1 Jewel Case (PAL)"]
        ntsc_j = CASE_TYPES["PS1 Jewel Case (NTSC-J)"]
        # Card size in tenths of a mm: with strips, then the middle alone.
        for size, shown, expected in [
            ((1580, 1180), ntsc, pal), ((1310, 1180), ntsc, pal),
            ((1500, 1180), pal, ntsc), ((1380, 1180), pal, ntsc),
            ((1500, 1180), ntsc, ntsc), ((1500, 1180), ntsc_j, ntsc_j),
            ((1580, 1180), pal, pal),
        ]:
            with self.subTest(size=size, shown=shown.name):
                got = jewel.card_case(Image.new("RGB", size), "PS1", shown)
                self.assertEqual(got.name, expected.name)
        dvd = CASE_TYPES["DVD Case"]
        self.assertIs(jewel.card_case(Image.new("RGB", (1580, 1180)), "PS2", dvd), dvd)

    def test_fold_reach_crosses_any_strip(self):
        """With the standard card's folds on a PAL scan, the sliders still
        reach the real folds."""
        pal_card = _bands([135, 1310, 135], [BLACK_TRAY, (240, 220, 0), BLACK_TRAY], 1180)
        left, right = jewel.detect_strip_folds(pal_card, CASE_TYPES["PS1 Jewel Case (NTSC-U)"])
        reach = jewel.fold_reach(pal_card)
        self.assertLessEqual(abs(135 - left), reach)
        self.assertLessEqual(abs(1445 - right), reach)


class TestCaseChoice(unittest.TestCase):

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
        window.platform_combo.setCurrentText("PS1")
        return window

    def _pick_by_hand(self, window, name):
        idx = window.case_combo.findText(name)
        window.case_combo.setCurrentIndex(idx)
        window.case_combo.activated.emit(idx)

    def test_hand_choice_holds_for_one_cover(self):
        """INV-3: detection sets the case; a hand pick holds until the next load."""
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d)
            window._detect_case("A (Europe).png")
            self.assertEqual(window.case_combo.currentText(), "PS1 Jewel Case (PAL)")
            self.assertFalse(window._case_by_hand)

            self._pick_by_hand(window, "PS1 Jewel Case (NTSC-J)")
            self.assertTrue(window._case_by_hand)
            self.assertEqual([c.name for c in window._batch_cases(["B (Europe).png"])],
                             ["PS1 Jewel Case (NTSC-J)"])

            window._detect_case("C (USA).png")
            self.assertEqual(window.case_combo.currentText(), "PS1 Jewel Case (NTSC-U)")
            self.assertFalse(window._case_by_hand)

    def test_back_card_picks_the_case(self):
        """SLIP-0111: a PAL-sized back card shows the PAL case, and the
        sliders reach a whole strip; a hand pick holds."""
        pal_card = _bands([135, 1310, 135], [BLACK_TRAY, (240, 220, 0), BLACK_TRAY], 1180)
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d)
            self.assertEqual(window.case_combo.currentText(), "PS1 Jewel Case (NTSC-U)")
            window._set_back_image(pal_card)
            self.assertEqual(window.case_combo.currentText(), "PS1 Jewel Case (PAL)")
            self.assertGreaterEqual(window.spine_left_slider.maximum(), 135)

            window._detect_case("A (USA).png")
            self.assertEqual(window.case_combo.currentText(), "PS1 Jewel Case (PAL)")

            self._pick_by_hand(window, "PS1 Jewel Case (NTSC-U)")
            window._set_back_image(pal_card)
            self.assertEqual(window.case_combo.currentText(), "PS1 Jewel Case (NTSC-U)")

    def test_batch_cases(self):
        """INV-13: each file gets its detected case unless one was picked by hand."""
        from ui.workers import BatchWorker
        files = ["A (Europe).png", "B (USA).png"]
        with tempfile.TemporaryDirectory() as d:
            window = self._window(d)
            cases = window._batch_cases(files)
            self.assertEqual([c.name for c in cases],
                             ["PS1 Jewel Case (PAL)", "PS1 Jewel Case (NTSC-U)"])
            worker = BatchWorker(files, d, BoxRenderer(CASE_TYPES["DVD Case"]),
                                 case_types=cases)
            self.addCleanup(worker.deleteLater)
            for f, case in zip(files, cases, strict=True):
                self.assertEqual(worker._args_for(f, "S")[3], case)

            self._pick_by_hand(window, "PS1 Jewel Case (NTSC-J)")
            self.assertEqual([c.name for c in window._batch_cases(files)],
                             ["PS1 Jewel Case (NTSC-J)"] * 2)


if __name__ == "__main__":
    unittest.main()
