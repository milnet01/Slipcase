"""Tests for core/box_model.py: the faces of the turnable box (SLIP-0104)."""

import unittest
from dataclasses import replace

import numpy as np
from PIL import Image, ImageOps

from core.box_model import build_box_model
from core.case_texture import generate_front_texture, generate_spine_texture
from core.case_types import CASE_TYPES
from core.image_utils import CLEAR_RIM, inset_in_rim, split_full_cover
from core.spine_generator import generate_spine


def _noise(w: int, h: int, seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    return Image.fromarray(rng.integers(0, 256, (h, w, 3), dtype=np.uint8), "RGB")


def _build(front, back=None, case="PS2 DVD Case", **overrides):
    kwargs = dict(
        title="Game", serial="SLUS-00001", platform="PS2", spine_color=None,
        case_color=None, spine_left_offset=0, spine_right_offset=0,
        full_cover=None, show_texture=False,
    )
    kwargs.update(overrides)
    return build_box_model(front, back, CASE_TYPES[case], **kwargs)


def _scaled(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """A source picture scaled as build_box_model scales a face."""
    return image.convert("RGBA").resize(size, Image.Resampling.LANCZOS)


def _in_rim(image: Image.Image, size: tuple[int, int], case: str,
            opening: str | None) -> Image.Image:
    """A source picture scaled, then framed by its case's plastic lip."""
    return inset_in_rim(_scaled(image, size), CASE_TYPES[case], None, opening)


def _on(image: Image.Image, colour: tuple[int, int, int]) -> Image.Image:
    """`image` flattened onto `colour`: the generated spine is partly
    transparent, and § 4.2 lays such faces on the edge colour."""
    background = Image.new("RGBA", image.size, (*colour, 255))
    return Image.alpha_composite(background, image.convert("RGBA")).convert("RGB")


class TestFaceSelection(unittest.TestCase):
    """INV-5: the model uses the faces render would use."""

    def assertSamePixels(self, a: Image.Image, b: Image.Image) -> None:
        self.assertEqual(a.size, b.size)
        self.assertTrue(np.array_equal(np.array(a), np.array(b)))

    def assertFramed(self, face, picture, case, opening) -> None:
        self.assertSamePixels(face, _in_rim(picture, face.size, case, opening).convert("RGB"))

    def test_full_cover_faces(self):
        ct = CASE_TYPES["PS2 DVD Case"]
        cover = _noise(568, 380, seed=1)  # back + spine + front, to scale
        model = _build(cover, spine_left_offset=6, spine_right_offset=-4)
        back, spine, front = split_full_cover(
            cover, ct, left_offset=6, right_offset=-4,
        )
        self.assertFramed(model.front, front, ct.name, "right")
        self.assertFramed(model.spine, spine, ct.name, None)
        self.assertFramed(model.back, back, ct.name, "left")

        # A loaded back cover wins over the split one.
        loaded = _noise(270, 380, seed=2)
        model = _build(cover, back=loaded, spine_left_offset=6, spine_right_offset=-4)
        self.assertFramed(model.back, loaded, ct.name, "left")

    def test_front_only_faces(self):
        ct = CASE_TYPES["PS2 DVD Case"]
        cover = _noise(270, 380, seed=3)
        model = _build(cover, full_cover=False, spine_color=(10, 20, 30))
        self.assertIsNone(model.back)
        self.assertFramed(model.front, cover, ct.name, "right")

        # The spine is generated at the front height's scale.
        h = model.front.size[1]
        self.assertEqual(model.spine.size, (max(round(ct.depth * h / ct.height), 4), h))
        expected = generate_spine(
            title="Game", spine_width=model.spine.size[0], spine_height=h,
            platform="PS2", serial="SLUS-00001", bg_color=(10, 20, 30),
        )
        self.assertSamePixels(model.spine, _on(inset_in_rim(expected, ct, None, None), model.edge))

        loaded = _noise(270, 380, seed=4)
        model = _build(cover, back=loaded, full_cover=False)
        self.assertFramed(model.back, loaded, ct.name, "left")


    def test_loaded_spine_wins(self):
        """A loaded spine picture wins over the generated spine and over a
        full cover's split one; one lying on its side is stood upright with
        its left end at the top (SLIP-0129)."""
        sideways = Image.new("RGB", (400, 30), (255, 0, 0))
        sideways.paste((0, 0, 255), (200, 0, 400, 30))
        ct = CASE_TYPES["PS2 DVD Case"]
        wrap = _noise(round(2 * ct.width + ct.depth) * 4, round(ct.height) * 4, 3)
        for label, front, case in (("front only", _noise(270, 380, 1), "PS2 DVD Case"),
                                   ("full cover", wrap, "PS2 DVD Case"),
                                   ("jewel", _noise(300, 300, 2), "CD Jewel Case")):
            with self.subTest(label):
                spine = np.asarray(_build(front, case=case, spine_image=sideways).spine)
                h, w = spine.shape[:2]
                top = spine[h // 8, w // 2].astype(int)
                bottom = spine[h - h // 8, w // 2].astype(int)
                self.assertGreater(top[0], 200)
                self.assertLess(top[2], 60)
                self.assertGreater(bottom[2], 200)
                self.assertLess(bottom[0], 60)


class TestCaseDetails(unittest.TestCase):
    """INV-11: case details are baked into the faces, the back's mirrored."""

    def test_case_details_baked_in(self):
        ct = CASE_TYPES["PS4 Blu-ray Case"]
        grey = Image.new("RGB", (270, 342), (128, 128, 128))
        model = _build(grey, back=grey.copy(), case="PS4 Blu-ray Case",
                       full_cover=False, show_texture=True)

        w, h = model.front.size
        front_tex = generate_front_texture(ct, w, h)
        framed_front = _in_rim(grey, (w, h), ct.name, "right")
        expected_front = Image.alpha_composite(framed_front, front_tex)
        self.assertTrue(np.array_equal(np.array(model.front),
                                       np.array(expected_front.convert("RGB"))))
        self.assertFalse(np.array_equal(np.array(model.front),
                                        np.array(framed_front.convert("RGB"))),
                         "the overlay changed no pixel, so this test proves nothing")

        bw, bh = model.back.size
        back_tex = generate_front_texture(ct, bw, bh)
        framed_back = _in_rim(grey, (bw, bh), ct.name, "left")
        mirrored = Image.alpha_composite(framed_back, ImageOps.mirror(back_tex))
        unmirrored = Image.alpha_composite(framed_back, back_tex)
        self.assertFalse(np.array_equal(np.array(mirrored), np.array(unmirrored)),
                         "the front overlay is symmetric, so mirroring is untested")
        self.assertTrue(np.array_equal(np.array(model.back),
                                       np.array(mirrored.convert("RGB"))))

        sw, sh = model.spine.size
        plain_spine = generate_spine(title="Game", spine_width=sw, spine_height=sh,
                                     platform="PS2", serial="SLUS-00001")
        framed_spine = inset_in_rim(plain_spine, ct, None, None)
        expected_spine = Image.alpha_composite(framed_spine,
                                               generate_spine_texture(ct, sw, sh))
        self.assertTrue(np.array_equal(np.array(model.spine),
                                       np.array(_on(expected_spine, model.edge))))

        # With show_texture clear, no face carries the overlay.
        plain = _build(grey, back=grey.copy(), case="PS4 Blu-ray Case",
                       full_cover=False, show_texture=False)
        self.assertTrue(np.array_equal(np.array(plain.front),
                                       np.array(framed_front.convert("RGB"))))
        self.assertTrue(np.array_equal(np.array(plain.back),
                                       np.array(framed_back.convert("RGB"))))
        self.assertTrue(np.array_equal(np.array(plain.spine),
                                       np.array(_on(framed_spine, plain.edge))))


class TestColours(unittest.TestCase):
    """§ 4.1: plastic is its own colour; a printed box's top and bottom come
    from the front's edges; case_color beats both."""

    def test_colours(self):
        cover = Image.new("RGB", (270, 380), (200, 0, 0))
        cover.paste((0, 0, 200), (0, 190, 270, 380))
        model = _build(cover, case="Switch Case", full_cover=False)
        self.assertEqual((model.top, model.bottom, model.edge), (CLEAR_RIM,) * 3)

        model = _build(cover, case="NES Cartridge Box", full_cover=False)
        self.assertEqual(model.top, (200, 0, 0))
        self.assertEqual(model.bottom, (0, 0, 200))
        self.assertEqual(model.edge, model.top)

        model = _build(cover, case="Switch Case", full_cover=False, case_color=(9, 8, 7))
        self.assertEqual((model.top, model.bottom, model.edge), ((9, 8, 7),) * 3)


class TestLip(unittest.TestCase):
    """SLIP-0125 INV-9: a real lip replaces the painted inner wall."""

    def test_lip_replaces_painted_wall(self):
        ps5 = CASE_TYPES["PS5 Blu-ray Case"]
        grey = Image.new("RGB", (270, 343), (128, 128, 128))
        fronts = {}
        for label, case in (("shaped", ps5), ("flat", replace(ps5, shape=None))):
            fronts[label] = np.array(build_box_model(
                grey, None, case, title="Game", serial="", platform="PS5",
                spine_color=None, case_color=None, spine_left_offset=0,
                spine_right_offset=0, full_cover=False, show_texture=False,
            ).front)
        h, w = fronts["shaped"].shape[:2]
        rim = max(1, round(ps5.rim_mm * h / ps5.height))
        # The row just inside the top of the frame, where the wall is painted.
        self.assertFalse(np.array_equal(fronts["flat"][rim - 1, w // 2],
                                        fronts["flat"][0, w // 2]),
                         "no painted wall without the shape, so this test proves nothing")
        self.assertTrue(np.array_equal(fronts["shaped"][rim - 1, w // 2],
                                       fronts["shaped"][0, w // 2]))

    def test_lip_width_is_rim_width(self):
        shaped = [ct for ct in CASE_TYPES.values()
                  if ct.shape is not None and ct.shape.lip_height > 0]
        self.assertTrue(shaped, "no case has a lip, so this test proves nothing")
        for ct in shaped:
            with self.subTest(case=ct.name):
                self.assertEqual(ct.shape.lip_width, ct.rim_mm)


if __name__ == "__main__":
    unittest.main()
