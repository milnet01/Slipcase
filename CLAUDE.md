# Slipcase

## Project Overview
Desktop GUI application that converts 2D game cover art into realistic 3D boxart renders.
Compatible with libretro/RetroArch thumbnail system and LaunchBox 3D box art style.

## Tech Stack
- Python 3.12, PyQt6, Pillow, NumPy, OpenCV (headless), SciPy, requests

## Architecture
- `core/` - Rendering engine, case types, image utilities, config
- `ui/` - PyQt6 GUI (main window, preview, settings, search)
- `api/` - Cover art API clients (ScreenScraper, TheGamesDB, libretro)
- `resources/` - Application icons, case colors

## Naming — deliberate exceptions

The app was renamed from "3D Boxart Generator" to Slipcase on 2026-08-27. Two
things were deliberately NOT renamed. Do not "finish" the rename:

- **`softname` in `api/screenscraper.py` stays `BoxArt3D`.** It identifies this
  client to the ScreenScraper API, which may recognise or rate-limit by that
  value. Changing it risks cover-art searches being refused.
- **The phrase "3D boxart" stays** wherever it names the rendered artifact or
  ScreenScraper's pre-rendered asset type (e.g. `boxart3d_selected`,
  `_download_3d_boxart`, "Use 3D Boxart"). It is the domain term, not the
  product name.

## Absolute paths — deliberate exceptions

The repository is public. Some `/mnt/` paths are kept on purpose; a scan for
personal paths will find them, and stripping them would be wrong:

- **`slipcase.desktop` keeps absolute `Exec=` and `Icon=` paths.** The
  freedesktop desktop-entry spec requires them — a relative path does not
  launch.
- **`ROADMAP.md` records retired `/mnt/Storage` and `/mnt/Emulators` paths**
  inside shipped items. Those are a truthful history of what was fixed, not
  live configuration. SLIP-0005 reviewed the tree before publication and
  accepted them.

Claude Code hook paths are the opposite case: they use `$CLAUDE_PROJECT_DIR`
and must stay portable.

## Conventions
- All dimensions in millimeters (real-world case measurements)
- Output: PNG with transparency, max 512px wide for RetroArch, 800-1200px for LaunchBox
- 2x supersampling with LANCZOS downscale for anti-aliasing
- Default viewing angle: 30 degrees, user-adjustable 5-60 (LaunchBox style)

## Running
```bash
python3 main.py
```

## Testing
```bash
python3 -m pytest tests/ -v
```
All tests must pass before any commit. The suite covers case types, image utils,
spine generation, rendering and config (`test_renderer.py`), plus security,
locked regressions, libretro and the search worker in their own files.

## Security, performance and memory rules
These MUST hold in every code change. `STANDARDS.md` owns them, and this
file does not restate them (SLIP-0092). Read the section before changing
code it covers:

- **Security** -- `STANDARDS.md` § 10: URL allowlist and per-hop redirect
  checks, credential scrubbing, download size and time limits, TLS, config
  permissions, decompression-bomb limit, no code execution.
- **Performance** -- `STANDARDS.md` § 11: `save_optimized_png()` for every
  single-image PNG, alpha-only shadow blur, no intermediate canvas in
  `_perspective_quad`, combined top/bottom faces, vectorised shading and
  edge padding.
- **Memory** -- `STANDARDS.md` § 12: `del` intermediates in `render()`,
  in-place frame handling, `deleteLater` on every worker, `img.load()` after
  `Image.open()`, API clients closed in `finally`, caches cleared on close,
  `closeEvent` stops workers before clearing images.

Change a rule in `STANDARDS.md`, never here.
