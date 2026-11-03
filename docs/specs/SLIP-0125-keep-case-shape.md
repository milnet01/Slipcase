<!-- ants-spec-format: 1 -->
# SLIP-0125 — Give the PS5 case its real shape in the 3D viewer

**Status:** spec draft (2026-11-03); amended 2026-11-03, before any build,
to make the lip and the seam real shape; amended again 2026-11-03, after
the user's first look, to add the finger recess, and again after their
photo of the opening side, to centre it on the seam with round ends.
**Kind:** implement.
**Source:** ROADMAP SLIP-0125 (user request 2026-11-03; shape format agreed
with the RetroDB session the same day).
**Amends:** SLIP-0104 § 4.1, § 4.5, INV-1 and INV-13
(`SLIP-0104-turnable-3d-box.md`).
**Pairs with:** RetroDB PASS-59-231, which draws the same shape.

**Layman:** Turn a PS5 case in the 3D viewer and it looks like the real one:
rounded corners and edges, the raised lip round the cover, the groove
where the two halves meet, and the finger recess in the opening side.

## 1. Goal

A PS5 case in Slipcase's 3D viewer has rounded corners and rounded edges, a
raised plastic lip round the cover on its front and back, and a groove along
its top, bottom and opening side where the case's halves meet, and a finger
recess in its opening side. All of them
are shape, not paint. The box file carries the shape as named measurements,
so RetroDB draws the same case. Every other case, and every older RetroDB,
behaves exactly as today.

## 2. Problem

1. The viewer draws a cuboid. `_face_corners` in `ui/box_viewer.py` gives six
   flat rectangles, and `BoxViewer.paintEvent` maps one picture onto each. A
   real keep case has no square corner or edge (the user's PS4 and PS5
   photos, 2026-11-03).
2. The lip is paint. `inset_in_rim` in `core/image_utils.py` frames each
   picture in plastic and paints the lip's inner wall as a shaded band, so
   the lip has no height when the box turns. The seam is not drawn at all.
3. The box file cannot say what shape a case is. RetroDB reads it
   (SLIP-0104 § 4.1), so a shape only Slipcase knew would make the two apps
   show different boxes.

## 3. Scope decisions (agreed with the user)

- **Real shape and painted detail together, worked out with RetroDB.** The
  user, 2026-11-03, chose this over painted detail first.
- **The lip and the seam are shape, not paint.** The user, 2026-11-03, will
  use the feature only once it is complete, and asked for the finished
  shape rather than paint to be redone later. The seam is "most certainly
  visible in real life" (the user), and shows as a clear line on the closed
  case in the reference photos.
- **The opening side has its finger recess.** The user, 2026-11-03, after
  the first look: the real case has it. Their photo of the opening side
  shows a slot with round ends across the seam, and they confirmed it sits
  in the middle of the side.
- **The tray and disc stay out.** The user, 2026-11-03, agreed: with a game
  in the case, the cover hides them.
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
"shape": {"corner_radius_mm": 3, "edge_radius_mm": 1,
          "lip_width_mm": 2.5, "lip_height_mm": 0.5,
          "seam_width_mm": 0.8, "seam_depth_mm": 0.4,
          "recess_length_mm": 59, "recess_height_mm": 6,
          "recess_depth_mm": 1.5}
```

```
 Seen from the front, spine on the left (SLIP-0104 § 4.1's orientation):

  (a)                                         (a)
   .--------------------------------------------.
   | spine side: no lip   .--------------(c)--. |
   |                      |   sheet           | |
   |                      '-------------------' |
   '--------------------------------------------'
  (a)                                         (a)

 The opening side, cut across, outside on the right:

          |<- (c) width ->|
  front   _______________ .
  sheet  |                 '.  (b)
  _______|  (c) height       |
                             |
                             >  (d) at half the depth
                             |
  _______                   .'
  back   |_______________ .'   (b)
```

- **(a) `corner_radius_mm`** rounds the four corners of the outline seen
  from the front, through the whole depth.
- **(b) `edge_radius_mm`** rounds the eight edges where the front and the
  back meet the four sides. On the top, bottom and opening side it rounds
  the lip's outer edge; on the spine side, the edge between the sheet and
  the spine.
- **(c) `lip_width_mm` and `lip_height_mm`.** On the front and on the back,
  a lip `lip_width_mm` wide runs along the top, the bottom and the opening
  side, measured in from the outline. The sheet lies `lip_height_mm` below
  the lip's top. The lip's inner wall is straight. The spine side has no
  lip: the sheet runs to the spine's rounded edge, and the lip falls to the
  sheet's level round the curve of the spine-side corners.
- **(d) `seam_width_mm` and `seam_depth_mm`.** A V-shaped groove at half
  the depth, along the top, the bottom and the opening side:
  `seam_width_mm` wide at the surface, its deepest line `seam_depth_mm`
  in. The spine side has none.
- **(e) `recess_length_mm`, `recess_height_mm` and `recess_depth_mm`.** A
  finger slot cut into the opening side, centred top to bottom and on the
  seam. It is `recess_length_mm` long end to end and `recess_height_mm`
  high, and its ends are half-rounds of half that height. Its floor lies
  `recess_depth_mm` in from the side's surface, and the seam's groove runs
  on along the floor. Its walls are square to the side. With any of the
  three 0 there is no recess.
- **The outer size stays `case`'s.** Rounding and grooves take material
  away; the lip's top is the case's face. Nothing stands outside the box.
- **Pictures.** Each face's picture still spans its face's full outer
  rectangle, `case`'s size. Every flat part shows the region of that
  picture straight below it on the face's plane, cropped, never rescaled.
  Each viewer decides how much detail the rounded parts, the lip's walls
  and the groove get; plain plastic in `colours` is always allowed.

**Reading rules for `shape`**, added to SLIP-0104 § 4.1's: a missing `shape`
means flat. `corner_radius_mm` and `edge_radius_mm` are required; a missing
`lip_*`, `seam_*` or `recess_*` key means 0, so a shape written before
those features reads. Each value must be a number, not `true` or `false`, at least 0. A
value of 0 means that feature is absent; every value 0 is a flat box. The
limits:

- `corner_radius_mm` and `lip_width_mm`: at most a quarter of the smaller
  of `width_mm` and `height_mm`.
- `edge_radius_mm`: at most a quarter of `depth_mm`.
- `lip_height_mm` and `seam_width_mm`: at most an eighth of `depth_mm`.
- `seam_depth_mm`: at most `seam_width_mm`.
- With `lip_height_mm` above 0, `lip_width_mm` is above 0 and at least
  `edge_radius_mm`, so the rounding fits on the lip.
- `recess_length_mm`: less than `height_mm` minus twice the larger of
  `corner_radius_mm` and `lip_width_mm`, so the recess ends before the
  corners.
- `recess_depth_mm`: at most a quarter of the smaller of `width_mm` and
  `height_mm`.
- `recess_height_mm`: above 0 only when it is above `seam_width_mm` and
  below `recess_length_mm`, so the slot is taller than the seam and its
  round ends fit.
- Half `recess_height_mm`: less than half `depth_mm` minus `lip_height_mm`
  and `edge_radius_mm`, so the slot ends before the roundings.

A `shape` that is not an object, lacks a required key, or breaks a rule is
ignored whole and the box is drawn flat. It never refuses the file: a wrong
decoration is no reason to lose a box.

### 4.2 Where the shape comes from

```python
@dataclass(frozen=True)
class CaseShape:                 # core/case_types.py
    corner_radius: float         # mm, as § 4.1 (a)
    edge_radius: float           # mm, as § 4.1 (b)
    lip_width: float = 0.0       # mm, as § 4.1 (c)
    lip_height: float = 0.0
    seam_width: float = 0.0      # mm, as § 4.1 (d)
    seam_depth: float = 0.0
    recess_length: float = 0.0   # mm, as § 4.1 (e)
    recess_height: float = 0.0
    recess_depth: float = 0.0

CaseType.shape: CaseShape | None = None
```

Only "PS5 Blu-ray Case" sets it. Its figures are working estimates; no
published source gives any of them (research 2026-11-03):

- `corner_radius` 3.0 mm, measured from the user's straight-on PS5 photo
  against the case's 135 mm width (2026-11-03).
- `edge_radius` 1.0 mm, judged by eye from the closed-case photos.
- `lip_width` equal to the case's `rim_mm`, so the lip and the plastic
  frame in the pictures line up.
- `lip_height` 0.5 mm, unsourced.
- `seam_width` 0.8 mm and `seam_depth` 0.4 mm, from the closed case photo
  labelled 10 mm deep, where the seam's line is about a twentieth of the
  depth (2026-11-03).
- `recess_length` 59 mm, `recess_height` 6 mm and `recess_depth` 1.5 mm.
  The length and height are measured from the user's photo of their case's
  opening side, against its 13 mm depth (2026-11-03). The depth is
  unsourced.

The user's by-eye check sets them all.

`write_box_file` writes `"shape"` when `case_type.shape` is set, with all
nine keys in mm, and leaves it out otherwise. `read_box_file` applies § 4.1's
rules and puts the result on the `CaseType` it builds.

### 4.3 The painted lip gives way to the real one

For a wrap case whose shape has `lip_height` above 0, `build_box_model`
frames each picture as today but without the lip's painted inner wall: the
shape now casts it. `inset_in_rim` gains `wall: bool = True`; the model
passes False for such a case. The still render keeps the painted wall
(§ 4.4). The top, bottom and opening side get no pictures: `top_face`,
`bottom_face` and `edge_face` stay None for the wrap layout, as today.

### 4.4 Drawing the shape

New `core/box_shape.py`, with no Qt, so it can be tested alone:

```python
@dataclass
class Patch:
    corners: list[Vec]            # 3D, mm, wound so the normal points out
    face: str | None              # the face whose picture it shows, or None
    source: list[tuple[float, float]] | None  # its corners in that picture, 0..1
    colour: str                   # "top", "bottom" or "edge": fill when face is None

def face_corners(case_type: CaseType) -> dict[str, list[Vec]]: ...
def box_patches(case_type: CaseType) -> list[Patch]: ...
```

`face_corners` is today's `_face_corners`, moved from `ui/box_viewer.py`.
With `shape` None, `box_patches` gives the six faces it gives. With a shape,
it builds the solid from rings running round the outline, front to back.
Each side has a profile: the inset from the outline and the height of each
ring on that side. The top, bottom and opening side share one, with the
lip, its rounding and the groove; the spine side has its own, with neither.
Round a corner, a ring's inset and height pass from one side's value to
the other's. With a recess, the rings carry four more points on the
opening side, where the slot's ends lie at that ring's height: cut in for
the rings across the slot, uncut for the rest. Rings at four steps a
quarter turn shape the slot's round ends; the seam's own rings stand in
for those that would fall inside the seam. Quads join the rings; the two sheets are flat
caps. Eight
segments a corner and three an edge rounding are the starting figures.

Each patch shows the picture of the face its outward direction is nearest
to, at its region straight below it on that face's plane. A lip's inner
wall shows the lip top beside it. The groove's walls and the recess show
plain plastic; on the spine side the seam's strip is flat, and shows the
spine's picture. The viewer joins the strips lying flat on one face's
plane and draws that face's picture once over them, so no line shows where
two strips meet. Slipcase's viewer maps a picture onto the
flat parts and onto the long straight strips, and fills small patches with
their region's average colour.

The solid is not convex: the lip stands above the sheet, and the groove
dips into the sides. So SLIP-0104 § 4.5's "no sorting" no longer holds for
a shaped box. The viewer draws only patches turned towards the camera. At
most one sheet faces the camera, as the two face opposite ways. The viewer
draws what lies behind that sheet's plane, then the sheet, then what stands
in front of it; each group from the farthest centre to the nearest. The
plane decides exactly what the sheet hides: the back lip's inner walls face
the camera from behind the front sheet, and drawn after it they show
through it. Within a group the patches are small, so sorting them by centre
goes wrong only at their joins, if at all; the by-eye check judges that
(§ 6). `visible_faces` still names the faces whose outer rectangle
faces the camera.

The still render (`BoxRenderer.render`) does not use the shape, and keeps
its painted lip.

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

- **INV-3** — *Withdrawn 2026-11-03: the lip and the groove make the solid
  concave (§ 4.4). INV-8 replaces it.* The shaped solid is closed and
  convex, wound outward: every patch's normal points away from the box's
  centre, and every edge is shared by exactly two patches.
  *Test:* `tests/test_box_shape.py::test_closed_and_outward`, which also
  checks that no patch corner lies in front of another patch's plane.
  *Breaks when:* a ring is joined in the wrong order, so the viewer culls
  a side facing the camera; a gap is left between a cap and its ring; or
  the rings' insets are out of order, so the solid is concave.

- **INV-4** — A written box file is still version 1 with SLIP-0104's keys,
  plus `shape` exactly when the case has one; with `shape` deleted from the
  JSON, the file reads whole and flat.
  *Test:* `tests/test_box_file.py::test_shape_written` and
  `::test_shape_is_optional`.
  *Breaks when:* the version is raised, or a reader requires `shape`.
  *Amended 2026-11-03:* a `shape` with only `corner_radius_mm` and
  `edge_radius_mm` reads, with the lip and seam 0
  (`::test_two_key_shape_reads`). Amended again the same day: the recess
  is 0 too.

- **INV-5** — A `shape` that breaks § 4.1's rules is ignored whole and the
  rest of the file reads.
  *Test:* `tests/test_box_file.py::test_bad_shape_ignored`, one fixture per
  rule: not an object, a missing key, a string value, `true`, −1, a corner
  radius above a quarter of the width, and an edge radius above a quarter
  of the depth. Each reads, with `case_type.shape` None.
  *Breaks when:* a bad shape refuses the file, or a value over its limit is
  clamped instead of ignored.
  *Amended 2026-11-03:* the same test also carries one fixture per new
  rule: a lip height and a seam width above an eighth of the depth, a seam
  depth above its width, a lip width above a quarter of the width, a lip
  narrower than the edge rounding, and `true` and −1 in a lip or seam key.
  Amended again the same day: a recess reaching the corners, deeper than a
  quarter of the width, reaching the roundings, no longer than its height,
  no taller than the seam, and `true` in a recess key.

- **INV-6** — *Withdrawn 2026-11-03: the seam is shape, so the sides get no
  pictures (§ 4.3). INV-9 replaces it.* With a shape and `show_texture` set,
  a wrap model has a
  `top_face`, `bottom_face` and `edge_face`; with `show_texture` clear, or
  with no shape, it has none.
  *Test:* `tests/test_box_model.py::test_keep_sides_follow_texture`.
  *Breaks when:* the sides are made regardless of `show_texture`, or for an
  unshaped case.

- **INV-7** — The still render ignores the shape: rendering the PS5 case
  with its shape and with `shape` set to None gives the same pixels.
  *Test:* `tests/test_renderer.py::test_render_ignores_shape`.
  *Breaks when:* `render` reads `case_type.shape`.

- **INV-8** — The shaped solid is closed and wound outward: every edge is
  shared by exactly two patches, which cross it in opposite directions, and
  the volume they enclose is positive and below the outer box's.
  *Test:* `tests/test_box_shape.py::test_closed_and_wound_outward`, on the
  PS5 case and on shapes with no lip, no seam, square corners, corners
  tighter than the lip, and a recess with no seam.
  *Breaks when:* a ring is joined in the wrong order, so the viewer culls a
  side facing the camera; a gap is left between a cap and its ring; or a
  corner's passage from one side's profile to the other leaves a hole.

- **INV-9** — A wrap case whose shape has a lip gets pictures framed without
  the painted inner wall; a case without a shape gets today's pictures.
  Every shaped case's `lip_width` equals its `rim_mm`.
  *Test:* `tests/test_box_model.py::test_lip_replaces_painted_wall`, which
  reads the row just inside the top of the frame in the PS5 front: plain
  plastic with the shape, the wall's shade with `shape` set to None; and
  `::test_lip_width_is_rim_width`, over every case in `CASE_TYPES`.
  *Breaks when:* the wall is painted under a real lip, or a lip width
  drifts from the frame it should cover.

- **INV-10** — The recess is cut where § 4.1 (e) puts it, in plain plastic,
  and the spine shows its picture whole.
  *Test:* `tests/test_box_shape.py::test_recess_is_cut_plain`: on the PS5
  case, the patches cut into the side's straight run span
  `recess_length` top to bottom and `recess_height` centred on the seam,
  reach `recess_depth` in plus the seam's depth, and show no picture;
  `::test_spine_shows_its_picture`: every patch flat on the spine shows the
  spine's picture; and
  `tests/test_box_viewer.py::test_flat_spine_drawn_whole`: a picture
  running dark to light across the spine draws with no dip where two
  strips meet.
  *Breaks when:* the recess is cut off centre or at the wrong size, takes a
  face's picture, the seam strip on the spine is drawn plain, or the
  spine's strips are drawn apart.

SLIP-0104's INV-7 (visible faces) and INV-12 (nothing outside the box) still
bind the viewer, and their tests run unchanged.

## 6. Failure modes

- **Painting is too slow for auto-spin.** A shaped PS5 box is a few hundred
  patches. If a frame takes longer than the spin's timer interval
  (`_SPIN_INTERVAL_MS`), the segment counts drop before anything else
  changes.
- **A patch drawn in the wrong order.** Sorting by centre can draw a patch
  over a nearer one where two meet. The patches are small, so a mistake
  shows as a sliver at a join. The by-eye check looks for one; if it shows,
  the segment counts rise round the lip.
- **A tiny face picture.** A clip at sub-pixel size draws nothing; that
  costs detail, not correctness.
- **RetroDB draws less.** Its viewer draws at its own fidelity (§ 4.1), so
  the two apps can differ in the rounded parts; the size and the pictures
  agree.

## 7. Tests

- INV-1, INV-2, INV-8, INV-10 — `tests/test_box_shape.py`; INV-10 also
  `tests/test_box_viewer.py`, a new file listed in
  `.indie-review/partition.json`.
- INV-4, INV-5 — `tests/test_box_file.py`.
- INV-9 — `tests/test_box_model.py`.
- INV-3 and INV-6 — withdrawn (§ 5); INV-8 and INV-9 replace them.
- INV-7 — `tests/test_renderer.py`.

Each is new and is seen failing before its code exists. The look has no
automated check: the user compares the viewer with their photos.

## 8. Alternatives considered (and rejected)

- **A mesh in the box file.** Rejected by RetroDB: it needs WebGL there and
  ties both apps to one geometry pipeline.
- **Box file version 2.** Rejected: every released RetroDB refuses it, while
  version 1 with an extra key loads everywhere.
- **A painted lip and seam.** The first draft chose them, as a raised lip
  makes the solid concave. The user, 2026-11-03, chose the finished shape
  instead (§ 3); the draw order in § 4.4 handles the concave solid.
- **Painted sides with the seam** (`generate_keep_side`). Dropped with the
  painted seam: the groove is shape.
- **OpenGL or Qt Quick 3D in Slipcase.** Rejected: a new dependency, and
  SLIP-0104 chose `QPainter`. Culling and a centre sort draw this solid.
- **Painted detail only.** The user chose both, 2026-11-03.
- **Refusing a box file with a bad shape.** Rejected: a wrong decoration
  should not lose the box.

## 9. Out of scope

- Opening the case — tracked by SLIP-0109.
- The two-disc PS5 case — tracked by SLIP-0126.
- PS4, PS3, Xbox One and the other cases — deferred; not yet queued. They
  follow the user's check of the PS5 case and reference photos.
- The tray and disc seen through the plastic — deferred; not yet queued.
  With a game in the case, the cover hides them (the user agreed,
  2026-11-03).
- Moulded marks on the edges — deferred; not yet queued. No source.
- The shape in the still render — deferred; not yet queued.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 | `tests/test_box_shape.py::test_no_shape_is_six_faces` |
| INV-2 | `tests/test_box_shape.py::test_outer_size_kept` |
| INV-3 | withdrawn — see INV-8 |
| INV-4 | `tests/test_box_file.py::test_shape_written`, `::test_shape_is_optional`, `::test_two_key_shape_reads` |
| INV-5 | `tests/test_box_file.py::test_bad_shape_ignored` |
| INV-6 | withdrawn — see INV-9 |
| INV-7 | `tests/test_renderer.py::test_render_ignores_shape` |
| INV-8 | `tests/test_box_shape.py::test_closed_and_wound_outward` |
| INV-9 | `tests/test_box_model.py::test_lip_replaces_painted_wall`, `::test_lip_width_is_rim_width` |
| INV-10 | `tests/test_box_shape.py::test_recess_is_cut_plain`, `::test_spine_shows_its_picture`; `tests/test_box_viewer.py::test_flat_spine_drawn_whole` |
| § 4.4's draw order | **nothing** — the by-eye check (§ 6) |
| § 4.2's working figures | **nothing** — no source exists; the user's by-eye check |
| § 6 frame time | **nothing** — judged while auto-spin runs |

## 11. Cross-doc impact

- `SLIP-0104-turnable-3d-box.md`: § 4.1 gains the `shape` key, pointing
  here; § 4.5 names `box_patches` as what is drawn, and the draw order of
  a shaped box; INV-1 is annotated (§ 13).
- `CHANGELOG.md`: Added, under Unreleased.
- RetroDB: the session is sent this path; PASS-59-231 builds from § 4.1.
  The amendment of 2026-11-03 adds the lip and seam keys; RetroDB accepted
  them the same day. The second amendment adds the recess keys, which
  RetroDB is sent.

## 12. Cold-eyes loop log

Rows live in `../reviews/SLIP-0125-keep-case-shape-loop-log.md`.

## 13. Migration / compatibility

- Box files written before this have no `shape` and draw flat, as before.
- A shaped file loads in every released RetroDB, which ignores `shape` and
  draws six flat faces with the same pictures (RetroDB, 2026-11-03). Those
  builds drop the key at import, so a box imported there must be imported
  again to gain its shape.
- SLIP-0104 INV-1 ("exactly § 4.1's keys") now allows the optional `shape`.
  SLIP-0104 INV-13 ("a wrap box file writes `"edge": null`") holds
  unchanged, as the sides get no pictures (§ 4.3).

## 14. Open questions

- The working figures in § 4.2, until the user's check.
- Whether RetroDB takes the recess keys as written in § 4.1.
