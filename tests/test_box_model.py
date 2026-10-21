"""Tests for core/box_model.py: the faces of the turnable box (SLIP-0104)."""

import unittest

import numpy as np
from PIL import Image, ImageOps

from core.box_model import build_box_model
from core.case_texture import generate_front_texture, generate_spine_texture
from core.case_types import CASE_TYPES
from core.image_utils import split_full_cover
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

    def test_full_cover_faces(self):
        ct = CASE_TYPES["PS2 DVD Case"]
        cover = _noise(568, 380, seed=1)  # back + spine + front, to scale
        model = _build(cover, spine_left_offset=6, spine_right_offset=-4)
        back, spine, front = split_full_cover(
            cover, ct, left_offset=6, right_offset=-4,
        )
        self.assertSamePixels(model.front, _scaled(front, model.front.size).convert("RGB"))
        self.assertSamePixels(model.spine, _scaled(spine, model.spine.size).convert("RGB"))
        self.assertSamePixels(model.back, _scaled(back, model.back.size).convert("RGB"))

        # A loaded back cover wins over the split one.
        loaded = _noise(270, 380, seed=2)
        model = _build(cover, back=loaded, spine_left_offset=6, spine_right_offset=-4)
        self.assertSamePixels(model.back, _scaled(loaded, model.back.size).convert("RGB"))

    def test_front_only_faces(self):
        ct = CASE_TYPES["PS2 DVD Case"]
        cover = _noise(270, 380, seed=3)
        model = _build(cover, full_cover=False, spine_color=(10, 20, 30))
        self.assertIsNone(model.back)
        self.assertSamePixels(model.front, _scaled(cover, model.front.size).convert("RGB"))

        # The spine is generated at the front height's scale.
        h = model.front.size[1]
        self.assertEqual(model.spine.size, (max(round(ct.depth * h / ct.height), 4), h))
        expected = generate_spine(
            title="Game", spine_width=model.spine.size[0], spine_height=h,
            platform="PS2", serial="SLUS-00001", bg_color=(10, 20, 30),
        )
        self.assertSamePixels(model.spine, _on(expected, model.edge))

        loaded = _noise(270, 380, seed=4)
        model = _build(cover, back=loaded, full_cover=False)
        self.assertSamePixels(model.back, _scaled(loaded, model.back.size).convert("RGB"))


class TestCaseDetails(unittest.TestCase):
    """INV-11: case details are baked into the faces, the back's mirrored."""

    def test_case_details_baked_in(self):
        ct = CASE_TYPES["PS3 Blu-ray Case"]
        grey = Image.new("RGB", (270, 342), (128, 128, 128))
        model = _build(grey, back=grey.copy(), case="PS3 Blu-ray Case",
                       full_cover=False, show_texture=True)

        w, h = model.front.size
        front_tex = generate_front_texture(ct, w, h)
        expected_front = Image.alpha_composite(_scaled(grey, (w, h)), front_tex)
        self.assertTrue(np.array_equal(np.array(model.front),
                                       np.array(expected_front.convert("RGB"))))
        self.assertFalse(np.array_equal(np.array(model.front),
                                        np.array(_scaled(grey, (w, h)).convert("RGB"))),
                         "the overlay changed no pixel, so this test proves nothing")

        bw, bh = model.back.size
        back_tex = generate_front_texture(ct, bw, bh)
        mirrored = Image.alpha_composite(_scaled(grey, (bw, bh)), ImageOps.mirror(back_tex))
        unmirrored = Image.alpha_composite(_scaled(grey, (bw, bh)), back_tex)
        self.assertFalse(np.array_equal(np.array(mirrored), np.array(unmirrored)),
                         "the front overlay is symmetric, so mirroring is untested")
        self.assertTrue(np.array_equal(np.array(model.back),
                                       np.array(mirrored.convert("RGB"))))

        sw, sh = model.spine.size
        plain_spine = generate_spine(title="Game", spine_width=sw, spine_height=sh,
                                     platform="PS2", serial="SLUS-00001")
        expected_spine = Image.alpha_composite(plain_spine.convert("RGBA"),
                                               generate_spine_texture(ct, sw, sh))
        self.assertTrue(np.array_equal(np.array(model.spine),
                                       np.array(_on(expected_spine, model.edge))))

        # With show_texture clear, no face carries the overlay.
        plain = _build(grey, back=grey.copy(), case="PS3 Blu-ray Case",
                       full_cover=False, show_texture=False)
        self.assertTrue(np.array_equal(np.array(plain.front),
                                       np.array(_scaled(grey, (w, h)).convert("RGB"))))
        self.assertTrue(np.array_equal(np.array(plain.back),
                                       np.array(_scaled(grey, (bw, bh)).convert("RGB"))))
        self.assertTrue(np.array_equal(np.array(plain.spine),
                                       np.array(_on(plain_spine, plain.edge))))


class TestColours(unittest.TestCase):
    """§ 4.1: top and bottom come from the front's edges unless case_color is set."""

    def test_colours(self):
        cover = Image.new("RGB", (270, 380), (200, 0, 0))
        cover.paste((0, 0, 200), (0, 190, 270, 380))
        # A clear, untinted case shows the cover's own colours (SLIP-0107).
        model = _build(cover, case="Switch Case", full_cover=False)
        self.assertEqual(model.top, (200, 0, 0))
        self.assertEqual(model.bottom, (0, 0, 200))
        self.assertEqual(model.edge, model.top)

        model = _build(cover, case="Switch Case", full_cover=False, case_color=(9, 8, 7))
        self.assertEqual((model.top, model.bottom, model.edge), ((9, 8, 7),) * 3)


if __name__ == "__main__":
    unittest.main()
