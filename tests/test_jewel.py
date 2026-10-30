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
            _noise(135, 190, 1), None, CASE_TYPES["PS2 DVD Case"], title="Game",
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
        # No gloss: the strip's ridges are the same at its top and bottom.
        front = generate_front_texture(pal, 284, 250)
        self.assertEqual(front.getpixel(at)[3], front.getpixel((10, 200))[3])
        self.assertGreater(generate_front_texture(pal, 284, 250, back=True).getpixel(at)[3], 0)
        ntsc = CASE_TYPES["PS1 Jewel Case (NTSC-U)"]
        self.assertGreater(generate_front_texture(ntsc, 284, 250).getpixel(at)[3], 0)

    def test_ridge_lines_on_the_front_only(self):
        """The lid's two ridge lines mark where it opens, on the front; the
        back's overlay has none (the user, 2026-10-21)."""
        ntsc = CASE_TYPES["PS1 Jewel Case (NTSC-U)"]
        # At 2 px/mm the booklet starts at x = 39 and the inner ridge is x = 38.
        ridge, beside, y = 38, 42, 25
        front = generate_front_texture(ntsc, 284, 250)
        back = generate_front_texture(ntsc, 284, 250, back=True)
        self.assertGreater(front.getpixel((ridge, y))[3] - front.getpixel((beside, y))[3], 10)
        self.assertLessEqual(abs(back.getpixel((ridge, y))[3] - back.getpixel((beside, y))[3]), 3)

    def test_ps1_hinge_strip_is_ridged(self):
        """A PAL PS1 case's black hinge strip carries fine vertical ridges on
        the front (the user, 2026-10-21); clear NTSC lids, other jewel cases
        and the back do not (the user, 2026-10-30)."""
        row = range(4, 30)  # at 2 px/mm: across the hinge strip, short of its ridge lines
        y = 125

        def spread(overlay):
            alphas = [overlay.getpixel((x, y))[3] for x in row]
            return max(alphas) - min(alphas)

        pal = CASE_TYPES["PS1 Jewel Case (PAL)"]
        self.assertGreater(spread(generate_front_texture(pal, 284, 250)), 20)
        self.assertLess(spread(generate_front_texture(pal, 284, 250, back=True)), 10)
        for name in ("PS1 Jewel Case (NTSC-U)", "PS1 Jewel Case (NTSC-J)",
                     "CD Jewel Case", "Dreamcast Jewel Case (NTSC-J)"):
            with self.subTest(case=name):
                self.assertLess(spread(generate_front_texture(CASE_TYPES[name], 284, 250)), 10)

    def test_dreamcast_pal_strip_logo(self):
        """SLIP-0112: a PAL Dreamcast front carries "Dreamcast" moulded in a
        panel on its hinge strip, running up the strip; the back and the
        other Dreamcast cases do not."""
        def logo_box(name, back=False):
            o = np.asarray(generate_front_texture(CASE_TYPES[name], 1420, 1250, back=back))
            # The hinge strip inside the rim and short of its ridge lines, at
            # 10 px/mm. Sharp steps mark moulding; the lid's shine is smooth.
            strip = o[20:1230, 15:160, 3].astype(int)
            edges = np.zeros(strip.shape, dtype=bool)
            edges[:, 1:] |= np.abs(np.diff(strip, axis=1)) > 10
            edges[1:, :] |= np.abs(np.diff(strip, axis=0)) > 10
            rows = np.flatnonzero(edges.any(axis=1))
            cols = np.flatnonzero(edges.any(axis=0))
            if not len(rows):
                return None
            return rows[-1] - rows[0], cols[-1] - cols[0]

        tall, wide = logo_box("Dreamcast Jewel Case (PAL)")
        self.assertGreater(tall, 3 * wide)
        self.assertTrue(300 < tall < 500)   # the panel, about 40 mm
        self.assertIsNone(logo_box("Dreamcast Jewel Case (PAL)", back=True))
        self.assertIsNone(logo_box("Dreamcast Jewel Case (NTSC-U)"))

    def test_lid_margin_is_lit(self):
        """The clear lid round the booklet reads lighter than the booklet
        and the hinge strip, as in the user's PAL Ridge Racer Type 4 photo
        (2026-10-21); the back is unchanged."""
        pal = CASE_TYPES["PS1 Jewel Case (PAL)"]
        front = generate_front_texture(pal, 284, 250)
        back = generate_front_texture(pal, 284, 250, back=True)
        # At 2 px/mm: rim y < 2, top margin y < 5, booklet x 39 to 278.
        booklet, top, right, hinge = (150, 20), (150, 3), (281, 125), (10, 3)
        for margin in (top, right):
            self.assertGreater(front.getpixel(margin)[3] - front.getpixel(booklet)[3], 60)
        self.assertEqual(front.getpixel(hinge)[3], front.getpixel((10, 200))[3])
        self.assertLess(back.getpixel(top)[3] - back.getpixel(booklet)[3], 30)


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

    def test_clear_tray_shows_the_tray_print(self):
        """INV-6: a clear tray shows its back card's printed panel through
        the front's hinge strip, the same on every game, as on the user's US
        Dreamcast cases and US PS1 Crash Bandicoot (2026-10-21). Dreamcast:
        light paper with a line of dark text running along the strip. NTSC
        PS1: black, then a band of printed ribs whose brightness repeats down
        the strip. The back card's own strips never show there, and an
        opaque tray shows plastic."""
        booklet = Image.new("RGB", (1200, 1200), (128, 128, 128))

        def strip(case, back, x0=2, x1=15):
            front = _faces(booklet, back, case).front
            px = front.width / CASE_TYPES[case].width
            # Inside the card's height, clear of its rims.
            return np.asarray(front.convert("RGB"))[
                round(5 * px):round(120 * px), round(x0 * px):round(x1 * px)], px

        cases = ("Dreamcast Jewel Case (NTSC-U)", "PS1 Jewel Case (NTSC-U)",
                 "PS1 Jewel Case (NTSC-J)")
        for case in cases:
            with self.subTest(case=case):
                ct = CASE_TYPES[case]
                s, _ = strip(case, _card(ct, [RED, GREEN, BLUE]))
                self.assertTrue(np.array_equal(s, strip(case, None)[0]))

        s, _ = strip(cases[0], None)
        grey = s.mean(axis=2)
        # White paper and near-black lettering, as on the LaunchBox Sonic
        # Adventure box the user sent (2026-10-30): a grey wash read as
        # printed on the front.
        self.assertGreater((grey > 215).mean(), 0.5)
        self.assertLess(grey.min(), 60)
        ink = grey < 120
        rows, cols = np.flatnonzero(ink.any(axis=1)), np.flatnonzero(ink.any(axis=0))
        self.assertGreater(len(rows), 0)
        self.assertGreater(rows[-1] - rows[0], 3 * (cols[-1] - cols[0]))

        for case in cases[1:]:
            with self.subTest(case=case):
                band, px = strip(case, None, 8, 9)
                down = band.mean(axis=(1, 2))
                # Bold enough to read through the lid (the user's DuckStation
                # covers, 2026-10-30).
                self.assertGreater(down.max() - down.min(), 50)
                # The ribs repeat at their pitch.
                pitch = round(6.8 * px)
                self.assertLess(np.abs(down[pitch:] - down[:-pitch]).mean(), 3)

        pal = "PS1 Jewel Case (PAL)"
        s, _ = strip(pal, _card(CASE_TYPES[pal], [RED, GREEN, BLUE]))
        self.assertTrue(np.all(s == CASE_TYPES[pal].plastic))

    def test_tray_print_sits_at_the_back_of_a_hollow_strip(self):
        """The front's hinge strip is a window onto the back card's inside,
        a case's depth behind it (the user's drawing, 2026-10-30). Turning
        the box slides the print towards the spine by depth * tan(angle), and
        the inner wall by the booklet takes the room it leaves."""
        booklet = Image.new("RGB", (1200, 1200), (128, 128, 128))
        case = "Dreamcast Jewel Case (NTSC-U)"
        ct = CASE_TYPES[case]

        def row_of_ink(angle):
            front = _faces(booklet, None, case, view_angle=angle).front
            px = front.width / ct.width
            strip = np.asarray(front.convert("L"))[
                round(5 * px):round(120 * px), :round(19 * px)]
            cols = np.flatnonzero((strip < 90).mean(axis=0) > 0.01)
            return cols.mean() / px, strip, px

        at_10, _, _ = row_of_ink(10)
        at_40, strip_40, px = row_of_ink(40)
        depth = ct.depth - jewel._WINDOW_INSET_MM
        expected = depth * (np.tan(np.radians(40)) - np.tan(np.radians(10)))
        self.assertAlmostEqual(at_10 - at_40, expected, delta=0.5)
        # Next to the booklet the wall shows and the paper does not.
        wall = strip_40[:, round(18 * px):]
        self.assertLess(wall.std(axis=0).max(), 2)

        # The renderer turns the print with its own angle.
        def rendered(angle):
            r = BoxRenderer(ct, output_width=800, angle=angle,
                            show_reflection=False, show_shadow=False)
            return np.asarray(r.render(booklet, title="T", platform="Dreamcast"))
        with patch.object(renderer, "jewel_faces", wraps=jewel_faces) as faces:
            rendered(40)
        self.assertEqual(faces.call_args.kwargs["view_angle"], 40)

    def test_ps1_ribs_fill_the_window(self):
        """The ribbed band runs the width of the window, not a narrow column
        (the user, on the trial picture, 2026-10-30)."""
        booklet = Image.new("RGB", (1200, 1200), (128, 128, 128))
        front = _faces(booklet, None, "PS1 Jewel Case (NTSC-U)").front
        px = front.width / 142
        grey = np.asarray(front.convert("L"), dtype=float)[round(5 * px):round(120 * px)]
        for x_mm in (4, 12):
            with self.subTest(x_mm=x_mm):
                down = grey[:, round(x_mm * px)]
                self.assertGreater(down.max() - down.min(), 25)

    def test_fine_ridges_only_on_the_pal_ps1_strip(self):
        """The fine vertical lines belong to the PAL case's black hinge strip.
        A US or Japanese lid is clear there (the user, 2026-10-30)."""
        ridged = {name for name, ct in CASE_TYPES.items() if ct.ridged_hinge_strip}
        self.assertEqual(ridged, {"PS1 Jewel Case (PAL)"})

    def test_lid_lines_show_on_a_white_tray_print(self):
        """The lid's two lines by the booklet are dark over white paper, or
        they vanish and the strip reads as flat print (Sonic Adventure's
        LaunchBox box, 2026-10-30)."""
        case = CASE_TYPES["Dreamcast Jewel Case (NTSC-U)"]
        texture = generate_front_texture(case, 1420, 1250)
        booklet_x = round((case.width - 2.5 - 120) * 10)
        line = np.asarray(texture)[600, booklet_x - 3]
        self.assertLess(line[:3].max(), 100)
        self.assertGreater(line[3], 80)

    def test_ps1_tray_print_draws_no_word(self):
        """SLIP-0117: a US PS1 booklet already prints "PlayStation" down its
        own left band, so a word drawn in the hinge strip beside it showed
        the name twice (libretro's Crash Bandicoot (USA), 2026-10-21). The
        hinge strip holds dark ribs on black and no light lettering."""
        booklet = Image.new("RGB", (1200, 1200), (128, 128, 128))
        for case in ("PS1 Jewel Case (NTSC-U)", "PS1 Jewel Case (NTSC-J)"):
            with self.subTest(case=case):
                front = _faces(booklet, None, case).front
                px = front.width / CASE_TYPES[case].width
                strip = np.asarray(front.convert("L"))[
                    round(5 * px):round(120 * px), round(1 * px):round(18 * px)]
                self.assertLess(strip.max(), 150)

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


class TestMouldedLogo(unittest.TestCase):
    """SLIP-0110: the PS1 PAL case's top and bottom carry moulded text."""

    def _model(self, name, show_texture=True):
        return build_box_model(
            _noise(240, 240, 1), None, CASE_TYPES[name], title="Game", serial="",
            platform="PS1", spine_color=None, case_color=None,
            spine_left_offset=0, spine_right_offset=0, full_cover=None,
            show_texture=show_texture,
        )

    def test_only_the_pal_case_with_details(self):
        model = self._model("PS1 Jewel Case (PAL)")
        ct = model.case_type
        top = np.array(model.top_face).astype(int)
        self.assertEqual(model.top_face.size,
                         (model.front.width, round(ct.depth * model.front.width / ct.width)))
        self.assertIs(model.bottom_face, model.top_face)
        # Bare plastic at the ends, raised letters in the middle.
        self.assertTrue((top[:, :10] == BLACK_TRAY).all())
        middle = top[:, top.shape[1] // 3: 2 * top.shape[1] // 3]
        self.assertGreater(middle.max(), BLACK_TRAY[0] + 20)
        self.assertIsNone(self._model("PS1 Jewel Case (PAL)", show_texture=False).top_face)
        self.assertIsNone(self._model("PS1 Jewel Case (NTSC-U)").top_face)


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
        dvd = CASE_TYPES["PS2 DVD Case"]
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
            worker = BatchWorker(files, d, BoxRenderer(CASE_TYPES["PS2 DVD Case"]),
                                 case_types=cases)
            self.addCleanup(worker.deleteLater)
            for f, case in zip(files, cases, strict=True):
                self.assertEqual(worker._args_for(f, "S")[3], case)

            self._pick_by_hand(window, "PS1 Jewel Case (NTSC-J)")
            self.assertEqual([c.name for c in window._batch_cases(files)],
                             ["PS1 Jewel Case (NTSC-J)"] * 2)


if __name__ == "__main__":
    unittest.main()
