# SLIP-0104 — cold-eyes loop log

Spec: [`../specs/SLIP-0104-turnable-3d-box.md`](../specs/SLIP-0104-turnable-3d-box.md).

## Cold-eyes loop log

| Loop | Date | Lanes | Q1 | Q2 | Q3 | Q4 | Outcome |
|------|------|-------|----|----|----|----|---------|
| 1 | 2026-10-15 | 2 (every lane held every question) | 1 | 4 | 1 | 1 | Verified 7, fixed 7, dismissed 2. Q1: parallel batch workers could pick the same stem; stems now picked in BatchWorker before dispatch (INV-6). Q2: single-export stem vs INV-10's _safe_filename; stems the reader refuses; an existing box file vs INV-3; Export PNG's model source vs INV-9. Q3 (from an open question): a back naming a missing file. Q4: round-trip equality impossible (low-bit strip, platforms). Dismissed: colour sampling (render rebinds front_image to the split front, renderer.py:145, outside the packet window); re-run batch stems not matching RetroDB (builds nothing different). NEEDS MEASUREMENT re-run: 6,743,095 bytes, matches. |
| 2 | 2026-10-15 | 2 (every lane held every question) | 3 | 3 | 1 | 2 | Verified 9, fixed 9, dismissed 0. Q1: back-view colours (render samples the back cover; the box file now always uses the front); CASE_TYPES carries no colour; the PNG dialog does not confirm an existing box file (Export PNG now asks). Q2: INV-3's test vs old faces left behind (write_box_file now clears all four box_paths); INV-2 fixtures missing five rules; § 3's no-renaming claim vs never-overwrite. Q3: hex case unpinned (upper case written, either read). Q4: INV-6 and INV-9 breaches no test could catch (pick_output_stems named and tested; INV-9 clause narrowed). Cap reached (spec cap 2): these fixes are read by no lane; implementation is their reader. Calm cap: 4 of 9 findings landed on loop 1's text. No second share: the armed change is the whole document. |
