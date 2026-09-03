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

## Security Requirements
These MUST be maintained in all code changes:
- **URL allowlist**: `api/base.py` restricts every request -- image downloads
  and JSON API calls alike -- to known domains over HTTPS
  (`ALLOWED_IMAGE_DOMAINS`, checked by `_is_allowed_url`). The name is
  historical: the check covers both paths, and is re-run on every redirect
  hop so a 302 cannot move the fetch to another host or drop TLS
- **Credential scrubbing**: API errors strip passwords/keys before display (`_sanitize_message`)
- **Download limit**: 50MB max per image download (`MAX_DOWNLOAD_BYTES`), and
  a wall-clock budget per download (`MAX_DOWNLOAD_SECONDS`). The byte cap
  alone does not bound a trickle: the request timeout is per-read, so a
  slow drip never reaches either limit
- **TLS only**: All API requests use HTTPS with `verify=True`
- **Config permissions**: `~/.config/slipcase/` dir gets `0o700`, config file gets `chmod 600`
- **Decompression bomb**: `MAX_IMAGE_PIXELS` (40M) defined and applied in
  `api/base.py`, so the download path is protected without depending on
  `main.py` having run; `download_image()` also checks the pixel count
  explicitly, because Pillow only warns at that value
- **No code execution**: User text (titles, serials) is rendered as image text only, never eval'd

## Performance Requirements
These optimisations MUST be preserved in all code changes:
- **PNG export**: Use `save_optimized_png()` for all PNG saves — LSB strip, alpha quantization, opaque RGB conversion, and a zlib level from the
  `rendering.compress_level` config key (default 6; 9 is ~5% smaller and 2-4x
  slower). The animated-export path is exempt: a multi-frame APNG/GIF cannot
  route through a single-image saver.
- **Shadow blur**: Blur alpha channel only (L mode), not full RGBA (~4x faster)
- **Perspective transform**: `_perspective_quad` transforms padded source directly to canvas (no intermediate canvas allocation)
- **Combined faces**: Top and bottom box faces rendered on single canvas layer
- **Vectorized operations**: NumPy for shading gradients; replicate-edge padding
  before the perspective transform — `cv2.copyMakeBorder(..., BORDER_REPLICATE)`,
  or `np.pad(mode='edge')` on the PIL fallback

## Memory Management Requirements
These patterns MUST be followed in all code changes:
- **`del` intermediates**: In `renderer.render()`, delete large PIL images immediately after their last use
- **In-place operations**: AnimationWorker normalizes/converts frames in-place (no separate `normalized` or `rgb_frames` lists)
- **Worker cleanup**: All QThread workers must connect `finished.connect(worker.deleteLater)`
- **File handle release**: Always call `img.load()` after `Image.open(path)` to release the file handle
- **API session cleanup**: Close API client sessions in `finally` blocks in worker threads
- **Cache cleanup**: SearchDialog clears `_preview_cache` and `_results` on close
- **Close cleanup**: `MainWindow.closeEvent` waits for running workers and clears all image references
- **Batch processing**: `del img` after render, `del result` after save — never accumulate images across loop iterations
