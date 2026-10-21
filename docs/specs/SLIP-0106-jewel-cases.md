<!-- ants-spec-format: 1 -->
# SLIP-0106 — Draw disc jewel cases as the real ones look, per region

**Status:** spec draft (2026-10-21).
**Kind:** feature.
**Source:** ROADMAP SLIP-0106 (user-request-2026-10-21). This spec is phase 1
of the item: disc jewel cases. Research:
[`../research/SLIP-0106-real-cases.md`](../research/SLIP-0106-real-cases.md).
**Pairs with:** SLIP-0104 (amends its box file and face clauses; § 16).

**Layman:** A PlayStation, Dreamcast or other CD game now looks like its
real case: the front booklet sits under a clear lid beside the hinge, the
back insert's two printed edges show on the case's two sides, the plastic
is the right colour, and a European PlayStation case is thicker than an
American one.

## 1. Goal

A jewel-case game renders as a real jewel case of its system and region.
The front shows the booklet beside a strip of bare tray plastic at the
hinge, under a clear lid with a soft shine. The back shows the back
insert's middle. The hinge side and the opening side each show one of the
back insert's two end strips. Top and bottom are bare plastic in the
tray's colour. The region comes from the cover file's name, and the user
can override it in the case list. The box file carries the opening side's
picture without breaking a version 1 reader.

## 2. Problem

1. **Every case is one wrap.** `BoxRenderer.render` in `core/renderer.py`
   and `build_box_model` in `core/box_model.py` treat every cover as back +
   spine + front, split by `is_full_cover` and `split_full_cover` in
   `core/image_utils.py`. A jewel case has no wrap. Its front booklet shows
   the front only, and the back card "is folded into a flattened "U"
   shape, with the sides being visible along the ends" (Wikipedia, Optical
   disc packaging, re-read 2026-10-21). So a jewel case carries printed
   strips on both sides, and today the opening side is plain plastic.
2. **The jewel case stands the wrong way.** `CASE_TYPES["CD Jewel Case"]`
   in `core/case_types.py` is `width=125, height=142`, portrait. The case is
   142 × 125 × 10 mm, and its back card is 150 × 118 mm, folded at the
   ends of its 150 mm side (same source). The folds therefore sit on the
   case's two 125 mm edges, one of which is the hinge. So the front is
   142 wide and 125 tall.
3. **One case serves every region.** PS1, Saturn and Dreamcast share
   `CD Jewel Case`, 10.4 mm deep. "The standard PAL jewel case measured
   18 mm thick" and "came with a black plastic disk tray" (Wikipedia, same
   page). Dreamcast trays are clear in the US, white in Japan and blue in
   Europe (research file, sources [DJ] and segareplay).
4. **The plastic colour is guessed from the art.** `render` colours the
   top and bottom with `extract_dominant_edge_color` of the front cover,
   and `build_box_model` does the same, unless the user picks a case
   colour. A jewel case's top and bottom are bare tray plastic.

## 3. Scope decisions (agreed with the user)

- **Region from the file name's tag.** User, 2026-10-21: read "(Europe)",
  "(Japan)", "(USA)" and the like from the cover or ROM file name; the case
  list overrides it; no tag means US.
- **Order of work.** User, 2026-10-21: disc jewel cases first (this spec);
  then sizes and colours for every other system; then cartridge boxes.
- **Plastic.** User, 2026-10-21: the real plastic colour per case, a
  see-through lid with a soft shine over the art, bare plastic where
  nothing is printed. Moulded logos later, as their own item.
- **Every jewel case is a music CD case.** User, 2026-10-21: "NTSC PS1
  cases and all Dreamcast cases are the same measurements as music CD
  cases. The width and height of PAL cases for PS1 are the same as music
  CD cases, it is only the thickness that is more. The width of the clear
  hinge strip is the same as any music CD case." And: "The thickness of
  the PAL Dreamcast cases is the same as NTSC PS1 cases." So only the PS1
  PAL case differs in size, and only in depth.
- **A hand choice holds for one cover.** Slipcase, 2026-10-21, open to the
  user's veto: a case picked in the case list holds until the next cover is
  loaded or the platform changes. A batch started while it holds uses it
  for every file (§ 4.6).
- **Clear trays get a pale grey stand-in.** Slipcase, 2026-10-21: a clear
  tray has no colour of its own. Bare clear plastic is filled with
  `#C8CCD0`, judged by eye at build.
- **No case type that differs only by name.** Slipcase, 2026-10-21. Saturn
  JP, Mega-CD JP and PC CD-ROM use the standard jewel case, and no source
  gives their tray colour. They use `CD Jewel Case`; see § 8.

## 4. Design

### 4.1 Case data

`core/case_types.py` gains:

```python
@dataclass(frozen=True)
class JewelGeometry:
    """The paper inside a jewel case, in mm. W x H, W across the front."""
    booklet: tuple[float, float]    # front insert
    back_card: tuple[float, float]  # back insert laid flat, both end strips included
    strip: float                    # width of one end strip

@dataclass(frozen=True)
class CaseType:
    name: str
    width: float
    height: float
    depth: float
    platforms: tuple[str, ...]
    jewel: JewelGeometry | None = None          # None: the wrap layout
    plastic: tuple[int, int, int] | None = None  # bare plastic colour

    @property
    def layout(self) -> str:                     # "wrap" or "jewel"
        return "wrap" if self.jewel is None else "jewel"
```

New fields carry defaults, so `read_box_file`'s
`CaseType(name=..., width=..., height=..., depth=..., platforms=())` and
every existing entry stay valid. `plastic` is ignored by the wrap layout in
this phase.

Phase 1 jewel entries. W × H × D in mm. **S** = sourced; **U** =
unverified, a working value the user can correct (§ 15).

| Name | W × H × D | Booklet | Back card, strip | Plastic | `platforms` | Sources |
|---|---|---|---|---|---|---|
| `CD Jewel Case` | 142 × 125 × 10 | 120 × 120 | 150 × 118, 6 | black `#101010` | `("Saturn",)` | size, booklet, card S [OD]; strip, plastic U |
| `PS1 Jewel Case (NTSC-U)` | 142 × 125 × 10.4 | 120 × 120 | 150 × 118, 6 | black | `("PS1",)` | depth S (vgcollect); black tray supported by a second account, "solid opaque black" (passed on by the coordinator, 2026-10-21); rest as above |
| `PS1 Jewel Case (PAL)` | 142 × 125 × 18 | 120 × 120 | 158 × 118, 13.5 | black | `()` | W × H and booklet S (the user, § 3); depth and black tray S [OD]; card measured from the user's scan, U |
| `PS1 Jewel Case (NTSC-J)` | 142 × 125 × 10 | 120 × 120 | 150 × 118, 6 | black | `()` | depth S (chiebukuro, later releases); tray colour varies by release, black kept as the default, U |
| `Dreamcast Jewel Case (NTSC-U)` | 142 × 125 × 10.4 | 120 × 120 | 150 × 118, 6 | clear `#C8CCD0` | `("Dreamcast",)` | size S (the user, § 3); clear tray S [DJ] |
| `Dreamcast Jewel Case (NTSC-J)` | 142 × 125 × 10.4 | 120 × 120 | 150 × 118, 6 | white `#F0F0F0` | `()` | size S (the user, § 3); white tray S [DJ] |
| `Dreamcast Jewel Case (PAL)` | 142 × 125 × 10.4 | 120 × 120 | 150 × 118, 6 | blue `#2A4F9E` | `()` | size S (the user, § 3); blue tray S (segareplay) |

How the unverified figures were reached:

- **PS1 PAL card.** Measured from the user's PAL Ridge Racer Type 4 back
  scan, 1925 × 1441 px with a dark strip of about 165 px at each end.
  Taking its height as the standard 118 mm card height gives 12.2 px/mm.
  So the card is about 158 mm wide, each end strip about 13.5 mm, and the
  middle about 131 mm. An AI summary the user passed on gives 150 × 118
  with 6 mm flaps for this card. The scan wins: a 6 mm flap cannot wrap an
  18 mm side.
- **Standard strip, 6 mm.** The 150 mm card spans a 142 mm case and folds
  into a 10 mm side; 6 mm is a judgement, not a measurement.

`PLATFORM_CASE_MAP` and `ALL_PLATFORMS` are built as today, from
`platforms`. So each platform still has exactly one default case, and
regional variants list no platform. A new table and function pick the
variant:

```python
REGIONAL_CASES: dict[tuple[str, str], str] = {
    ("PS1", "PAL"): "PS1 Jewel Case (PAL)",
    ("PS1", "NTSC-J"): "PS1 Jewel Case (NTSC-J)",
    ("Dreamcast", "NTSC-J"): "Dreamcast Jewel Case (NTSC-J)",
    ("Dreamcast", "PAL"): "Dreamcast Jewel Case (PAL)",
}

def case_for(platform: str, region: str) -> CaseType | None:
    """The case for `platform` in `region`: its regional variant, else the
    platform's default case, else None."""
```

`get_case_for_platform` is unchanged. A region with no row falls back to
the platform's default, so PS2 in PAL stays `DVD Case` until phase 2 adds
rows.

### 4.2 Region from the file name

New `core/region.py`:

```python
NTSC_U, PAL, NTSC_J = "NTSC-U", "PAL", "NTSC-J"

def detect_region(file_name: str) -> str:
    """The region a cover's file name declares, NTSC_U when none does."""
```

- Read every parenthesised group of the name, left to right. Split each on
  commas and strip the parts. The first part, in the first group holding a
  known region word, decides. Case is ignored. A word must equal a whole
  part, never a substring.
- Known words. NTSC-U: `USA`, `US`, `Canada`, `World`. PAL: `Europe`,
  `EU`, `UK`, `Germany`, `France`, `Spain`, `Italy`, `Netherlands`,
  `Sweden`, `Scandinavia`, `Nordic`, `Denmark`, `Norway`, `Finland`,
  `Portugal`, `Belgium`, `Austria`, `Switzerland`, `Greece`, `Australia`,
  `New Zealand`. NTSC-J: `Japan`, `JP`, `Asia`, `Korea`, `Taiwan`,
  `Hong Kong`.
- Every group is read, not only the first. The tree on this machine holds
  `Tomb Raider (PSX) (USA)` under `/mnt/Games/PS3_PSN` (listed
  2026-10-21), where the first group is not a region.
- No group with a known word gives `NTSC_U`. This covers language tags
  such as `(En,Fr,De)`.

`detect_region` reads only the string it is given. Callers pass
`Path(path).name`, so no folder name decides a region.

### 4.3 Where detection hooks in

- **`MainWindow._load_front` and `MainWindow._open_recent`.** Both load a
  cover from a file. After the file is read and before `_set_front_image`,
  a new `MainWindow._detect_case(path)` runs:
  `case_for(self.platform_combo.currentText(), detect_region(Path(path).name))`.
  When that returns a case, it is set in `case_combo`. It runs before
  `_set_front_image` because that method calls `is_full_cover` with the
  current case. It also clears `self._case_by_hand`. It returns a note
  naming the region, which the caller adds to the status line after
  `_set_front_image`, since that method rewrites the status line.
- **Search results.** `_on_search_images` has no file name, so the case is
  left as it is.
- **The case list.** A new slot on `case_combo.activated` sets
  `self._case_by_hand = True`. Qt emits `activated` only on a user's choice,
  never on `setCurrentIndex`, so detection never marks itself as a hand
  choice.
- **The platform list.** `_on_platform_changed` sets the platform's default
  as today, then re-runs detection on `_front_image_path` when there is
  one, and clears `_case_by_hand`.
- **Batch.** § 4.6.

### 4.4 Building a jewel case's faces

New `core/jewel.py`. One function builds the faces both `render` and
`build_box_model` use, so the still render and the box file cannot differ:

```python
JEWEL_PX_PER_MM_MAX = 16   # LaunchBox 1200 px at 2x supersampling needs
                           # about 15.5 px/mm on a PAL case at 30 degrees

@dataclass
class JewelFaces:
    front: Image.Image          # RGBA, case W x H: hinge strip + booklet
    back: Image.Image | None    # RGBA, case W x H: card middle on plastic
    hinge: Image.Image          # RGBA, case D x H: the spine on the front's left
    opening: Image.Image        # RGBA, case D x H: the side opposite

def back_has_strips(image: Image.Image, case_type: CaseType) -> bool: ...
def detect_strip_folds(image: Image.Image, case_type: CaseType) -> tuple[int, int]: ...
def split_back_card(image, case_type, left_offset=0, right_offset=0,
                    folds=None) -> tuple[Image.Image, Image.Image, Image.Image]:
    """(left strip, middle, right strip) of a back card scan."""
def jewel_faces(front_image, back_image, case_type, *, title, serial,
                platform, spine_color, spine_left_offset, spine_right_offset,
                full_cover, back_strips) -> JewelFaces: ...
```

**Scale.** Faces are built at `p = min(front_image.height / booklet_h,
JEWEL_PX_PER_MM_MAX)` px per mm, from the booklet, or from the wrap's front
panel when the front is a wrap.

**Front.** A case-size canvas filled with `plastic`. The booklet image is
resized to the booklet area and pasted. The area's top, bottom and right
margins are equal: `m = (H − booklet_h) / 2`. The strip left of it,
`W − m − booklet_w` wide, is the hinge strip: tray plastic seen through the
lid. Every jewel case is 142 × 125 with a 120 × 120 booklet, so the strip
is 19.5 mm on each. The user confirms it is the same on every jewel case
(§ 3); the 19.5 mm is computed, U. The hinge strip is geometry, so it is drawn whatever
`show_texture` says.

**Back card.** `back_strips` None means detect: `back_has_strips` compares
the image's width/height with the card's ratio with strips
(`back_card_w / back_card_h`) and without them
(`(back_card_w − 2·strip) / back_card_h`). The nearer ratio, measured
relatively, wins. A 15% band, as `is_full_cover` uses, would not work here.
The standard card's two ratios are 1.271 and 1.169, 8.7% apart, so such a
band takes a back without strips for one with them.

**Folds.** `detect_strip_folds` estimates each fold from the geometry, at
`strip / back_card_w` of the width from each end. It then moves each fold
by the same multi-band edge search `_refine_spine_bounds` uses (STANDARDS.md
§ 5). The search's `_nudge`, and the per-band column means it reads, now
`_fold_band_means`, are lifted to module level in `core/image_utils.py`
so both callers share them. The 85–115% width check is
not applied, because the folds bound the middle, not a spine.
`split_back_card` adds the offsets, then clamps each fold to at least one
pixel from either edge and from the other fold, as `split_full_cover`
clamps its bounds. Three parts need three pixels, so `jewel_faces` treats
a back scan under 3 px wide as a card without strips.

**Which strip goes where.** A back scan is seen from behind, and from behind
the hinge is on the right. So the scan's **right** strip is the hinge side
and its **left** strip is the opening side. This matches the wrap layout,
whose spine sits right of the back.

**Face sources**, in priority order:

| Face | 1st | 2nd | 3rd |
|---|---|---|---|
| back | the loaded back card's middle (strips cut off when it has them) | a wrap's back panel | None |
| hinge | the loaded back card's right strip | a wrap's spine | `generate_spine` |
| opening | the loaded back card's left strip | — | `generate_spine` |
| front | the wrap's front panel, when the front is a wrap | the front image | — |

`generate_spine` is called as `render` calls it today, filling the whole
D × H face. A strip from a scan, or a wrap's spine, is resized to
`strip × back_card_h` and centred on a D × H canvas of `plastic`. The back's middle,
`(back_card_w − 2·strip) × back_card_h`, is centred on a W × H canvas of
`plastic`.

**A wrap for a jewel case** is back middle, then hinge strip, then booklet.
`is_full_cover` and `_geometric_spine_bounds` take their panel widths and
height from a new `wrap_panels_mm(case_type) -> (back, spine, front, height)`
in `core/image_utils.py`. For the wrap layout it returns
`(width, depth, width, height)`, which is today's arithmetic unchanged. For
a jewel case it returns `(back_card_w − 2·strip, strip, booklet_w,
back_card_h)`. The expected wrap ratio for the standard case becomes 2.237;
today's `CD Jewel Case` gives 1.834 (both computed from the table,
2026-10-21). See § 14 and § 15.

### 4.5 Using the faces

- **`BoxRenderer.render`**, when `case_type.layout == "jewel"`, calls
  `jewel_faces` in place of the full-cover block. It then sets
  `front_image = faces.front`, `back_image = faces.back` and
  `extracted_spine = faces.hinge`. Everything after (back view, texture,
  shading, warp, effects) is unchanged. The top and bottom colours are
  `case_color or case_type.plastic`, never sampled from the art. A new
  keyword, `back_strips: bool | None = None`, is passed through.
- **`build_box_model`**, for a jewel case, calls `jewel_faces` with the
  same arguments and scales each face with `_scaled`. The front and back
  use aspect W/H; the hinge and the opening use D/H. `top`, `bottom` and
  `edge` are `case_color or case_type.plastic`. `BoxModel` gains
  `edge_face: Image.Image | None = None`, the opening side's picture,
  flattened like the others. It also gains a `back_strips` keyword. For the
  wrap layout `edge_face` is None and nothing else changes.
- **`RenderWorker` and `AnimationWorker`** in `ui/workers.py` gain
  `back_strips` and pass it to both calls. `MainWindow` passes
  `_back_strips_choice()`, which works as `_full_cover_choice` does: None
  unless the user was asked.
- **The UI.** With a jewel case and a back loaded, a new checkbox,
  `back_strips_check`, reads "Back scan has end strips: put them on the
  case's sides". It sits in the Back Cover group. It is shown ticked when
  `back_has_strips` says so, and the user can untick it. When the front is not a wrap, the Spine Boundary
  Adjustment sliders move the back card's folds, its three thumbnails
  show left strip, middle and right strip, and the full-cover checkbox is
  hidden, so `_full_cover_choice` stays None. When the front is a wrap, the
  sliders stay with the wrap and the back's folds come from detection
  alone.

### 4.6 Batch

`BatchWorker` gains `case_types: list[CaseType] | None = None`, one per file.
`_args_for` uses the file's own case where the list is given. `MainWindow`
builds the list with a new `_batch_cases(files)`. When `_case_by_hand` is
set, every file gets the shown case. Otherwise each file gets
`case_for(platform, detect_region(Path(f).name))`, or the shown case when
that returns None.

### 4.7 Plastic and shine

`core/case_texture.py` dispatches on `case_type.layout == "jewel"` where it
now tests the name `"CD Jewel Case"`, so every jewel entry gets the jewel
overlays. The jewel front overlay gains a lid shine. It is drawn by a new
`generate_lid_shine(w, h)`, composited onto the overlay rather than drawn
over it: white, with alpha `round(SHINE_ALPHA · max(0, 1 − x/w − y/h))`,
`SHINE_ALPHA = 48`. So the shine is strongest at the top-left and gone past
the diagonal. The value is Slipcase's, judged by eye at build. The shine is a case detail, so it follows
`show_texture`. The back already carries the front overlay mirrored
(SLIP-0104 § 4.2), so the clear base shines too. The opening side gets no
overlay. No logos (§ 9).

### 4.8 The box file

The box file gains one optional face, `edge`: the opening side's picture,
`S.edge.png`. It is the side `colours.edge` already names, which is why the
key reuses that word. Version stays 1. The exact changes to SLIP-0104 are
in § 16.

**Why a version 1 reader still draws a right-enough box.** SLIP-0104
§ 4.1 tells readers to ignore keys they do not know. A reader that ignores
`faces.edge` fills the opening side with `colours.edge`. For a jewel case
that is `plastic`, unless the user chose a case colour. Its front picture
already holds the hinge strip and shine, and its spine and back pictures
already hold the strips and the bare plastic (SLIP-0104 INV-11 bakes
details into faces). So the only loss is the opening strip's print. The
reader shows bare tray plastic there, which is what an empty jewel case
shows.

## 5. Invariants

- **INV-1** — `detect_region` returns the region of the first part, in the
  first parenthesised group, that is a whole known region word, else
  `NTSC-U`.
  *Test:* `tests/test_region.py::test_detect_region` with
  `Ridge Racer Type 4 (Europe).png` → PAL, `Game (USA, Europe).png` →
  NTSC-U, `Tomb Raider (PSX) (USA).png` → NTSC-U,
  `Game (PSX) (Japan).png` → NTSC-J, `Game (France) (Rev 1).png` → PAL,
  `Game (En,Fr,De).png` → NTSC-U, `Europa (Demo).png` → NTSC-U,
  `Game (Europa Demo).png` → NTSC-U, `Game.png` → NTSC-U.
  *Breaks when:* only the first group is read (the `(PSX) (Japan)` fixture
  then gives NTSC-U, and only this rule turns it into NTSC-J), or words are
  matched as substrings (`EU` inside `(Europa Demo)` gives PAL). The
  `Europa (Demo)` fixture cannot catch a substring match: its title is
  outside the brackets, which are all that is read.

- **INV-2** — `case_for` returns a platform's regional variant where
  `REGIONAL_CASES` has one, else the platform's default. Every platform
  still has exactly one default.
  *Test:* `tests/test_region.py::test_case_for`: (PS1, PAL) →
  `PS1 Jewel Case (PAL)`; (PS1, NTSC-U) → `PS1 Jewel Case (NTSC-U)`;
  (Dreamcast, NTSC-J) → `Dreamcast Jewel Case (NTSC-J)`; (PS2, PAL) →
  `DVD Case`; (Saturn, PAL) → `CD Jewel Case`. Plus the existing
  `tests/test_regressions.py::test_each_platform_maps_to_exactly_one_case`.
  *Breaks when:* a variant lists its platform in `platforms`, so
  `PLATFORM_CASE_MAP`, built by overwriting, makes it the default.

- **INV-3** — Loading a cover sets the detected case. A hand choice in the
  case list holds until the next cover load or platform change, and
  detection never counts as a hand choice.
  *Test:* `tests/test_jewel.py::test_hand_choice_holds_for_one_cover`
  (a `MainWindow`, as `tests/test_box_file.py` builds one). With platform
  PS1, `_detect_case("A (Europe).png")` shows `PS1 Jewel Case (PAL)` and
  leaves `_case_by_hand` False. A hand pick of `PS1 Jewel Case (NTSC-J)`
  (`setCurrentIndex` then `activated.emit`) sets it, and `_batch_cases`
  gives that case for `B (Europe).png`. `_detect_case("C (USA).png")` then
  shows the NTSC-U case and clears the flag.
  *Breaks when:* the flag is set from `currentIndexChanged`, which
  detection's own `setCurrentIndex` fires, or a load does not clear it.

- **INV-4** — `back_has_strips` picks the nearer of the two card ratios.
  *Test:* `tests/test_jewel.py::test_back_has_strips` on blank images:
  PS1 PAL 1580 × 1180 → True and 1310 × 1180 → False; `CD Jewel Case`
  1500 × 1180 → True and 1380 × 1180 → False.
  *Breaks when:* a 15% band around the with-strips ratio is used, which
  calls the standard 1380 × 1180 middle (1.169, within 8.7% of 1.271) a
  card with strips. That fixture is the one only the nearest-ratio rule
  rejects.

- **INV-5** — A back card's right strip becomes the hinge face, its left
  strip the opening face, and its middle the back. The offsets move the
  folds.
  *Test:* `tests/test_jewel.py::test_strips_go_to_their_sides`. A PS1 PAL
  card drawn red | green | blue in the card's proportions goes through
  `jewel_faces` with `show_texture` off and a plain booklet. Then: the
  hinge face's centre is blue, the opening face's centre red, the back's
  centre green. With `spine_left_offset=+20` the left fold of
  `split_back_card` moves 20 px right.
  *Breaks when:* the left strip is put on the hinge side, or the offsets
  are not passed to `split_back_card`.

- **INV-6** — A jewel front is `plastic` in the hinge strip and the booklet
  in the booklet area. Top, bottom and edge colours are
  `case_color or plastic`, never sampled from the art.
  *Test:* `tests/test_jewel.py::test_front_layout_and_colours`. A uniform
  red booklet on `PS1 Jewel Case (PAL)`, `show_texture` off, through
  `build_box_model`. The front at x = 9 mm and mid-height is `#101010`, and
  at the booklet area's centre is red. `top`, `bottom` and `edge` are
  `#101010`, and with `case_color=(0, 0, 255)` all three are blue.
  *Breaks when:* the booklet is stretched over the whole front, or the
  colours come from `extract_dominant_edge_color` of the loaded art (a red
  booklet then gives red). Sampling the built front face is not caught:
  its edges are plastic margin, so it gives the plastic by chance.

- **INV-7** — Face sources follow § 4.4's priority table.
  *Test:* `tests/test_jewel.py::test_face_sources`, three cases on
  `CD Jewel Case`. Front only: `back` is None, and `hinge` and `opening`
  equal `generate_spine`'s output for the same title, size and platform.
  A wrap: `hinge` holds the wrap's spine and `opening` is generated. A wrap
  plus a back card with strips: `back`, `hinge` and `opening` come from the
  card.
  *Breaks when:* the wrap's spine wins over a loaded card's strip, or a
  missing back card gives a back face made of plastic, not None.

- **INV-8** — `render` and `build_box_model` build a jewel case from one
  `jewel_faces` call each, with the same arguments.
  *Test:* `tests/test_jewel.py::test_render_and_model_share_faces` patches
  `jewel_faces` where `core.renderer` and `core.box_model` import it,
  records both calls for one input, and compares the arguments.
  *Breaks when:* either path builds jewel faces its own way, or drops
  `back_strips` or the offsets.

- **INV-9** — The wrap layout is unchanged. For a case with `jewel` None,
  `wrap_panels_mm` gives `(width, depth, width, height)`, and `edge_face`
  is None.
  *Test:* `tests/test_jewel.py::test_wrap_layout_unchanged` checks
  `wrap_panels_mm` for every wrap entry of `CASE_TYPES`, and that a
  `DVD Case` model has `edge_face` None. The existing
  `tests/test_box_model.py::test_full_cover_faces` and
  `tests/test_renderer.py` still pass.
  *Breaks when:* a jewel rule leaks into the shared split, for example
  paper widths used for every case.

- **INV-10** — Trust boundary: a back scan is any image the user loads,
  of any size, and the offsets come from the sliders. `split_back_card`
  never returns an empty crop and never raises for a 3 × 3 image or
  offsets of ±1000.
  *Test:* `tests/test_jewel.py::test_split_survives_extremes`, each
  combination, with every returned part at least 1 px wide.
  *Breaks when:* the folds are clamped before the offsets are added, or
  one fold may cross the other.

- **INV-11** — Every jewel entry gets the jewel overlays, and the jewel
  front overlay is brighter at the top-left than at the bottom-right.
  *Test:* `tests/test_jewel.py::test_jewel_overlays`: for each jewel entry,
  `generate_front_texture` at 284 × 250 has alpha at (10, 10) above alpha
  at (274, 240), and `generate_lid_shine(284, 250)` has alpha `SHINE_ALPHA`
  at (0, 0) and 0 at (283, 249). The existing
  `tests/test_renderer.py` check that every case's overlay is non-empty
  covers the new entries.
  *Breaks when:* the dispatch still tests the name `"CD Jewel Case"`, so
  the other jewel entries fall through to an empty overlay.

- **INV-12** — An old box file and an old setting naming `CD Jewel Case`
  still load.
  *Test:* `tests/test_jewel.py::test_old_jewel_name_still_loads`. A version
  1 box file written with `case` `{"name": "CD Jewel Case", "width_mm":
  125, "height_mm": 142, "depth_mm": 10.4}` and no `faces.edge` reads with
  width 125 and `edge_face` None. A config holding `last_case_type` `CD
  Jewel Case` restores that case in `case_combo`.
  *Breaks when:* `read_box_file` starts looking case names up in
  `CASE_TYPES`, or the entry is renamed.

- **INV-13** — A batch gives each file its detected case, unless the case
  was picked by hand.
  *Test:* `tests/test_jewel.py::test_batch_cases`. Platform PS1, files
  `A (Europe).png` and `B (USA).png`: `_batch_cases` gives the PAL and
  NTSC-U cases, and `BatchWorker._args_for` passes each file its own. With
  `_case_by_hand` set, both get the shown case.
  *Breaks when:* `BatchWorker` keeps one `_case_type` for every file, as
  today.

## 6. Failure modes

- **A file name with no tag, or a wrong one.** It is treated as US, as the
  user decided. The user picks the right case in the list (INV-3).
- **A platform with no regional row.** `case_for` falls back to its
  default, so a Saturn PAL game gets `CD Jewel Case` (INV-2).
- **Strip detection picks wrong.** The user unticks or ticks
  `back_strips_check`. A scan whose ratio sits midway is the likely case.
- **Folds found in the wrong place.** The sliders move them; `split_back_card`
  clamps them (INV-10).
- **A wrap and a back card with strips, both loaded.** The card supplies
  back and both strips. The sliders stay with the wrap, so the card's folds
  cannot be nudged. The user can clear the wrap or the card.
- **Unverified sizes are wrong.** The back card and strip widths, and the
  hinge strip, are working values (§ 4.1, § 15). A wrong one makes the
  case look a little off. Each is one table row to change.
- **A user's PS1 wrap stops being detected**, because the jewel wrap ratio
  moves from 1.834 to 2.237. Detection is the only way the full-cover
  checkbox appears, so such a wrap renders as a front-only cover. § 15 asks
  for the user's wraps to be measured before build.
- **A version 1 reader that ignores `faces.edge`** shows bare plastic on
  the opening side (§ 4.8). A reader that refuses unknown keys breaks
  SLIP-0104 § 4.1 and is that reader's defect.
- **The back view of a jewel case with no back card** raises, as `render`
  does today for any case without a back, and the UI does not offer it.

## 7. Tests

| Test | Locks |
|------|-------|
| `tests/test_region.py::test_detect_region` | INV-1 |
| `tests/test_region.py::test_case_for`, `tests/test_regressions.py::test_each_platform_maps_to_exactly_one_case` | INV-2 |
| `tests/test_jewel.py::test_hand_choice_holds_for_one_cover` | INV-3 |
| `tests/test_jewel.py::test_back_has_strips` | INV-4 |
| `tests/test_jewel.py::test_strips_go_to_their_sides` | INV-5 |
| `tests/test_jewel.py::test_front_layout_and_colours` | INV-6 |
| `tests/test_jewel.py::test_face_sources` | INV-7 |
| `tests/test_jewel.py::test_render_and_model_share_faces` | INV-8 |
| `tests/test_jewel.py::test_wrap_layout_unchanged` | INV-9 |
| `tests/test_jewel.py::test_split_survives_extremes` | INV-10 |
| `tests/test_jewel.py::test_jewel_overlays` | INV-11 |
| `tests/test_jewel.py::test_old_jewel_name_still_loads` | INV-12 |
| `tests/test_jewel.py::test_batch_cases` | INV-13 |

`tests/test_region.py` and `tests/test_jewel.py` are new. Each test is run
and seen to fail before the code it locks exists. Widget tests keep the
`QApplication` on the class and delete windows with `sip.delete`, as
`tests/test_box_file.py` does. Tests that pin the old portrait jewel
change with it: `tests/test_regressions.py::test_proportions_hold_across_case_types`
keeps `CD Jewel Case` and must pass at the new size.

### 7.1 Manual check

On Linux, render the user's PAL Ridge Racer Type 4 front and back as
`PS1 Jewel Case (PAL)`. Check by eye: the hinge strip is black, the right
strip of the back scan is on the hinge side, the 3D view shows the left
strip on the opening side, and the lid shine is soft. Repeat with a
Dreamcast front only, and check the clear tray reads as clear.

## 8. Alternatives considered (and rejected)

- **The hinge side takes the back scan's left strip**, as first proposed.
  From behind, the hinge is on the right, so the right strip folds onto it.
  Taking the left one would put each strip on the wrong side.
- **A separate case type for Saturn JP, Mega-CD JP and PC CD-ROM.** No
  source gives them anything that differs from the standard jewel case, so
  each would be a second name for `CD Jewel Case`. Mega-CD is not a
  platform in `ALL_PLATFORMS`, nor in the ScreenScraper, TheGamesDB or
  libretro maps under `api/`. Adding it is a platform item, not a case.
- **Rename `CD Jewel Case`.** Config files (`ui/last_case_type`) and box
  files store the name. Keeping it as the generic standard case needs no
  migration (INV-12).
- **Box file version 2 with a `layout` key.** A version 1 reader would
  refuse every jewel box, though version 1 can carry it with one optional
  face (§ 4.8). RetroDB's importer is being built against version 1.
- **The opening strip under `faces.spine_right`.** `colours.edge` already
  names that side, and a reader without the picture falls back to that
  colour. The same word for the same side keeps the fallback obvious.
- **A 15% band for back-strip detection**, as `is_full_cover` uses. On the
  standard card it cannot tell the two cases apart (INV-4).
- **Shine baked in whatever `show_texture` says.** The user could then not
  get a flat case. The hinge strip, which is geometry, is baked in always.
- **Compositing the jewel faces inside the renderer only.** The box file
  would then have to repeat it. SLIP-0104 already found two paths deciding
  faces separately to be a source of drift (its INV-5), hence one function.

## 9. Out of scope

- Sizes and colours for every other system (keep cases, handhelds) —
  phase 2, queued as SLIP-0107.
- Cartridge boxes — phase 3, queued as SLIP-0108.
- The US long box (Saturn US, Sega CD US, early PS1 US) — deferred; not
  yet queued. Its art layout is unverified (research file).
- Early 18 mm NTSC-J PS1 cases — deferred; not yet queued. The user can
  pick `PS1 Jewel Case (PAL)` for the depth meanwhile, but its tray and
  paper are PAL's.
- Moulded logos (the PS1 PAL embossed logo) — deferred; not yet queued, by
  the user's decision.
- Multi-disc "multiway" and fat cases — deferred; not yet queued; no depth
  is sourced.
- A Sega CD / Mega-CD platform — deferred; not yet queued (§ 8).
- Region read from ScreenScraper results — deferred; not yet queued.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 | `tests/test_region.py::test_detect_region` |
| INV-2 | `tests/test_region.py::test_case_for`, `tests/test_regressions.py::test_each_platform_maps_to_exactly_one_case` |
| INV-3 | `tests/test_jewel.py::test_hand_choice_holds_for_one_cover` |
| INV-4 | `tests/test_jewel.py::test_back_has_strips` |
| INV-5 | `tests/test_jewel.py::test_strips_go_to_their_sides` |
| INV-6 | `tests/test_jewel.py::test_front_layout_and_colours` |
| INV-7 | `tests/test_jewel.py::test_face_sources` |
| INV-8 | `tests/test_jewel.py::test_render_and_model_share_faces` |
| INV-9 | `tests/test_jewel.py::test_wrap_layout_unchanged` |
| INV-10 | `tests/test_jewel.py::test_split_survives_extremes` |
| INV-11 | `tests/test_jewel.py::test_jewel_overlays` |
| INV-12 | `tests/test_jewel.py::test_old_jewel_name_still_loads` |
| INV-13 | `tests/test_jewel.py::test_batch_cases` |
| § 4.1 unverified sizes match real cases | **nothing** — the user's measurements (§ 15) |
| The case looks like the real one | **nothing** — § 7.1, by eye |
| SLIP-0104 INV-13 and INV-14 (§ 16) | the tests SLIP-0104 names for them |

## 11. Cross-doc impact

- `docs/specs/SLIP-0104-turnable-3d-box.md`: amended in place, § 16; a
  labelled non-review row in its loop log names SLIP-0106 as the origin.
- `ROADMAP.md` SLIP-0106: its body names this spec and SLIP-0104.
- `STANDARDS.md`: § 2 (new `core/jewel.py`, `core/region.py`); § 4
  (`CaseType`'s new fields; pipeline step 2's ratio comes from
  `wrap_panels_mm`); § 5 (geometric estimate from `wrap_panels_mm`; the
  back card's folds); § 9 (two new test files).
- `docs/subsystems.md`: case-model gains `core/region.py`; image-analysis
  gains `core/jewel.py`.
- `README.md`: the case list and a line on region from the file name.
- `CHANGELOG.md`: Added (jewel cases per region) and Changed (the jewel
  case's orientation).
- RetroDB: told that version 1 gains the optional `faces.edge`
  (SLIP-0104 § 4.1 as amended).

## 12. Cold-eyes loop log

Rows live in `../reviews/SLIP-0106-jewel-cases-loop-log.md`.

## 13. Resource cost

- No new dependency.
- Memory: `jewel_faces` holds at most two case-size RGBA canvases at 16
  px/mm. Every jewel case is 142 × 125 mm, so each is 2272 × 2000 × 4
  bytes, about 18 MB, so about 36 MB plus two small edge faces. They are released
  when the call returns. `RenderWorker` runs the render's call and the
  model's call one after the other, so the peak is one set.
- `BoxModel` gains one D × H face, capped as every face is (SLIP-0104 § 13).
- Disk: one more PNG per jewel box file.

## 14. Migration / compatibility

- **Saved settings.** `ui/last_case_type` `CD Jewel Case` still names a
  case (INV-12). That case is now the landscape standard jewel case, so a
  PS1 user who last chose it sees the generic black-tray case. Choosing the
  platform again picks `PS1 Jewel Case (NTSC-U)`.
- **Old box files** keep their own `case` sizes. `read_box_file` never
  looks a name up (INV-12), and a missing `faces.edge` is null.
- **`CaseType` callers** pass four positional or keyword fields today. The
  new fields have defaults, and `CaseType` stays frozen and picklable for
  `BatchWorker`'s spawned processes.
- **Wrap detection for jewel cases moves** (§ 4.4, § 6, § 15).

## 15. Open questions

1. **Dreamcast PAL depth, and PS1 PAL booklet and card.** Answered by the
   user, 2026-10-21 (§ 3): the Dreamcast PAL case is 10.4 deep, and the
   PS1 PAL case is a music CD case but 18 deep. The PS1 PAL card is
   measured from the user's scan (§ 4.1) and remains U.
2. **The hinge strip's width.** Answered by the user, 2026-10-21 (§ 3): the
   same on every jewel case. Its 19.5 mm is computed, not measured, U.
3. **How the user's existing PS1, Saturn and Dreamcast wraps are
   proportioned.** Answered 2026-10-21 by measuring the box art in
   RetroDB's library (`static/images/boxart`, systems from its
   `roms.db`): 340 PS1 images and 1 Dreamcast image readable, no Saturn.
   None is a wrap. The images wider than 1.5 are 16:9 promotional art,
   not scans: 34 PS1 images between 1.5 and 1.85, none near 2.237. So
   § 4.4 stands, and no wrap in that library stops being detected.
4. **Tray colour of the generic case and the PS1 NTSC-U and NTSC-J cases**
   (black). Taken as black (Slipcase, 2026-10-21, the user's veto open),
   as the PS1 PAL source gives for PAL. A second account supports black
   for NTSC-U (§ 4.1). NTSC-J varies by release, so its black stays U, as
   does the generic case's.
5. **Does a hand-picked case hold for one cover or for the session?**
   Taken as one cover (§ 3). A mislabelled file is a one-game problem,
   and a session-long hold would silently give every later cover the
   wrong region.
6. **SLIP-0106's phases 2 and 3 under the same id.** One spec per id
   (spec-format § 2). Done 2026-10-21: queued as SLIP-0107 and SLIP-0108,
   each to be specced on its own.

## 16. Amendments to SLIP-0104

Applied to `docs/specs/SLIP-0104-turnable-3d-box.md` in place, in the same
commit as this spec. Once applied, SLIP-0104 holds the format text and this
section is only the record of what changed. Nothing is renumbered.

- **§ 4.1, the file list.** "four files sit in one folder" becomes "up to
  five files". `S.edge.png  opening side (absent when there is none)` is
  added after `S.back.png`.
- **§ 4.1, `faces`.** The example gains `"edge": "S.edge.png"`. A sentence
  is added: "`edge` is the opening side's picture, or `null` when there is
  none; a viewer then fills that side with `colours.edge`. Readers that do
  not know `edge` ignore it, as any unknown key."
- **§ 4.1, orientation.** A sentence is added: "The edge is on the front's
  right as seen from the front."
- **§ 4.1, reading rules.** "a `back` that names a missing file" becomes
  "a `back` or `edge` that names a missing file". The name rule covers
  `edge`.
- **§ 4.2.** `BoxModel` gains `edge_face: Image.Image | None = None`, and
  `build_box_model` gains `back_strips`. A sentence is added: "A jewel case
  (`case_type.layout == "jewel"`) builds its faces with SLIP-0106 § 4.4's
  `jewel_faces`; the rest of this section describes the wrap layout."
- **§ 4.3.** `box_paths` returns "the five paths", with `edge` last.
  `write_box_file` clears and writes `edge` like `back`.
- **§ 4.4.** "any of the four `box_paths`" becomes "any of the five", in
  both places.
- **§ 4.5.** The viewer draws `edge_face` on the edge side when it is
  present, converted once per model like the other faces.
- **INV-1.** The face names become "`S.front.png`, `S.spine.png`, and each
  of `S.back.png` and `S.edge.png` or `null`".
- **INV-2.** One fixture is added: an `edge` naming a missing file.
- **INV-5.** Scoped: "For the wrap layout, …".
- **INV-13 (new).** A jewel box file names `S.edge.png` and the file holds
  `edge_face`; a wrap box file writes `"edge": null` and no `S.edge.png`.
  *Test:* `tests/test_box_file.py::test_edge_face_written`. *Breaks when:*
  the writer drops the edge face, or leaves an old `S.edge.png` behind when
  the stem is rewritten as a wrap box.
- **INV-14 (new).** A reader that ignores `faces.edge` still reads a jewel
  box file whole, with the opening side's colour equal to the case's
  plastic. *Test:* `tests/test_box_file.py::test_v1_reader_without_edge`
  deletes the key from a written jewel file's JSON, reads it, and checks
  `edge_face` is None and `edge` is `plastic`. *Breaks when:* `colours.edge`
  is sampled from the art for a jewel case, or `edge` is made required.
- **§ 7 and § 10** gain rows for INV-13 and INV-14; `test_box_paths`
  expects five paths.
