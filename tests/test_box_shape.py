"""Tests for core/box_shape.py: the solid the 3D viewer draws (SLIP-0125)."""

import unittest
from dataclasses import replace

from core.box_shape import box_patches
from core.case_types import CASE_TYPES, CaseShape

PS5 = CASE_TYPES["PS5 Blu-ray Case"]

# Shapes that take each path through the profiles and the corners.
SHAPES = {
    "PS5": PS5.shape,
    "PS3": CASE_TYPES["PS3 Blu-ray Case"].shape,
    "lip and seam, no recess": CaseShape(3, 1, 2.5, 0.5, 0.8, 0.4),
    "no lip, no seam": CaseShape(3, 1),
    "square corners": CaseShape(0, 1, 2.5, 0.5, 0.8, 0.4),
    "corners tighter than the lip": CaseShape(1, 1, 2.5, 0.5, 0.8, 0.4),
    "lip, no edge rounding": CaseShape(3, 0, 2.5, 0.5, 0, 0),
    "seam only": CaseShape(0, 0, 0, 0, 0.8, 0.4),
    "flat": CaseShape(0, 0),
    "recess, no seam": CaseShape(3, 1, 2.5, 0.5, 0, 0, 59, 6, 1.5),
    "recess only": CaseShape(0, 0, 0, 0, 0, 0, 59, 6, 1.5),
}


def _key(point):
    return tuple(round(c, 6) for c in point)


def _signed_volume(patches) -> float:
    """The volume the patches enclose, positive when they are wound so their
    normals point out (clockwise as seen from outside)."""
    total = 0.0
    for patch in patches:
        a = patch.corners[0]
        for b, c in zip(patch.corners[1:], patch.corners[2:], strict=False):
            total += (a[0] * (b[1] * c[2] - b[2] * c[1])
                      - a[1] * (b[0] * c[2] - b[2] * c[0])
                      + a[2] * (b[0] * c[1] - b[1] * c[0]))
    return -total / 6


class TestBoxShape(unittest.TestCase):

    def test_no_shape_is_six_faces(self):
        """INV-1: corners copied from ui/box_viewer.py's _face_corners before
        SLIP-0125, for 135 x 171.5 x 13 mm."""
        w, h, d = 67.5, 85.75, 6.5
        expected = {
            "front": [(-w, h, d), (w, h, d), (w, -h, d), (-w, -h, d)],
            "back": [(w, h, -d), (-w, h, -d), (-w, -h, -d), (w, -h, -d)],
            "spine": [(-w, h, -d), (-w, h, d), (-w, -h, d), (-w, -h, -d)],
            "edge": [(w, h, d), (w, h, -d), (w, -h, -d), (w, -h, d)],
            "top": [(-w, h, -d), (w, h, -d), (w, h, d), (-w, h, d)],
            "bottom": [(-w, -h, d), (w, -h, d), (w, -h, -d), (-w, -h, -d)],
        }
        patches = box_patches(CASE_TYPES["PS4 Blu-ray Case"])
        self.assertEqual(len(patches), 6)
        self.assertEqual({p.face: p.corners for p in patches}, expected)
        for patch in patches:
            self.assertEqual(patch.source, [(0, 0), (1, 0), (1, 1), (0, 1)])

    def test_outer_size_kept(self):
        """INV-2."""
        bounds = (PS5.width / 2, PS5.height / 2, PS5.depth / 2)
        corners = [c for p in box_patches(PS5) for c in p.corners]
        for axis, bound in enumerate(bounds):
            values = [c[axis] for c in corners]
            self.assertLessEqual(max(abs(v) for v in values), bound + 1e-9)
            self.assertAlmostEqual(max(values), bound)
            self.assertAlmostEqual(min(values), -bound)

    def test_spine_shows_its_picture(self):
        """§ 4.1 (d): the spine side has no groove, so every flat patch on it
        shows the spine's picture, the seam's strip included."""
        w = PS5.width / 2
        on_spine = [p for p in box_patches(PS5)
                    if all(abs(c[0] + w) < 1e-9 for c in p.corners)]
        self.assertTrue(on_spine)
        for patch in on_spine:
            self.assertEqual(patch.face, "spine", patch.corners)

    def test_recess_is_cut_plain(self):
        """§ 4.1 (e): the slot is cut recess_depth into the opening side,
        recess_length long and recess_height high, centred on the case and
        the seam, with the seam's V along its floor, all in plain plastic."""
        shape = PS5.shape
        w = PS5.width / 2
        floor_x = w - shape.recess_depth
        # The side's straight run, between the front and back roundings.
        straight = PS5.depth / 2 - shape.lip_height - shape.edge_radius
        cut = [p for p in box_patches(PS5)
               if all(c[0] < w - 1e-9 and abs(c[1]) <= shape.recess_length / 2 + 1e-9
                      and abs(c[2]) < straight for c in p.corners)]
        corners = [c for p in cut for c in p.corners]
        self.assertAlmostEqual(max(c[1] for c in corners), shape.recess_length / 2)
        self.assertAlmostEqual(min(c[1] for c in corners), -shape.recess_length / 2)
        self.assertAlmostEqual(max(c[2] for c in corners), shape.recess_height / 2)
        self.assertAlmostEqual(min(c[2] for c in corners), -shape.recess_height / 2)
        self.assertAlmostEqual(min(c[0] for c in corners), floor_x - shape.seam_depth)
        self.assertTrue(any(abs(c[0] - floor_x) < 1e-9 for c in corners))
        for patch in cut:
            self.assertIsNone(patch.face, patch.corners)

    def test_closed_and_wound_outward(self):
        """INV-8."""
        box = PS5.width * PS5.height * PS5.depth
        for name, shape in SHAPES.items():
            with self.subTest(shape=name):
                patches = box_patches(replace(PS5, shape=shape))
                edges: dict[tuple, int] = {}
                for patch in patches:
                    self.assertGreaterEqual(len(patch.corners), 3)
                    keys = [_key(c) for c in patch.corners]
                    for a, b in zip(keys, keys[1:] + keys[:1], strict=True):
                        self.assertNotEqual(a, b, "a patch repeats a corner")
                        edges[(a, b)] = edges.get((a, b), 0) + 1
                for (a, b), count in edges.items():
                    self.assertEqual(count, 1, f"edge {a} -> {b} crossed {count} times")
                    self.assertEqual(edges.get((b, a)), 1, f"edge {a} -> {b} is open")
                volume = _signed_volume(patches)
                self.assertGreater(volume, 0.9 * box)
                self.assertLessEqual(volume, box + 1e-6)


if __name__ == "__main__":
    unittest.main()
