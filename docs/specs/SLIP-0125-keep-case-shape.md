<!-- ants-spec-format: 1 -->
# SLIP-0125 — Give the PS5 case its real shape and painted detail in the 3D viewer

**Status:** spec draft (2026-11-03).
**Kind:** implement.
**Source:** ROADMAP SLIP-0125 (user request 2026-11-03; shape format agreed
with the RetroDB session the same day).
**Amends:** SLIP-0104 § 4.1, § 4.5, INV-1 and INV-13
(`SLIP-0104-turnable-3d-box.md`).
**Pairs with:** RetroDB PASS-59-231, which draws the same shape.

**Layman:** Turn a PS5 case in the 3D viewer and it looks like the real one:
rounded corners and edges, and the seam where the two halves meet.

## 1. Goal

A PS5 case in Slipcase's 3D viewer has rounded corners and rounded edges,
and its top, bottom and opening side show the seam where the case's halves
meet. The box file carries the shape as two measurements, so RetroDB draws
the same case. Every other case, and every older RetroDB, behaves exactly as
today.

## 2. Problem

1. The viewer draws a cuboid. `_face_corners` in `ui/box_viewer.py` gives six
   flat rectangles, and `BoxViewer.paintEvent` maps one picture onto each. A
   real keep case has no square corner or edge (the user's PS4 and PS5
   photos, 2026-11-03).
2. A wrap case's top, bottom and opening side are flat colours.
   `build_box_model` in `core/box_model.py` leaves `top_face`, `bottom_face`
   and `edge_face` as None for the wrap layout, so the seam never shows.
3. The box file cannot say what shape a case is. RetroDB reads it
   (SLIP-0104 § 4.1), so a shape only Slipcase knew would make the two apps
   show different boxes.

## 3. Scope decisions (agreed with the user)

- **Real shape and painted detail together, worked out with RetroDB.** The
  user, 2026-11-03, chose this over painted detail first.
- **PS5 first.** The user, 2026-11-03: "Let's test PS5 for now", then other
  cases from reference photos or research.
- **The size stays 135 × 171.5 × 13 mm.** The user, 2026-11-03, kept the
  sourced figure over a seller photo's 170 × 135 × 10.
- **The case does not open; the two-disc case waits.** The user, 2026-11-03:
  opening is "a later feature" (SLIP-0109); the two-disc case comes with it
  (SLIP-0126).
- **Shape is named measurements in an optional section of box file
  version 1.** RetroDB, 2026-11-03: every released RetroDB (3.34.0 to
  3.35.4) refuses a version other than 1 but ignores unknown keys, and its
  CSS 3D viewer can draw parameters at its own fidelity where a mesh would
  force WebGL. Absent or zero means flat.

## 4. Design

### 4.1 The shape, in the box file

`S.box.json` gains one optional top-level key. Version stays 1.

```json
"shape": {"corner_radius_mm": 3, "edge_radius_mm": 1}
```

```
 Seen from the front, spine on the left (SLIP-0104 § 4.1's orientation):

  (a)                                         (a)
   .--------------------------------------------.
   |                                            |
   |                 front                      |
   |                                            |
   '--------------------------------------------'
  (a)                                         (a)

 Cut across the case, seen from the top:

        spine     front                       opening
          .-(b)------------------------------(b)-.
          |                                      |
          '-(b)------------------------------(b)-'
                  back
```

- **(a) `corner_radius_mm`** rounds the four corners of the outline seen
  from the front, through the whole depth.
- **(b) `edge_radius_mm`** rounds the eight edges where the front and the
  back meet the four sides, the two hinge edges included.
- **The outer size stays `case`'s.** Rounding takes material away; nothing
  stands outside the box.
- **Pictures.** Every flat part shows its face's picture at its own
  position. Each viewer decides how much detail the rounded parts get;
  plain plastic in `colours` is always allowed.

**Reading rules for `shape`**, added to SLIP-0104 § 4.1's: a missing `shape`
means flat. Each value must be a number, at least 0. `corner_radius_mm` is
at most a quarter of the smaller of `width_mm` and `height_mm`;
`edge_radius_mm` at most a quarter of `depth_mm`. A `shape` that is not an
object, lacks a key, or breaks a limit is ignored whole and the box is drawn
flat. It never refuses the file: a wrong decoration is no reason to lose a
box.

### 4.2 Where the shape comes from

```python
@dataclass(frozen=True)
class CaseShape:                 # core/case_types.py
    corner_radius: float         # mm, as § 4.1 (a)
    edge_radius: float           # mm, as § 4.1 (b)

CaseType.shape: CaseShape | None = None
```

Only "PS5 Blu-ray Case" sets it, at working figures: `corner_radius` 3.0 mm,
measured from the user's straight-on PS5 photo against the case's 135 mm
width (2026-11-03), an estimate; `edge_radius` 1.0 mm, judged by eye from
the closed-case photos. No published source gives either (research
2026-11-03). The user's by-eye check sets them.

`write_box_file` writes `"shape"` when `case_type.shape` is set, with both
keys in mm, and leaves it out otherwise. `read_box_file` applies § 4.1's
rules and puts the result on the `CaseType` it builds.

### 4.3 Painted detail

For a wrap case with `shape` set and `show_texture` on, `build_box_model`
also makes `top_face`, `bottom_face` and `edge_face`. Each is the bare
plastic at the front's px/mm, with the seam where the halves meet: a fine
dark line with a lit line beside it, along the full length, at half the
depth. The front half is a shade lighter, as the lid catches more light in
the photos. Line widths and shades are judged by eye. They follow
`show_texture` as every overlay does (SLIP-0104 INV-11). The front, spine
and back pictures are unchanged; their painted lip, with its shaded inner
wall (`inset_in_rim` in `core/image_utils.py`), stays the lip.

New in `core/case_texture.py`:

```python
def generate_keep_side(case_type: CaseType, plastic: tuple[int, int, int],
                       length: int, depth: int) -> Image.Image: ...
```

### 4.4 Drawing the shape

New `core/box_shape.py`, with no Qt, so it can be tested alone:

```python
@dataclass
class Patch:
    corners: list[Vec]            # 3D, mm, wound so the normal points out
    face: str | None              # the face whose picture it shows, or None
    source: list[tuple[float, float]] | None  # its corners in that picture, 0..1
    colour: str                   # "top", "bottom" or "edge": fill when face is None

def box_patches(case_type: CaseType) -> list[Patch]: ...
```

With `shape` None, `box_patches` gives the six faces `_face_corners` gives
today; that function moves into this module. With a shape, it builds the
solid from rings of the rounded outline, front to back. Each ring is the
outline inset by the edge rounding at its depth, its corner radius reduced
by the same inset and never below 0. Quads join the rings; the front and
back faces are flat caps. Eight segments a corner and three an edge
rounding are the starting figures.

The solid is convex, so SLIP-0104 § 4.5's rule still holds: the viewer
draws only patches turned towards the camera, and none of them overlap. A
flat part is drawn with `QTransform.quadToQuad` from its face's plane and
clipped to the part, so one picture spans its face. A rounded patch next to
a picture continues that picture's border pixels; others are plain
plastic. `visible_faces` still names the faces whose flat parts face the
camera.

The still render (`BoxRenderer.render`) does not use the shape.

## 5. Invariants

- **INV-1** — A case with no shape draws exactly as SLIP-0104: `box_patches`
  returns six patches whose corners equal today's `_face_corners`.
  *Test:* `tests/test_box_shape.py::test_no_shape_is_six_faces`, on
  "PS4 Blu-ray Case", against corners copied from today's code.
  *Breaks when:* the shaped path runs for an unshaped case, or the move
  changes a corner's order.

- **INV-2** — A shaped box keeps the case's outer size: every patch corner
  lies within ±width/2, ±height/2 and ±depth/2, and each of those six bounds
  is reached.
  *Test:* `tests/test_box_shape.py::test_outer_size_kept`, on the PS5 case.
  *Breaks when:* a rounding is added outside the outline, or a cap is
  placed short of the depth.

- **INV-3** — The shaped solid is closed and convex, wound outward: every
  patch's normal points away from the box's centre, and every edge is
  shared by exactly two patches.
  *Test:* `tests/test_box_shape.py::test_closed_and_outward`.
  *Breaks when:* a ring is joined in the wrong order, so the viewer culls
  a side facing the camera; or a gap is left between a cap and its ring.

- **INV-4** — A written box file is still version 1 with SLIP-0104's keys,
  plus `shape` exactly when the case has one; with `shape` deleted from the
  JSON, the file reads whole and flat.
  *Test:* `tests/test_box_file.py::test_shape_written` and
  `::test_shape_is_optional`.
  *Breaks when:* the version is raised, or a reader requires `shape`.

- **INV-5** — A `shape` that breaks § 4.1's rules is ignored whole and the
  rest of the file reads.
  *Test:* `tests/test_box_file.py::test_bad_shape_ignored`, one fixture per
  rule: not an object, a missing key, a string value, −1, and a corner
  radius above a quarter of the width. Each reads, with `case_type.shape`
  None.
  *Breaks when:* a bad shape refuses the file, or a value over its limit is
  clamped instead of ignored.

- **INV-6** — With a shape and `show_texture` set, a wrap model has a
  `top_face`, `bottom_face` and `edge_face`; with `show_texture` clear, or
  with no shape, it has none.
  *Test:* `tests/test_box_model.py::test_keep_sides_follow_texture`.
  *Breaks when:* the sides are made regardless of `show_texture`, or for an
  unshaped case.

- **INV-7** — The still render ignores the shape: rendering the PS5 case
  with its shape and with `shape` set to None gives the same pixels.
  *Test:* `tests/test_renderer.py::test_render_ignores_shape`.
  *Breaks when:* `render` reads `case_type.shape`.

SLIP-0104's INV-7 (visible faces) and INV-12 (nothing outside the box) still
bind the viewer, and their tests run unchanged.

## 6. Failure modes

- **Painting is too slow for auto-spin.** A shaped PS5 box is a few hundred
  patches. If a frame takes longer than the spin's timer interval
  (`_SPIN_INTERVAL_MS`), the segment counts drop before anything else
  changes.
- **A tiny face picture.** A clip at sub-pixel size draws nothing; that
  costs detail, not correctness.
- **RetroDB draws less.** Its viewer draws at its own fidelity (§ 4.1), so
  the two apps can differ in the rounded parts; the size and the pictures
  agree.

## 7. Tests

- INV-1, INV-2, INV-3 — `tests/test_box_shape.py`, a new file listed in
  `.indie-review/partition.json`.
- INV-4, INV-5 — `tests/test_box_file.py`.
- INV-6 — `tests/test_box_model.py`.
- INV-7 — `tests/test_renderer.py`.

Each is new and is seen failing before its code exists. The look has no
automated check: the user compares the viewer with their photos.

## 8. Alternatives considered (and rejected)

- **A mesh in the box file.** Rejected by RetroDB: it needs WebGL there and
  ties both apps to one geometry pipeline.
- **Box file version 2.** Rejected: every released RetroDB refuses it, while
  version 1 with an extra key loads everywhere.
- **A raised lip as shape.** Rejected: the lip has no hinge side, so a
  raised one steps at the hinge and makes the solid concave, which needs
  depth sorting in both viewers. It is about half a millimetre, unsourced,
  and already painted with a shaded inner wall.
- **OpenGL or Qt Quick 3D in Slipcase.** Rejected: a new dependency, and
  SLIP-0104 chose `QPainter`. A convex solid needs only culling.
- **Painted detail only.** The user chose both, 2026-11-03.
- **Refusing a box file with a bad shape.** Rejected: a wrong decoration
  should not lose the box.

## 9. Out of scope

- Opening the case — tracked by SLIP-0109.
- The two-disc PS5 case — tracked by SLIP-0126.
- PS4, PS3, Xbox One and the other cases — deferred; not yet queued. They
  follow the user's check of the PS5 case and reference photos.
- The tray and disc seen through the plastic — deferred; not yet queued.
  With a game in the case, the back cover hides them.
- Moulded marks on the edges — deferred; not yet queued. No source.
- The shape in the still render — deferred; not yet queued.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 | `tests/test_box_shape.py::test_no_shape_is_six_faces` |
| INV-2 | `tests/test_box_shape.py::test_outer_size_kept` |
| INV-3 | `tests/test_box_shape.py::test_closed_and_outward` |
| INV-4 | `tests/test_box_file.py::test_shape_written`, `::test_shape_is_optional` |
| INV-5 | `tests/test_box_file.py::test_bad_shape_ignored` |
| INV-6 | `tests/test_box_model.py::test_keep_sides_follow_texture` |
| INV-7 | `tests/test_renderer.py::test_render_ignores_shape` |
| § 4.2's working figures | **nothing** — no source exists; the user's by-eye check |
| § 6 frame time | **nothing** — judged while auto-spin runs |

## 11. Cross-doc impact

- `SLIP-0104-turnable-3d-box.md`: § 4.1 gains the `shape` key, pointing
  here; § 4.5 names `box_patches` as what is drawn; INV-1 and INV-13 are
  annotated (§ 13).
- `CHANGELOG.md`: Added, under Unreleased.
- RetroDB: the session is sent this path; PASS-59-231 builds from § 4.1.

## 12. Cold-eyes loop log

Rows live in `../reviews/SLIP-0125-keep-case-shape-loop-log.md`.

## 13. Migration / compatibility

- Box files written before this have no `shape` and draw flat, as before.
- A shaped file loads in every released RetroDB, which ignores `shape` and
  draws six flat faces with the same pictures (RetroDB, 2026-11-03). Those
  builds drop the key at import, so a box imported there must be imported
  again to gain its shape.
- SLIP-0104 INV-1 ("exactly § 4.1's keys") now allows the optional `shape`.
  SLIP-0104 INV-13 ("a wrap box file writes `"edge": null`") now holds for
  wrap cases without a shape, or with `show_texture` clear.

## 14. Open questions

- The working figures in § 4.2, until the user's check.
