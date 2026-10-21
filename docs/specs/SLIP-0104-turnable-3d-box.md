<!-- ants-spec-format: 1 -->
# SLIP-0104 — Show a turnable 3D box, and save it as a box file RetroDB can load

**Status:** accepted (2026-10-15); amended 2026-10-21 (case details,
transparent viewer background; the optional edge face, SLIP-0106), not
re-reviewed: user rulings 2026-10-21.
**Amended by:** SLIP-0106 (`SLIP-0106-jewel-cases.md` § 16).
**Kind:** implement.
**Source:** ROADMAP SLIP-0104 (user request 2026-10-10; details agreed with
the RetroDB session the same day).

**Layman:** Slipcase shows the whole game box, every side, and lets you turn
it and zoom in with the mouse; it can also save the box so RetroDB shows the
same turnable box.

## 1. Goal

A user can turn a rendered box in Slipcase to any angle, zoom in and out, and
see all six sides. Slipcase can save a **box file** beside each render: the
case's real size, its colours, and its front, back and spine pictures. RetroDB
loads box files and shows the same turnable box. Slipcase writes the format;
RetroDB reads it. This spec fixes the format both sides bind to and Slipcase's
half of the work.

## 2. Problem

1. The preview shows one fixed view. `BoxRenderer.render` in
   `core/renderer.py` draws the box from a single angle (`angle`, 5–60
   degrees) and from the front or the back (`view`), with no other way to see
   it.
2. The flat PNG is all that leaves Slipcase. `MainWindow._export_png` and
   `_render_single_image` in `ui/workers.py` save one picture. RetroDB stores
   it as a flat image (its `custom_boxart_3d` upload in `routes/games.py`), so
   RetroDB cannot turn the box.
3. The user is rebuilding a wiped RetroDB library from covers they kept, most
   of them full covers (back, spine and front in one image). Every box they
   make now is made once more if the format arrives later.

## 3. Scope decisions (agreed with the user)

- **Both apps, Slipcase first.** User, 2026-10-10: a model of the box, all
  sides, that the viewer can rotate and zoom, "and whatever else goes with
  that"; add it to RetroDB too, worked out with the RetroDB session.
- **The box looks like the real case.** User, 2026-10-10: true per-platform
  size from `CASE_TYPES` in `core/case_types.py`, and the colours the render
  uses (§ 4.1).
- **JSON plus images, not a 3D model file.** Proposed by Slipcase, accepted
  by RetroDB 2026-10-10 (reply approved by the user).
- **Matched by ROM base name.** RetroDB, 2026-10-10: its bulk import matches
  a file to a game by ROM file name without extension, inside a folder per
  system. Game ids are not stable across a library rebuild.
- **Fallback order in RetroDB.** RetroDB, 2026-10-10: Slipcase box file,
  then ScreenScraper back art, then generated faces. RetroDB's own work.
- **RetroDB's viewer uses CSS 3D, on the game detail page.** RetroDB,
  2026-10-10. Recorded so this spec does not re-decide it.
- **Slipcase's viewer draws with `QPainter`, adding no dependency.** Slipcase,
  2026-10-10, from the prototype in § 8. Open to the user's veto.
- **The box file is on by default.** User, 2026-10-15.
- **Cover files are named after their ROMs.** User, 2026-10-15. So batch
  output, which keeps each cover's file name as its stem, matches RetroDB's
  ROM base names with no renaming step when the output folder holds no
  earlier files of those names (§ 4.4 never overwrites them).
- **The turnable box shows the case details.** User, 2026-10-21: the box
  must look like the real thing, so its faces carry the same per-case
  details (embossing, ridges, grooves) as the still render (§ 4.2).
- **The viewer's background is transparent.** User, 2026-10-21: a viewer
  draws only the box, and whatever is behind it shows through (§ 4.1,
  § 4.5).

## 4. Design

### 4.1 The box file (the shared contract)

For a stem `S`, these files sit in one folder:

```
S.box.json        the description, written last
S.front.png       front cover
S.spine.png       spine
S.back.png        back cover (absent when there is none)
S.edge.png        opening side (absent when there is none)
S.top.png         top (absent when there is none)
S.bottom.png      bottom (absent when there is none)
```

`S.box.json`, format version 1:

```json
{
  "format": "slipcase-box",
  "version": 1,
  "generator": "Slipcase 1.4.0",
  "case": {"name": "PS2 DVD Case", "width_mm": 135, "height_mm": 190, "depth_mm": 14},
  "colours": {"top": "#1C1C1C", "bottom": "#1C1C1C", "edge": "#1C1C1C"},
  "faces": {"front": "S.front.png", "spine": "S.spine.png", "back": "S.back.png",
            "edge": "S.edge.png", "top": "S.top.png", "bottom": "S.bottom.png"}
}
```

- **`case`** copies the `CaseType` used for the render: `width` is the front
  face's width, `height` its height, `depth` the spine's width, all in mm.
- **`colours`** are `#RRGGBB`, written in upper case; readers accept either
  case. `top` and `bottom` are `case_color` when set, else
  `extract_dominant_edge_color` of the front cover at that edge (the split
  front for a full cover), whatever view was rendered. `edge` is
  the opening side opposite the spine: `case_color` when set, else `top`.
- **`faces`** values are file names in the same folder. `back` is `null`
  when the box has no back cover; a viewer then fills it with `edge`.
  `edge` is the opening side's picture, or `null` when there is none; a
  viewer then fills that side with `colours.edge`. Readers that do not
  know `edge` ignore it, as any unknown key (SLIP-0106 § 4.8). `top` and
  `bottom` work the same way for those faces and `colours.top` and
  `colours.bottom` (SLIP-0110): a case with moulded text there has them.
- **Orientation.** Each picture shows its face from outside the box, standing
  upright. The spine is on the front's left as seen from the front, as on
  every case in `CASE_TYPES`. The edge is on the front's right as seen from
  the front. The top's picture has the spine on its left and the back at
  its top edge; the bottom's has the spine on its left and the front at its
  top edge.
- **Pictures** are PNG, RGB with no alpha, longest edge at most 1600 px, never
  enlarged. Measured worst case (2026-10-10): 1600 × 1600 random noise through
  `save_optimized_png` is 6,743,128 bytes, under RetroDB's 10 MB limit.
- **Case details** are already in the face pictures (§ 4.2). A viewer adds
  only its own lighting.
- **Background.** A viewer draws the box and nothing behind it.
- **`generator`** is informational. Readers ignore it and any key they do not
  know, so version 1 can gain optional keys.

**Reading rules**, for any reader: refuse a `format` other than
`slipcase-box` or a `version` other than 1; refuse a face name that is not a
single plain file name (contains `/` or `\`, is `.` or `..`, starts with
`.`); refuse a `front` or `spine` that is null or whose file is missing, and
a `back`, `edge`, `top` or `bottom` that names a missing file; refuse a size that is not a
positive number at most 1000; refuse a colour that is not `#RRGGBB`. RetroDB
adds its own image checks (§ 11).

### 4.2 Building the faces

New `core/box_model.py`:

```python
@dataclass
class BoxModel:
    case_type: CaseType
    top: tuple[int, int, int]
    bottom: tuple[int, int, int]
    edge: tuple[int, int, int]
    front: Image.Image          # RGB, longest edge <= FACE_MAX_EDGE
    spine: Image.Image          # RGB, same cap
    back: Image.Image | None    # RGB, same cap
    edge_face: Image.Image | None = None  # RGB, same cap; the opening side
    top_face: Image.Image | None = None   # RGB, same cap (SLIP-0110)
    bottom_face: Image.Image | None = None

FACE_MAX_EDGE = 1600

def build_box_model(front_image, back_image, case_type, *, title, serial,
                    platform, spine_color, case_color, spine_left_offset,
                    spine_right_offset, full_cover,
                    show_texture, back_strips=None) -> BoxModel: ...
```

A jewel case (`case_type.layout == "jewel"`) builds its faces with
SLIP-0106 § 4.4's `jewel_faces`; the rest of this section describes the
wrap layout. A jewel case with `moulded_logo` and `show_texture` set gets
`top_face` and `bottom_face`: one picture, the front's width by the depth
at the front's px/mm, from `generate_moulded_edge`. That draws the text
37 mm long, centred and raised, reading left to right on both (SLIP-0110).
The still render does not use them; there those edges are slivers.

It takes `BoxRenderer.render`'s face inputs and decides the faces the way
render does: `is_full_cover` when `full_cover` is None; `split_full_cover`
with the same offsets; a loaded back cover wins over the split one; with no
full cover, the spine is `generate_spine(title or "Game", ...)` at the front
height's scale.

**Case details.** With `show_texture` set, each face is scaled to its final
size and then composited, as render does, with the overlay at that size:
`generate_front_texture(case_type, w, h)` on the front,
`generate_spine_texture` on the spine, and the front overlay mirrored left
to right on the back, as render's back view lays it. With it clear, no
overlay. `RenderWorker` passes the render's own `show_texture`.

No shading: lighting depends on the viewing angle, so the viewer applies it.
Pictures with alpha are flattened onto `edge` after the overlay.

### 4.3 Writing and reading the box file

New `core/box_file.py`:

```python
def write_box_file(model: BoxModel, folder: str, stem: str,
                   compress_level: int = 6) -> str: ...   # returns the .json path
def read_box_file(path: str) -> BoxModel: ...              # raises BoxFileError
def box_paths(folder: str, stem: str) -> list[str]: ...    # the description, then each face
```

`write_box_file` first refuses, writing nothing, a stem whose face names
would fail § 4.1's name rule. It then deletes every existing file among the
`box_paths`, saves each face with `save_optimized_png`, and writes the JSON last through a
temporary file and `os.replace`, so a `.box.json` never names a face that was
not written. If a face fails, it deletes the faces it wrote and raises.
`read_box_file` applies § 4.1's reading rules and builds `case_type` from the
JSON `case` with `platforms=()`. Slipcase uses it in tests, and it is the
reference for RetroDB's reader.

### 4.4 When a box file is written

- **Setting** `export/box_file` (bool) in `core/config.py`, shown in the
  settings dialog. Default: on (§ 3).
- **Export PNG.** With the setting on, `MainWindow._export_png` also writes
  the `BoxModel` paired with the shown render (§ 4.5) beside the PNG. Stem:
  the chosen PNG's stem with a trailing ` 3D Boxart` removed. When any of
  that stem's `box_paths` exists, Slipcase asks before replacing the box
  file; on No, the PNG is saved and the box file is not.
- **Batch.** With the setting on, `_render_single_image` and
  `BatchWorker._run_sequential` write the box file after the PNG, with the
  PNG's stem. New `pick_output_stems(file_paths, output_dir) -> list[str]` in
  `ui/workers.py`, called by `BatchWorker` before any render starts, picks
  each stem: one for which neither the PNG nor any of its `box_paths`
  exists, and that no earlier file in the list was given. Each render
  receives its stem.
- A box-file failure is reported like a PNG failure (a message for a single
  export, the batch `error` signal per file); the PNG already saved stays.

### 4.5 The viewer in Slipcase

New `ui/box_viewer.py::BoxViewer(QWidget)`, a third page of
`MainWindow.preview_stack`, reached by a **3D View** toggle under the preview
and the shortcut Ctrl+3 (unused today; added to `STANDARDS.md` § 6).

- **Drawing.** For each face, project its four corners and draw its picture
  with `QTransform.quadToQuad` and `QPainter.drawImage`, which maps the
  picture perspective-correctly. Plain faces are filled polygons. Only faces
  turned towards the camera are drawn; on a box those never overlap, so no
  sorting is needed. Each face is darkened by a fixed light: brightness =
  0.45 + 0.55 × max(0, normal · light).
- **Background.** `paintEvent` draws the box and nothing else, and the
  widget keeps `autoFillBackground` off, so the preview area behind it shows
  through.
- **Controls.** Left-drag turns the box (yaw unlimited, pitch clamped to
  −89…89 degrees). Right-drag or middle-drag moves it. The wheel zooms
  (camera distance clamped). Arrow keys turn, `+`/`-` zoom, `Home` and a
  double-click reset to yaw = the render's `angle`, pitch 10 degrees, zoom to
  fit. An **Auto-spin** button turns the yaw at 30 degrees a second through a
  `QTimer`; any drag stops it.
- **Data.** `RenderWorker` builds the `BoxModel` after the render and emits it
  as a new `model_ready(object)` signal. `MainWindow` keeps it with the
  render it belongs to, for the viewer and for Export PNG. The viewer converts the faces to
  `QImage` once per model, never in `paintEvent`. It draws `edge_face` on
  the edge side when present, and `top_face` and `bottom_face` on the top
  and bottom (SLIP-0110), converted once per model like the others.

## 5. Invariants

- **INV-1** — A written `S.box.json` holds exactly § 4.1's keys for version 1:
  `format` `slipcase-box`, `version` 1, `case` equal to the `CaseType` used,
  `#RRGGBB` colours, and face names `S.front.png`, `S.spine.png`, and each
  of `S.back.png`, `S.edge.png`, `S.top.png` and `S.bottom.png` or `null`.
  *Test:* `tests/test_box_file.py::test_written_file_matches_schema`.
  *Breaks when:* `case` is filled from pixel sizes, a key is renamed, or a
  colour is written as a list.

- **INV-2** — `read_box_file` refuses every case in § 4.1's reading rules and
  accepts what `write_box_file` writes. The model read back has the written
  case name and sizes, the written colours, `case_type.platforms == ()`, and
  face pixels equal to the written faces after `save_optimized_png`'s
  low-bit strip (`& 0xFE`).
  *Test:* `tests/test_box_file.py::test_reader_refuses` (one fixture per rule:
  `format` `foo`, version 2, `../x.png`, `a/b.png`, `a\b.png`, `..`,
  `.hidden.png`, a null `front`, a missing spine file, a `back` naming a
  missing file, an `edge` naming a missing file, `depth_mm` 0, `width_mm` 5000, colour `red`), and
  `::test_round_trip`.
  *Breaks when:* the name check strips folders instead of refusing, so
  `../x.png` is read as `x.png` — the fixture places a valid `x.png` beside
  the JSON so only the name rule can refuse it.

- **INV-3** — A `.box.json` exists only when every face it names was written.
  *Test:* `tests/test_box_file.py::test_failed_face_leaves_no_json` makes
  saving the spine raise, in a folder already holding a valid box file of
  that stem, and checks that no `.box.json` and no face file remains.
  *Breaks when:* the JSON is written before the faces, the old `.box.json` is
  left in place, or the written faces are not removed.

- **INV-4** — Every face picture is RGB, its longest edge at most 1600 px and
  never larger than its source.
  *Test:* `tests/test_box_file.py::test_face_limits` with a 3000 × 4200 RGBA
  front and a 100 × 140 one.
  *Breaks when:* alpha is kept, the cap is missing, or a small picture is
  enlarged.

- **INV-5** — For the wrap layout, `build_box_model` gives the faces render
  would use (amended by SLIP-0106): for a full
  cover, back, spine and front are `split_full_cover`'s output for the same
  offsets, scaled; for a front-only cover, the spine is `generate_spine`'s
  output and `back` is None unless a back cover was loaded.
  *Test:* `tests/test_box_model.py::test_full_cover_faces` and
  `::test_front_only_faces`, comparing pixels.
  *Breaks when:* the offsets are not passed through, or a split back
  replaces a loaded one.

- **INV-6** — A batch with the setting on never overwrites an existing file
  or another file of the same batch, and the box file's stem equals its PNG's
  stem.
  *Test:* `tests/test_box_file.py::test_batch_does_not_overwrite` calls
  `pick_output_stems` for two sources `A/game.png` and `B/game.png` and an
  output folder already holding `game.box.json` but no `game.png`; the stems
  are distinct and neither is `game`.
  *Breaks when:* the check looks only at the `.png` — the fixture passes such
  a check — or ignores stems already given in the batch.

- **INV-7** — The viewer draws exactly the faces turned towards the camera.
  *Test:* `tests/test_box_viewer.py::test_visible_faces`: yaw 0 and pitch 0
  give `{front}`; yaw 30 and pitch 10 give `{front, spine, top}`; yaw 180
  and pitch 0 give `{back}`.
  *Breaks when:* a face's corner order is reversed, so its normal points
  inward and it is culled when it faces the camera.

- **INV-8** — Pitch stays within −89…89 degrees, zoom within its limits, and
  reset restores yaw = the render's angle, pitch 10 degrees and the fitted
  zoom.
  *Test:* `tests/test_box_viewer.py::test_limits_and_reset`.
  *Breaks when:* a long drag carries the pitch past 90 degrees and the box
  turns upside down, or the wheel moves the camera inside the box.

- **INV-9** — Faces are built off the main thread, and the viewer converts
  them once per model.
  *Test:* `tests/test_box_viewer.py::test_model_from_worker` checks
  `RenderWorker` emits `model_ready` with a `BoxModel`, and that two
  `paintEvent`s on one model convert no picture again.
  *Breaks when:* `RenderWorker` stops building the model, or `paintEvent`
  converts PIL images.

- **INV-10** — Trust boundary: a stem comes from a file name the user typed
  or a cover file on disk. `write_box_file` refuses, before writing anything,
  a stem whose face names fail § 4.1's name rule. So no face lands outside
  the chosen folder, and Slipcase never writes a face name its own reader
  refuses.
  *Test:* `tests/test_box_file.py::test_stem_cannot_escape` tries the stems
  `../../evil`, `a/b`, `a\b`, `.x` and the empty string, and checks each
  raises `BoxFileError` and leaves the folder empty.
  *Breaks when:* the check runs after a face is saved, or tests the stem
  rather than the face names built from it.

- **INV-11** — With `show_texture` set, every face carries § 4.2's overlay
  at the face's own size, the back's mirrored; with it clear, none does.
  *Test:* `tests/test_box_model.py::test_case_details_baked_in` builds a
  PS3 Blu-ray Case model from uniform grey (128) front and back covers, so the
  overlay's faint lines change pixels, and compares each face with the
  overlay composited by hand. A Blu-ray front is not mirror-symmetric (its
  spine-edge groove), so only the mirroring rule passes the back.
  *Breaks when:* the overlay is left out, made at a size other than the
  face's, laid on the back unmirrored, or applied with `show_texture` clear.

- **INV-12** — The viewer paints nothing outside the box.
  *Test:* `tests/test_box_viewer.py::test_background_transparent` renders the
  widget into a `QImage` cleared to transparent, with no render flags so only
  `paintEvent` draws, and checks that the four corner pixels keep alpha 0
  while the centre pixel does not.
  *Breaks when:* `paintEvent` fills its rectangle before drawing the faces.

- **INV-13** — A jewel box file names `S.edge.png` and that file holds
  `edge_face`; a wrap box file writes `"edge": null` and no `S.edge.png`
  (added by SLIP-0106).
  *Test:* `tests/test_box_file.py::test_edge_face_written`.
  *Breaks when:* the writer drops the edge face, or leaves an old
  `S.edge.png` behind when the stem is rewritten as a wrap box.

- **INV-14** — A reader that ignores `faces.edge` still reads a jewel box
  file whole, with the opening side's colour equal to the case's plastic
  (added by SLIP-0106).
  *Test:* `tests/test_box_file.py::test_v1_reader_without_edge` deletes the
  key from a written jewel file's JSON, reads it, and checks `edge_face` is
  None and `edge` is the case's `plastic`.
  *Breaks when:* `colours.edge` is sampled from the art for a jewel case, or
  `edge` is made required.

## 6. Failure modes

- **Disk full or folder not writable** — the PNG may save and the box file
  fail. INV-3 keeps the folder free of a half box; the user sees the error.
- **Spine not found in a full cover** — the same as today: the user moves the
  spine sliders; the model uses the same offsets (INV-5).
- **A front-only cover** — the spine is generated and the back is plain. The
  viewer and RetroDB both handle `back: null`.
- **A very large source** — faces are capped at 1600 px, so memory and file
  size stay bounded (§ 13).
- **No OpenGL** — not needed. `QPainter` draws in software, as the preview
  does today.
- **A future version 2** — a version 1 reader refuses it rather than
  half-reading it (INV-2).

## 7. Tests

| Test | Locks |
|------|-------|
| `tests/test_box_file.py::test_written_file_matches_schema` | INV-1 |
| `tests/test_box_file.py::test_reader_refuses`, `::test_round_trip` | INV-2 |
| `tests/test_box_file.py::test_failed_face_leaves_no_json` | INV-3 |
| `tests/test_box_file.py::test_face_limits` | INV-4 |
| `tests/test_box_model.py::test_full_cover_faces`, `::test_front_only_faces` | INV-5 |
| `tests/test_box_file.py::test_batch_does_not_overwrite` | INV-6 |
| `tests/test_box_viewer.py::test_visible_faces` | INV-7 |
| `tests/test_box_viewer.py::test_limits_and_reset` | INV-8 |
| `tests/test_box_viewer.py::test_model_from_worker` | INV-9 |
| `tests/test_box_file.py::test_stem_cannot_escape` | INV-10 |
| `tests/test_box_model.py::test_case_details_baked_in` | INV-11 |
| `tests/test_box_viewer.py::test_background_transparent` | INV-12 |
| `tests/test_box_file.py::test_edge_face_written` | INV-13 |
| `tests/test_box_file.py::test_v1_reader_without_edge` | INV-14 |

Each test is run and seen to fail before the code it locks exists. Widget
tests keep the `QApplication` on the class and clean up with
`_destroy_now` / `sip.delete`, as the existing Qt tests do.

## 8. Alternatives considered (and rejected)

- **A glTF (`.glb`) model file.** Viewers could load it with a 3D library,
  but Slipcase would need a glTF writer and RetroDB a WebGL library, and the
  box is six rectangles. JSON plus images is readable by both with code they
  already have.
- **Qt Quick 3D or an OpenGL widget in Slipcase.** Real 3D, but more
  packaged size and a graphics-driver dependency the packaged builds do not
  have today. A prototype of § 4.5's method (2026-10-10; one 270 × 380 face drawn into a
  600 × 600 image with `quadToQuad` and `drawImage`, offscreen) drew
  perspective-correct and took about 0.3 ms per frame.
- **A web view in Slipcase showing RetroDB's CSS viewer.** One viewer for
  both apps, but Qt WebEngine adds a browser engine to every download.
- **Re-rendering with `BoxRenderer` while dragging.** It is built for one
  yaw range seen from the front or back, and redoes shading and shadow per
  frame; it cannot show the top or bottom.
- **Baking shading into the face pictures.** Light that looks right at one
  angle looks wrong once the box turns.
- **Case details as separate overlay pictures in the box file.** A viewer
  could switch them off, but every reader would have to composite them, and
  RetroDB would need new code and version 2. Baked in, version 1 is
  unchanged. The overlay's faint highlight lines do not move with the light;
  at their strength that is not visible at viewer sizes (unmeasured, judged
  by eye at build).

## 9. Out of scope

- RetroDB's importer, viewer and back-art download — RetroDB's roadmap.
- Saving the current viewer angle as a picture or animation — deferred; not
  yet queued. The existing Export Animation covers turning videos.
- Reading box files back into Slipcase's editor — deferred; not yet queued.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 | `tests/test_box_file.py::test_written_file_matches_schema` |
| INV-2 | `tests/test_box_file.py::test_reader_refuses`, `::test_round_trip` |
| INV-3 | `tests/test_box_file.py::test_failed_face_leaves_no_json` |
| INV-4 | `tests/test_box_file.py::test_face_limits` |
| INV-5 | `tests/test_box_model.py::test_full_cover_faces`, `::test_front_only_faces` |
| INV-6 | `tests/test_box_file.py::test_batch_does_not_overwrite` |
| INV-7 | `tests/test_box_viewer.py::test_visible_faces` |
| INV-8 | `tests/test_box_viewer.py::test_limits_and_reset` |
| INV-9 | `tests/test_box_viewer.py::test_model_from_worker` |
| INV-10 | `tests/test_box_file.py::test_stem_cannot_escape` |
| INV-11 | `tests/test_box_model.py::test_case_details_baked_in` |
| INV-12 | `tests/test_box_viewer.py::test_background_transparent` |
| INV-13 | `tests/test_box_file.py::test_edge_face_written` |
| INV-14 | `tests/test_box_file.py::test_v1_reader_without_edge` |
| RetroDB reads version 1 as § 4.1 says | **nothing** in this repository — RetroDB's import tests own it |
| The viewer looks right and feels smooth | **nothing** — checked by eye on Linux and the Windows test machine |

## 11. Cross-doc impact

- `STANDARDS.md`: § 2 (new modules, the `model_ready` signal), § 6 (Ctrl+3),
  § 7 (`export/box_file`), § 12 (the viewer's images released on a new model
  and on close).
- `README.md`: the 3D view and the box file.
- `CHANGELOG.md`: an Added entry.
- RetroDB: its own spec or roadmap items for the importer and viewer, citing
  § 4.1. RetroDB adds per-image checks on import: at most 10 MB, a real image
  (Pillow verify, decompression-bomb guard), re-encoded to WebP at 1080 px
  tall, no symlinks followed, fill-only unless the user asks to overwrite.

## 12. Cold-eyes loop log

Rows live in `../reviews/SLIP-0104-turnable-3d-box-loop-log.md`.

## 13. Resource cost

- No new dependency.
- Memory: one `BoxModel` per render, three RGB faces of at most
  1600 × 1600 (3 bytes a pixel), plus their 32-bit `QImage` copies in the
  viewer (4 bytes a pixel) — at most 3 × 1600 × 1600 × 7 bytes, about 54 MB.
  A DVD box at 1600 px tall (front and back 1137 × 1600, spine 118 × 1600) is
  about 27 MB. Released when a new model arrives and when the window closes.
- Disk: up to three extra PNGs and a small JSON per box, only with the
  setting on.

## 14. Migration / compatibility

New files only. Existing PNG exports are unchanged. `export/box_file` is a new
config key with a default, so an old `config.json` loads unchanged.

## 15. Open questions

None. The two left to the user were answered on 2026-10-15 and are in § 3.
