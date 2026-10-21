<!-- ants-spec-format: 1 -->
# SLIP-0107 — Give keep cases and handheld cases their real size and plastic, per region

**Status:** spec draft (2026-10-21).
**Kind:** feature.
**Source:** ROADMAP SLIP-0107 (user-request-2026-10-21). Phase 2 of
SLIP-0106. Research:
[`../research/SLIP-0106-real-cases.md`](../research/SLIP-0106-real-cases.md),
and Wikipedia, Keep case, re-read 2026-10-21 (revision of 3 September
2026). Source: https://en.wikipedia.org/wiki/Keep_case
**Pairs with:** SLIP-0106 (reuses its `plastic` field, region detection
and lid shine).

**Layman:** DVD-style and handheld game cases get the right size and
plastic for each console and region: a European PS2 case is blue, a Wii
case white, a Switch case clear, and the case list names each console's
case.

## 1. Goal

Each disc keep case and handheld case renders at its real size, with its
real plastic. An opaque case's top, bottom and opening edge are its
plastic colour. A clear or tinted case shows the cover through the
plastic, with a soft shine on the front. Each console has its own entry
in the case list, and a region variant where the region's case differs.
The console picks its case and the cover's file name picks the region,
as for jewel cases.

## 2. Problem

1. **Six consoles share one case.** `CASE_TYPES["DVD Case"]` in
   `core/case_types.py` lists PS2, Wii, Xbox, Xbox 360, PC and GameCube,
   and `CASE_TYPES["Blu-ray Case"]` lists PS3 to PS5, Xbox One and Xbox
   Series X. Xbox and Xbox 360 cases are smaller than a DVD case (research
   file), and each console's plastic differs (Wikipedia, Keep case).
2. **Some sizes are wrong.** PSP is `105 × 170 × 14` against the source's
   `99 × 168 × 14`; PS Vita `107 × 135` against `105 × 135`; DS depth
   `14` against `15`, and the European DS case is `20` deep; Switch is
   `104 × 169 × 10.5` against `104 × 170 × 10`.
3. **The plastic is guessed from the art.** For the wrap layout,
   `BoxRenderer.render` colours the top and bottom with
   `extract_dominant_edge_color` of the front, and `build_box_model` does
   the same, unless the user picks a case colour. `CaseType.plastic` says
   "the wrap layout ignores it for now".
4. **The overlays are chosen by case name.** `generate_front_texture` and
   `generate_spine_texture` in `core/case_texture.py` compare
   `case_type.name` with `"DVD Case"`, `"Switch Case"` and so on, so a
   renamed or added case loses its overlay.

## 3. Scope decisions (agreed with the user)

- **Opaque cases: real plastic edges.** User, 2026-10-21: the top, bottom
  and opening edge take the plastic colour, as jewel cases do. Case Color
  still overrides.
- **Clear cases: cover colour plus shine.** User, 2026-10-21: the edges
  keep the colour sampled from the cover, which a real clear case shows
  through its plastic, and the front gets a soft shine.
- **One entry per console.** User, 2026-10-21: names such as "PS2 DVD
  Case" and "DS Case (PAL)", like the PS1 jewel cases. The console picks
  its case and the region its variant.
- **PS2 by region.** User, 2026-10-21: "Most are blue, platinum versions
  were a matte silver (or more like gray). Some are black but not sure
  when." Wikipedia: "Navy blue or black", "Blue in PAL regions from 2001
  onward". So PAL is blue, NTSC-U and NTSC-J black. Platinum silver is
  out of scope (§ 9).

## 4. Design

### 4.1 Case data

`CaseType` gains two fields:

```python
    # Overlay family for the wrap layout: "dvd", "bluray", "switch", "ds",
    # "psp", "cardboard", or None for no overlay.
    texture: str | None = None
    # Clear or tinted plastic: the cover shows through, so edges keep the
    # cover's colour, tinted by `plastic` when set, and the front shines.
    clear: bool = False
```

`DVD Case` and `Blu-ray Case` are replaced by these entries. Sizes are
W × H × D in mm. "S" = sourced, "W" = working value, judged by eye.

| Name | Platforms | Size | Plastic | Clear | Texture |
|---|---|---|---|---|---|
| PS2 DVD Case | PS2 | 135 × 190 × 14 S | black W | no | dvd |
| PS2 DVD Case (PAL) | — | 135 × 190 × 14 S | navy blue W | no | dvd |
| Wii DVD Case | Wii | 135 × 190 × 14 S | white W | no | dvd |
| GameCube DVD Case | GameCube | 135 × 190 × 14 S | black W | no | dvd |
| GameCube Case (NTSC-J) | — | 107 × 149 × 17 S | none | yes | dvd |
| PC DVD Case | PC | 135 × 190 × 14 S | black W | no | dvd |
| Xbox Case | Xbox | 129 × 189 × 13 S | lime green W | no | dvd |
| Xbox 360 Case | Xbox 360 | 133 × 187 × 13 S | green tint W | yes | dvd |
| PS3 Blu-ray Case | PS3 | 135 × 171.5 × 13 S | white tint W | yes | bluray |
| PS4 Blu-ray Case | PS4 | 135 × 171.5 × 13 S | blue tint W | yes | bluray |
| PS5 Blu-ray Case | PS5 | 135 × 171.5 × 13 S | blue tint W | yes | bluray |
| Xbox One Case | Xbox One | 135 × 171.5 × 13 S | green tint W | yes | bluray |
| Xbox Series X Case | Xbox Series X | 135 × 171.5 × 13 S | green tint W | yes | bluray |

The handheld entries keep their names and gain `texture` and `plastic`;
their sizes become the sourced ones:

| Name | Platforms | Size | Plastic | Clear | Texture |
|---|---|---|---|---|---|
| DS Case | DS | 122 × 135 × 15 S | black W | no | ds |
| DS Case (PAL) | — | 122 × 135 × 20 S | none | yes | ds |
| 3DS Case | 3DS | 122 × 135 × 12 S | white W | no | ds |
| PSP Case | PSP | 99 × 168 × 14 S | none | yes | psp |
| PS Vita Case | Vita | 105 × 135 × 12 S | blue W | no | psp |
| Switch Case | Switch | 104 × 170 × 10 S | none | yes | switch |

The cartridge boxes and `Universal Cart Case` gain `texture="cardboard"`
and nothing else; SLIP-0108 owns their sizes.

`REGIONAL_CASES` gains `("PS2", "PAL")`, `("DS", "PAL")` and
`("GameCube", "NTSC-J")`.

### 4.2 Edge colours

New in `core/image_utils.py`, used by both `BoxRenderer.render` and
`build_box_model` so the two cannot differ:

```python
def case_edge_colours(front_image, case_type, case_color
                      ) -> tuple[RGB, RGB, RGB]:   # top, bottom, opening edge
```

- `case_color` set: all three are `case_color`.
- Opaque case with `plastic` (jewel or wrap): all three are `plastic`.
- Clear case: top and bottom are `extract_dominant_edge_color` of the
  front at that edge, mixed `CLEAR_TINT` (0.3, working value) toward
  `plastic` when set; the opening edge is the top's colour.
- No `plastic` and not clear: as today, sampled, opening edge = top.

The jewel path keeps `render`'s `_JEWEL_EDGE_LIFT` on top of this.

### 4.3 Overlays and shine

`generate_front_texture` and `generate_spine_texture` dispatch on
`case_type.texture` instead of the name, to the same drawing functions as
today. A clear wrap case's front overlay also gets `generate_lid_shine`
and `_lid_streak`, as a jewel lid does; its back gets them mirrored, as
SLIP-0104 § 4.2 already lays the front overlay on the back.

### 4.4 Saved settings

`ui/last_case_type` may hold a removed name (`DVD Case`, `Blu-ray Case`).
`MainWindow._restore_state` already ignores a name the case list lacks,
and the restored platform has already picked its case, so no migration
is written.

## 5. Invariants

- **INV-1** — Every platform maps to exactly one default case.
  *Test:* `tests/test_regressions.py::test_each_platform_maps_to_exactly_one_case`.
  *Breaks when:* two entries list the same platform.

- **INV-2** — Each case's size, plastic, clear flag and texture match
  § 4.1's tables.
  *Test:* `tests/test_keep_cases.py::test_case_table`.
  *Breaks when:* an entry is edited without the spec, or the PS2 PAL
  variant takes NTSC's black.

- **INV-3** — `render`'s top colour and `build_box_model`'s `top` are
  both `case_edge_colours(...)[0]` for every wrap case, with and without
  a case colour.
  *Test:* `tests/test_keep_cases.py::test_edge_colours_agree`.
  *Breaks when:* either path samples the art for an opaque case.

- **INV-4** — A clear case's front overlay is brighter at its top-left
  than an opaque case's of the same texture family.
  *Test:* `tests/test_keep_cases.py::test_clear_case_shines`.
  *Breaks when:* the shine is keyed to the jewel layout only.

- **INV-5** — Each renamed case draws the overlay its old entry drew.
  *Test:* `tests/test_keep_cases.py::test_overlay_by_family` compares
  "PS2 DVD Case" with `_draw_dvd_front`'s output at the same size, and
  likewise one case per family.
  *Breaks when:* dispatch still reads the name.

- **INV-6** — `case_for("PS2", "PAL")`, `case_for("DS", "PAL")` and
  `case_for("GameCube", "NTSC-J")` give their regional case;
  `case_for("PS2", "NTSC-U")` gives "PS2 DVD Case".
  *Test:* `tests/test_region.py::test_case_for`.
  *Breaks when:* a `REGIONAL_CASES` key is missing.

- **INV-7** — A saved `last_case_type` of "DVD Case" restores the saved
  platform's case without error.
  *Test:* `tests/test_keep_cases.py::test_removed_case_name_restores`.
  *Breaks when:* `_restore_state` trusts the saved name.

## 6. Failure modes

- **A working colour is wrong.** The user picks Case Color, and the
  table is corrected from their report.
- **A clear case's cover edge is a poor colour.** It is today's sampled
  colour; Case Color overrides.
- **A ROM tagged "(Europe)" for a console with no PAL variant.** `case_for`
  falls back to the console's default, as today.

## 7. Tests

New `tests/test_keep_cases.py` holds INV-2, INV-3, INV-4, INV-5 and INV-7.
`tests/test_region.py::test_case_for` gains INV-6's rows. INV-1's test
exists. Each new test is run against the code before the change and
seen to fail.

## 8. Alternatives considered (and rejected)

- **One shared DVD entry coloured by the console.** Rejected by the user
  (§ 3): two consoles' cases could not be told apart in the list.
- **Plastic edges on clear cases too.** Rejected by the user (§ 3): a
  real clear case shows the cover through its edges.
- **Migrating the saved case name.** Not needed (§ 4.4).

## 9. Out of scope

- PS2 Platinum silver, PS3 and Xbox Platinum, Greatest Hits red and other
  edition colours — deferred; not yet queued.
- Wii U and Switch 2 — deferred; not yet queued. Neither is a platform
  in `ALL_PLATFORMS` today.
- The European New 3DS black case — deferred; not yet queued.
- Genesis and Master System cases — SLIP-0108, with the cartridge boxes.
- Moulded logos on keep cases (Xbox 360's embossed top) — deferred; not
  yet queued.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 | `tests/test_regressions.py::test_each_platform_maps_to_exactly_one_case` |
| INV-2 | `tests/test_keep_cases.py::test_case_table` |
| INV-3 | `tests/test_keep_cases.py::test_edge_colours_agree` |
| INV-4 | `tests/test_keep_cases.py::test_clear_case_shines` |
| INV-5 | `tests/test_keep_cases.py::test_overlay_by_family` |
| INV-6 | `tests/test_region.py::test_case_for` |
| INV-7 | `tests/test_keep_cases.py::test_removed_case_name_restores` |

## 11. Cross-doc impact

`CHANGELOG.md` (Changed), `README.md` where it lists case types,
`docs/specs/SLIP-0106-jewel-cases.md` § 9 points here for phase 2, and
`core/config.py`'s `last_case_type` default becomes "PS2 DVD Case".

## 12. Cold-eyes loop log

Rows live in `../reviews/SLIP-0107-keep-cases-loop-log.md`.

No review is planned: the user ruled on 2026-10-21 that specs get no
review-contract run; the code is built from this and corrected where the
build shows it wrong.

## 13. Open questions

- The working colours, judged by eye at build.
- Whether an opaque case's clear outer sleeve should also shine. Today
  only clear cases do (§ 3).
