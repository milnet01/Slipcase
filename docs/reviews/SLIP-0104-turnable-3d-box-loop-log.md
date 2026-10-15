# SLIP-0104 — cold-eyes loop log

Spec: [`../specs/SLIP-0104-turnable-3d-box.md`](../specs/SLIP-0104-turnable-3d-box.md).

## Cold-eyes loop log

| Loop | Date | Lanes | Q1 | Q2 | Q3 | Q4 | Outcome |
|------|------|-------|----|----|----|----|---------|
| 1 | 2026-10-15 | 2 (every lane held every question) | 1 | 4 | 1 | 1 | Verified 7, fixed 7, dismissed 2. Q1: parallel batch workers could pick the same stem; stems now picked in BatchWorker before dispatch (INV-6). Q2: single-export stem vs INV-10's _safe_filename; stems the reader refuses; an existing box file vs INV-3; Export PNG's model source vs INV-9. Q3 (from an open question): a back naming a missing file. Q4: round-trip equality impossible (low-bit strip, platforms). Dismissed: colour sampling (render rebinds front_image to the split front, renderer.py:145, outside the packet window); re-run batch stems not matching RetroDB (builds nothing different). NEEDS MEASUREMENT re-run: 6,743,095 bytes, matches. |
