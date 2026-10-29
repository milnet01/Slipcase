# SLIP-0031 — cold-eyes loop log

Spec: [`../specs/SLIP-0031-auto-update.md`](../specs/SLIP-0031-auto-update.md).

## Cold-eyes loop log

| Loop | Date | Lanes | Q1 | Q2 | Q3 | Q4 | Outcome |
|------|------|-------|----|----|----|----|---------|
| 1 | 2026-10-29 | 2 | 0 | 3 | 3 | 3 | 9 findings, 9 verified / 0 dismissed, 9 fixed. One (Q4, INV-5's import scan covered `tests/`) was found building the packet and fixed before dispatch. Two lanes, each holding every question; both raised the `shutdown_for_update` busy gap and the INV-9 mode-assertion defect. Fixes: busy re-check and `UpdateError` handling on `ready`; the opt-in gate inside `check_for_update`; `ReleaseError` and the progress total in `api/releases.py`; `MainWindow`'s `release_instance` argument; the mode assertion moved to INV-7, POSIX only; INV-9's success leg uses the real `os.replace`. Unrunnable region declared: Windows and macOS runtime, the AppImage runtime, PowerShell, GitHub's live replies. Loop 2 dispatched. |
| 2 | 2026-10-29 | 2 | 0 | 2 | 3 | 4 | 9 findings, 8 verified / 1 dismissed, 8 fixed. Two lanes, each holding every question; both raised that `_busy_worker()` could come to include the update workers, so `ready` would refuse its own install. Fixes: `_busy_worker()` keeps its three workers; the chmod keyed on `AppImageInstaller`; Skip saves through `_save_config()`; the staged names and clean-up suffixes `<ext>` and `<ext>.sig`; INV-3, INV-6, INV-7 and INV-15 tests made able to catch their named mutations. Dismissed: where the verification-failure sentence is produced, which is local to two new modules one builder writes. **Capped** at a spec's cap of 2; the 8 fixes of this loop were read by no lane. Calm cap: 2 of 8 verified findings landed on text this run wrote (`_busy_worker` scope; the POSIX mode clause). No second share: the armed change (b04666b) is the whole document. Status set to accepted. |
