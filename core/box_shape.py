"""The solid the 3D viewer draws, cut into flat patches (SLIP-0125 § 4.4).

No Qt here, so the shape can be tested alone. Coordinates are millimetres
with the box centred on the origin: x runs across the front, y up, z out of
the front. The spine is the x = -width/2 side, the opening side x = +width/2.

Every patch is wound clockwise as seen from outside the box, as a face's
corners run top left, top right, bottom right, bottom left of its picture.
patch_normal turns that winding into the outward normal.

A shaped case is built from rings running round the outline, from the front
sheet over the front lip, down the side, through the seam and up over the
back lip to the back sheet. Each ring gives every side an inset from the
outline and a height: the top, bottom and opening side share one profile,
with the lip and the seam; the spine side has its own, with neither.
Round a corner a ring passes from one side's values to the other's.

A finger recess cuts into the opening side across the seam: a slot whose
ends are square, half-round or between, set above or below the side's
middle by its offset. Every ring carries four more points on that side, where
the slot's ends lie at that ring's height; rings above and below the slot
carry them uncut, so every ring has as many points as the next.
"""

import math
from dataclasses import dataclass

from core.case_types import CaseShape, CaseType

Vec = tuple[float, float, float]

# Starting figures (SLIP-0125 § 4.4); § 6 lowers them if a frame is too slow.
CORNER_SEGMENTS = 8
EDGE_SEGMENTS = 3
RECESS_SEGMENTS = 4             # per rounded corner of the slot's ends
_SAME_MM = 1e-9

_FULL_PICTURE = [(0, 0), (1, 0), (1, 1), (0, 1)]
_FACE_NORMALS: dict[str, Vec] = {
    "front": (0.0, 0.0, 1.0), "back": (0.0, 0.0, -1.0),
    "spine": (-1.0, 0.0, 0.0), "edge": (1.0, 0.0, 0.0),
    "top": (0.0, 1.0, 0.0), "bottom": (0.0, -1.0, 0.0),
}


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _same(a: Vec, b: Vec) -> bool:
    return max(abs(x - y) for x, y in zip(a, b, strict=True)) <= _SAME_MM


@dataclass
class Patch:
    """One flat or nearly flat piece of the box's surface.

    `source` holds each corner's place in `face`'s picture, 0..1 across and
    down; None when `face` is None. `colour` names the plain colour that
    fills the patch when it shows no picture.
    """
    corners: list[Vec]
    face: str | None
    source: list[tuple[float, float]] | None
    colour: str


def face_corners(case_type: CaseType) -> dict[str, list[Vec]]:
    """Each face's corners as seen from outside the box: top left, top
    right, bottom right, bottom left of its picture."""
    w, h, d = case_type.width / 2, case_type.height / 2, case_type.depth / 2
    return {
        "front": [(-w, h, d), (w, h, d), (w, -h, d), (-w, -h, d)],
        "back": [(w, h, -d), (-w, h, -d), (-w, -h, -d), (w, -h, -d)],
        "spine": [(-w, h, -d), (-w, h, d), (-w, -h, d), (-w, -h, -d)],
        "edge": [(w, h, d), (w, h, -d), (w, -h, -d), (w, -h, d)],
        "top": [(-w, h, -d), (w, h, -d), (w, h, d), (-w, h, d)],
        "bottom": [(-w, -h, d), (w, -h, d), (w, -h, -d), (-w, -h, -d)],
    }


def patch_normal(corners: list[Vec]) -> Vec:
    """The outward unit normal of a patch wound as this module winds them,
    by Newell's method so a corner patch that is not quite flat still gets
    its average; (0, 0, 0) for a patch with no area."""
    nx = ny = nz = 0.0
    for (x0, y0, z0), (x1, y1, z1) in zip(corners, corners[1:] + corners[:1], strict=True):
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length < _SAME_MM:
        return (0.0, 0.0, 0.0)
    # Newell's normal follows the right-hand rule; these patches run clockwise.
    return (-nx / length, -ny / length, -nz / length)


def _colour(face: str | None, normal: Vec) -> str:
    """The plain colour for a patch: its face's, else its side's."""
    if face is None:
        face = max(("edge", "top", "bottom", "spine"),
                   key=lambda f: _dot(normal, _FACE_NORMALS[f]))
    return face if face in ("top", "bottom") else "edge"


def _source(face: str, corners: list[Vec],
            faces: dict[str, list[Vec]]) -> list[tuple[float, float]]:
    """Each corner's place in `face`'s picture, straight below it on the
    face's plane, held to the picture."""
    tl, tr, _br, bl = faces[face]
    across = tuple(b - a for a, b in zip(tl, tr, strict=True))
    down = tuple(b - a for a, b in zip(tl, bl, strict=True))
    result = []
    for corner in corners:
        rel = tuple(c - o for c, o in zip(corner, tl, strict=True))
        u = _dot(rel, across) / _dot(across, across)
        v = _dot(rel, down) / _dot(down, down)
        result.append((min(1.0, max(0.0, u)), min(1.0, max(0.0, v))))
    return result


def _has_recess(shape: CaseShape) -> bool:
    return shape.recess_length > 0 and shape.recess_height > 0 and shape.recess_depth > 0


# One ring: its (inset, height) on the lip sides and on the spine side, and
# how far the finger recess's cut reaches each way from the middle at that
# height, or None where the ring runs above or below the slot.
Ring = tuple[tuple[float, float], tuple[float, float], float | None]


def _profiles(shape: CaseShape, d: float) -> list[Ring]:
    """The rings, front sheet to back sheet, `d` being half the depth."""
    r, sw = shape.edge_radius, shape.seam_width
    lip = shape.lip_height > 0
    t = shape.lip_height if lip else 0.0
    front: list[tuple[tuple[float, float], tuple[float, float]]] = []
    if lip:
        # The lip's inner wall, bottom then top; on the spine side the sheet
        # runs straight to the rounding, so these rings sit where it starts.
        front.append(((shape.lip_width, d - t), (r, d - t)))
        front.append(((shape.lip_width, d), (r, d - t)))
    steps = EDGE_SEGMENTS if r > 0 else 0
    for k in range(steps, -1, -1):
        theta = math.pi / 2 * k / steps if steps else 0.0
        inset = r * (1 - math.cos(theta)) if k != steps else r
        rise = r * math.sin(theta) if k != steps else r
        front.append(((inset, d - r + rise), (inset, d - t - r + rise)))
    back = [((li, -lz), (si, -sz)) for (li, lz), (si, sz) in reversed(front)]
    # The straight run between the two roundings: the seam, and the slot.
    seam = []
    if sw > 0:
        seam = [((0.0, sw / 2), (0.0, sw / 2)), ((shape.seam_depth, 0.0), (0.0, 0.0)),
                ((0.0, -sw / 2), (0.0, -sw / 2))]
    if not _has_recess(shape):
        straight: list[Ring] = [(lip_side, spine_side, None) for lip_side, spine_side in seam]
    else:
        end, rho = shape.recess_height / 2, shape.recess_end_radius
        flat = end - rho    # the slot's ends run straight up to here each way

        def reach(z: float) -> float:
            past = max(0.0, abs(z) - flat)
            return shape.recess_length / 2 - rho + math.sqrt(max(0.0, rho * rho - past * past))

        # Rings round each end's two rounded corners, top then bottom; a
        # square end needs only its top and bottom rings.
        arc = [flat + rho * math.cos(math.pi / 2 * j / RECESS_SEGMENTS)
               for j in range(RECESS_SEGMENTS + 1)]
        levels: list[float] = []
        for z in arc + [-z for z in reversed(arc)]:
            if not levels or levels[-1] - z > _SAME_MM:
                levels.append(z)
        # Levels inside the seam would cut its V; the seam's own rings stand in.
        cut = [((0.0, z), (0.0, z)) for z in levels if sw == 0 or abs(z) > sw / 2 + _SAME_MM]
        inside = sorted(cut + seam, key=lambda ring: -ring[0][1])
        straight = ([((0.0, end), (0.0, end), None)]
                    + [(lip, spine, reach(lip[1])) for lip, spine in inside]
                    + [((0.0, -end), (0.0, -end), None)])
    return ([(lip_side, spine_side, None) for lip_side, spine_side in front]
            + straight
            + [(lip_side, spine_side, None) for lip_side, spine_side in back])


def _arc(j: int) -> tuple[float, float]:
    """cos and sin of the j-th of CORNER_SEGMENTS steps through a quarter
    turn, exact at both ends so neighbouring rings meet."""
    if j == 0:
        return (1.0, 0.0)
    if j == CORNER_SEGMENTS:
        return (0.0, 1.0)
    a = math.pi / 2 * j / CORNER_SEGMENTS
    return (math.cos(a), math.sin(a))


def _ring(case_type: CaseType, ring: Ring) -> list[Vec]:
    """One ring, anticlockwise as seen from the front, starting at the top
    of the opening side; with a recess, its four points close the ring."""
    lip_side, spine_side, reach = ring
    shape = case_type.shape
    w, h = case_type.width / 2, case_type.height / 2
    radius = shape.corner_radius
    points: list[Vec] = []
    # (x sign, y sign, does the arc run from the x side to the y side?)
    for sx, sy, x_first in ((1, 1, True), (-1, 1, False), (-1, -1, True), (1, -1, False)):
        ix, zx = spine_side if sx < 0 else lip_side
        iy, zy = lip_side
        cx = sx * (w - max(radius, ix))
        cy = sy * (h - max(radius, iy))
        rx, ry = max(0.0, radius - ix), max(0.0, radius - iy)
        for j in range(CORNER_SEGMENTS + 1):
            c, s = _arc(j if x_first else CORNER_SEGMENTS - j)
            # c is 1 on the x side and 0 on the y side; c*c eases between.
            z = zx if zx == zy else zx * c * c + zy * (1 - c * c)
            points.append((cx + sx * rx * c, cy + sy * ry * s, z))
    if _has_recess(shape):
        x, z = w - lip_side[0], lip_side[1]
        if reach is None:
            # Uncut: the points sit where the slot's straight edges end.
            reach, floor = shape.recess_length / 2 - shape.recess_end_radius, x
        else:
            floor = x - shape.recess_depth
        mid = shape.recess_offset
        points += [(x, mid - reach, z), (floor, mid - reach, z),
                   (floor, mid + reach, z), (x, mid + reach, z)]
    return points


def _clean(corners: list[Vec]) -> list[Vec]:
    """`corners` without a corner repeating the one before it."""
    kept: list[Vec] = []
    for corner in corners:
        if not kept or not _same(corner, kept[-1]):
            kept.append(corner)
    while len(kept) > 1 and _same(kept[0], kept[-1]):
        kept.pop()
    return kept


def box_patches(case_type: CaseType) -> list[Patch]:
    """The patches a viewer draws for `case_type`: its six faces when it has
    no shape, else its shaped surface (SLIP-0125 § 4.4)."""
    faces = face_corners(case_type)
    shape = case_type.shape
    if shape is None:
        return [Patch(corners, face, list(_FULL_PICTURE), _colour(face, (0.0, 0.0, 0.0)))
                for face, corners in faces.items()]

    profiles = _profiles(shape, case_type.depth / 2)
    rings = [_ring(case_type, ring) for ring in profiles]
    n = len(rings[0])
    # The lips' inner walls and the seam's two faces show plain plastic,
    # but on the spine side, where the seam runs flat, the picture.
    last = len(rings) - 2
    plain = {0, last} if shape.lip_height > 0 else set()
    seam = set()
    if shape.seam_width > 0:
        middle = next(i for i, (lip_side, _, _) in enumerate(profiles)
                      if lip_side == (shape.seam_depth, 0.0))
        seam = {middle - 1, middle}
    # The recess's walls and floor: the three quads between its four points.
    recess_quads = {n - 4, n - 3, n - 2} if _has_recess(shape) else set()

    pieces: list[tuple[list[Vec], str]] = [(list(reversed(rings[0])), "face")]
    for band, (a, b) in enumerate(zip(rings, rings[1:], strict=False)):
        in_recess = profiles[band][2] is not None or profiles[band + 1][2] is not None
        for k in range(n):
            quad = [a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]]
            if band in plain or (in_recess and k in recess_quads):
                kind = "plain"
            else:
                kind = "seam" if band in seam else "face"
            pieces.append((quad, kind))
    pieces.append((list(rings[-1]), "face"))

    patches = []
    for raw, kind in pieces:
        corners = _clean(raw)
        if len(corners) < 3:
            continue
        normal = patch_normal(corners)
        face = None
        if kind != "plain" and normal != (0.0, 0.0, 0.0):
            face = max(_FACE_NORMALS, key=lambda f: _dot(normal, _FACE_NORMALS[f]))
            if kind == "seam" and _dot(normal, _FACE_NORMALS[face]) < 1 - _SAME_MM:
                face = None
        source = _source(face, corners, faces) if face is not None else None
        patches.append(Patch(corners, face, source, _colour(face, normal)))
    return patches
