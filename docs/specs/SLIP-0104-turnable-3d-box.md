<!-- ants-spec-format: 1 -->
# SLIP-0104 — Show a turnable 3D box, and save it as a box file RetroDB can load

**Status:** spec draft (2026-10-10).
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
  size and colour, from `CASE_TYPES` in `core/case_types.py`.
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
- **Two calls left to the user** — § 15.

## 4. Design

### 4.1 The box file (the shared contract)

For a stem `S`, four files sit in one folder:

```
S.box.json        the description, written last
S.front.png       front cover
S.spine.png       spine
S.back.png        back cover (absent when there is none)
```

`S.box.json`, format version 1:

```json
{
  "format": "slipcase-box",
  "version": 1,
  "generator": "Slipcase 1.4.0",
  "case": {"name": "DVD Case", "width_mm": 135, "height_mm": 190, "depth_mm": 14},
  "colours": {"top": "#1C1C1C", "bottom": "#1C1C1C", "edge": "#1C1C1C"},
  "faces": {"front": "S.front.png", "spine": "S.spine.png", "back": "S.back.png"}
}
```

- **`case`** copies the `CaseType` used for the render: `width` is the front
  face's width, `height` its height, `depth` the spine's width, all in mm.
- **`colours`** are `#RRGGBB`. `top` and `bottom` are the colours
  `BoxRenderer.render` gives those faces: `case_color` when set, else
  `extract_dominant_edge_color` of the front picture at that edge. `edge` is
  the opening side opposite the spine: `case_color` when set, else `top`.
- **`faces`** values are file names in the same folder. `back` is `null`
  when the box has no back cover; a viewer then fills it with `edge`.
- **Orientation.** Each picture shows its face from outside the box, standing
  upright. The spine is on the front's left as seen from the front, as on
  every case in `CASE_TYPES`.
- **Pictures** are PNG, RGB with no alpha, longest edge at most 1600 px, never
  enlarged. Measured worst case: 1600 × 1600 random noise through
  `save_optimized_png` is 6,743,128 bytes, under RetroDB's 10 MB limit.
- **`generator`** is informational. Readers ignore it and any key they do not
  know, so version 1 can gain optional keys.

**Reading rules**, for any reader: refuse a `format` other than
`slipcase-box` or a `version` other than 1; refuse a face name that is not a
single plain file name (contains `/` or `\`, is `.` or `..`, starts with
`.`); refuse a missing `front` or `spine` file; refuse a size that is not a
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

FACE_MAX_EDGE = 1600

def build_box_model(front_image, back_image, case_type, *, title, serial,
                    platform, spine_color, case_color, spine_left_offset,
                    spine_right_offset, full_cover) -> BoxModel: ...
```

It takes `BoxRenderer.render`'s face inputs and decides the faces the way
render does: `is_full_cover` when `full_cover` is None; `split_full_cover`
with the same offsets; a loaded back cover wins over the split one; with no
full cover, the spine is `generate_spine(title or "Game", ...)` at the front
height's scale. No shading and no case texture: lighting depends on the
viewing angle, so the viewer applies it. Pictures with alpha are flattened
onto `edge`.

### 4.3 Writing and reading the box file

New `core/box_file.py`:

```python
def write_box_file(model: BoxModel, folder: str, stem: str,
                   compress_level: int = 6) -> str: ...   # returns the .json path
def read_box_file(path: str) -> BoxModel: ...              # raises BoxFileError
def box_paths(folder: str, stem: str) -> list[str]: ...    # the four paths
```

`write_box_file` saves each face with `save_optimized_png`, then the JSON
through a temporary file and `os.replace`, so a `.box.json` never names a face
that was not written. If a face fails, it deletes the faces it wrote and
raises. `read_box_file` applies § 4.1's reading rules; Slipcase uses it in
tests, and it is the reference for RetroDB's reader.

### 4.4 When a box file is written

- **Setting** `export/box_file` (bool) in `core/config.py`, shown in the
  settings dialog. Default: § 15 item 1.
- **Export PNG.** With the setting on, `MainWindow._export_png` also writes
  the box file beside the PNG. Stem: the PNG's stem with a trailing
  ` 3D Boxart` removed.
- **Batch.** With the setting on, `_render_single_image` and
  `BatchWorker._run_sequential` write the box file after the PNG, with the
  PNG's stem. `unique_output_path` picks a stem for which none of the PNG and
  the four `box_paths` exists, so a batch never overwrites a file.
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
- **Controls.** Left-drag turns the box (yaw unlimited, pitch clamped to
  −89…89 degrees). Right-drag or middle-drag moves it. The wheel zooms
  (camera distance clamped). Arrow keys turn, `+`/`-` zoom, `Home` and a
  double-click reset to yaw = the render's `angle`, pitch 10 degrees, zoom to
  fit. An **Auto-spin** button turns the yaw at 30 degrees a second through a
  `QTimer`; any drag stops it.
- **Data.** `RenderWorker` builds the `BoxModel` after the render and emits it
  as a new `model_ready(object)` signal. The viewer converts the faces to
  `QImage` once per model, never in `paintEvent`.

## 5. Invariants

- **INV-1** — A written `S.box.json` holds exactly § 4.1's keys for version 1:
  `format` `slipcase-box`, `version` 1, `case` equal to the `CaseType` used,
  `#RRGGBB` colours, and face names `S.front.png`, `S.spine.png` and either
  `S.back.png` or `null`.
  *Test:* `tests/test_box_file.py::test_written_file_matches_schema`.
  *Breaks when:* `case` is filled from pixel sizes, a key is renamed, or a
  colour is written as a list.

- **INV-2** — `read_box_file` refuses every case in § 4.1's reading rules and
  accepts what `write_box_file` writes, giving back an equal `BoxModel`.
  *Test:* `tests/test_box_file.py::test_reader_refuses` (one fixture per rule:
  `../x.png`, `a/b.png`, `.hidden.png`, version 2, `depth_mm` 0, colour
  `red`, a missing spine file), and `::test_round_trip`.
  *Breaks when:* the name check strips folders instead of refusing, so
  `../x.png` is read as `x.png` — the fixture places a valid `x.png` beside
  the JSON so only the name rule can refuse it.

- **INV-3** — A `.box.json` exists only when every face it names was written.
  *Test:* `tests/test_box_file.py::test_failed_face_leaves_no_json` makes
  saving the spine raise and checks that no `.box.json` and no face file
  remains.
  *Breaks when:* the JSON is written before the faces, or the written faces
  are not removed.

- **INV-4** — Every face picture is RGB, its longest edge at most 1600 px and
  never larger than its source.
  *Test:* `tests/test_box_file.py::test_face_limits` with a 3000 × 4200 RGBA
  front and a 100 × 140 one.
  *Breaks when:* alpha is kept, the cap is missing, or a small picture is
  enlarged.

- **INV-5** — `build_box_model` gives the faces render would use: for a full
  cover, back, spine and front are `split_full_cover`'s output for the same
  offsets, scaled; for a front-only cover, the spine is `generate_spine`'s
  output and `back` is None unless a back cover was loaded.
  *Test:* `tests/test_box_model.py::test_full_cover_faces` and
  `::test_front_only_faces`, comparing pixels.
  *Breaks when:* the offsets are not passed through, or a split back
  replaces a loaded one.

- **INV-6** — A batch with the setting on never overwrites an existing file,
  and the box file's stem equals its PNG's stem.
  *Test:* `tests/test_box_file.py::test_batch_does_not_overwrite`: an output
  folder already holding `game.box.json` but no `game.png`.
  *Breaks when:* `unique_output_path` checks only the `.png` — that fixture
  passes such a check, so only the wider check can move the stem.

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
  *Breaks when:* `build_box_model` is called from a slot on the main thread,
  or `paintEvent` converts PIL images.

- **INV-10** — Trust boundary: a box file's face names come from a title the
  user typed or a cover-art service sent. Slipcase passes the stem through
  `MainWindow._safe_filename` (single export) or takes it from a file name on
  disk (batch), so no written face lands outside the chosen folder.
  *Test:* `tests/test_box_file.py::test_stem_cannot_escape` writes with the
  stem `_safe_filename("../../evil")` and checks every written path is inside
  the folder.
  *Breaks when:* the single export builds the stem from the raw title.

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
  have today. A prototype of § 4.5's method (one 270 × 380 face drawn into a
  600 × 600 image with `quadToQuad` and `drawImage`, offscreen) drew
  perspective-correct and took about 0.3 ms per frame.
- **A web view in Slipcase showing RetroDB's CSS viewer.** One viewer for
  both apps, but Qt WebEngine adds a browser engine to every download.
- **Re-rendering with `BoxRenderer` while dragging.** It is built for one
  yaw range seen from the front or back, and redoes shading and shadow per
  frame; it cannot show the top or bottom.
- **Baking shading into the face pictures.** Light that looks right at one
  angle looks wrong once the box turns.

## 9. Out of scope

- RetroDB's importer, viewer and back-art download — RetroDB's roadmap.
- Case texture (plastic sheen, emboss) on the turnable box — deferred; not
  yet queued.
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
  1600 × 1600, plus their `QImage` copies in the viewer — under 62 MB at the
  cap, about 6 MB for a typical DVD cover at 1600 px tall. Released when a new
  model arrives and when the window closes.
- Disk: up to three extra PNGs and a small JSON per box, only with the
  setting on.

## 14. Migration / compatibility

New files only. Existing PNG exports are unchanged. `export/box_file` is a new
config key with a default, so an old `config.json` loads unchanged.

## 15. Open questions

1. **Is the box file on by default?** Recommendation: on. The user is
   rebuilding a library and RetroDB is the main reader; a user who wants
   only the PNG turns it off once.
2. **How are the user's cover files named?** RetroDB matches by ROM base
   name. Batch output takes each cover's own file name, so covers named after
   their ROMs match with no extra step. If they are named otherwise, renaming
   is a separate tool, not part of this spec.
