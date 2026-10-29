# SLIP-0031 — cold-eyes loop log

Spec: [`../specs/SLIP-0031-auto-update.md`](../specs/SLIP-0031-auto-update.md).

## Cold-eyes loop log

| Loop | Date | Lanes | Q1 | Q2 | Q3 | Q4 | Outcome |
|------|------|-------|----|----|----|----|---------|
| 1 | 2026-10-29 | 2 | 0 | 3 | 3 | 3 | 9 findings, 9 verified / 0 dismissed, 9 fixed. One (Q4, INV-5's import scan covered `tests/`) was found building the packet and fixed before dispatch. Two lanes, each holding every question; both raised the `shutdown_for_update` busy gap and the INV-9 mode-assertion defect. Fixes: busy re-check and `UpdateError` handling on `ready`; the opt-in gate inside `check_for_update`; `ReleaseError` and the progress total in `api/releases.py`; `MainWindow`'s `release_instance` argument; the mode assertion moved to INV-7, POSIX only; INV-9's success leg uses the real `os.replace`. Unrunnable region declared: Windows and macOS runtime, the AppImage runtime, PowerShell, GitHub's live replies. Loop 2 dispatched. |
