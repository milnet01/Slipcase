# Slipcase - Standards Document

## 1. Project Overview

**Purpose**: Desktop GUI application that converts 2D game cover art into realistic
3D boxart renders, compatible with libretro/RetroArch thumbnails and LaunchBox.

**Tech Stack**: Python 3.12, PyQt6, Pillow, NumPy, OpenCV (headless), SciPy, requests

**License**: MIT (see `LICENSE`)

**Signs of success**: three of the four things the purpose names carry a
checkable bar, stated later in this document — the interface must never block
(§ 6), and the RetroArch and LaunchBox output targets fix format, transparency
and size (§ 4). The fourth, *realistic*, does not. It is judged by eye by the
project author, and there is deliberately no written test for it. Do not read
the rendering pipeline as that bar: it constrains how a render is produced,
never whether the result is good enough.

---

## 2. Architecture

### Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `core/` | Rendering engine, case definitions, image processing, configuration |
| `ui/` | PyQt6 GUI: windows, dialogs, widgets, background workers, themes |
| `api/` | External cover art API clients (ScreenScraper, TheGamesDB, libretro) |
| `resources/` | Static assets: icons, platform colors JSON, logos |
| `tests/` | Unit tests using `unittest` |

### Dependency Flow

```
main.py
  -> core/config.py         (configuration)
  -> ui/main_window.py       (GUI)
       -> ui/themes.py       (theme system)
       -> ui/preview_widget.py
       -> ui/workers.py      (background threads)
       -> ui/settings_dialog.py
       -> ui/search_dialog.py
       -> ui/animation_dialog.py
       -> core/renderer.py   (rendering engine)
            -> core/case_types.py
            -> core/image_utils.py
            -> core/spine_generator.py
            -> core/case_texture.py
       -> api/screenscraper.py
       -> api/thegamesdb.py
       -> api/libretro.py
```

### Threading Model

All heavy work runs in `QThread` subclasses. The main thread is **never blocked**
by rendering, batch processing, animation export, or network requests. The one
exception is shutdown: `closeEvent` waits, bounded, for a running worker to
notice its interruption request (see § 12).

`BatchWorker` additionally fans out across a `ProcessPoolExecutor` (spawn
context), falling back to sequential rendering if the pool cannot start.

Every worker declares `error(str)`.

| Worker | Purpose | Signals |
|--------|---------|---------|
| `RenderWorker` | Single 3D render | `rendered(Image)`, `error(str)` |
| `BatchWorker` | Multi-file processing | `progress(int,int,str)`, `finished_signal(int)`, `error(str)` |
| `AnimationWorker` | Multi-angle animation | `progress(int,int)`, `finished_signal(str)`, `error(str)` |
| `SearchWorker` | API game search | `results_ready(list,int)`, `finished_signal()`, `error(str)` |
| `PreviewWorker` | Thumbnail download | `preview_ready(Image,int)`, `error(str)` |
| `DownloadWorker` | Full image download | `image_ready(Image,Image)`, `error(str)` |

---

## 3. Code Style

### Language & Formatting

- **Python 3.12+** type annotations throughout (use `X | None`, not `Optional[X]`)
- **PEP 8** naming: `snake_case` for functions/variables, `PascalCase` for classes
- **4-space indentation**, no tabs
- **Max line length**: 100 characters (soft), 120 characters (hard)
- **Imports**: stdlib first, then third-party, then local; grouped with blank lines
- **Docstrings**: Required on all public classes and functions; `"""One-liner."""`
  or multi-line with summary, blank line, details
- **No star imports**: Always use explicit `from module import Name1, Name2`

### Private Conventions

- Private methods/attributes prefixed with `_` (single underscore)
- UI signal handlers named `_on_<event>()` (e.g., `_on_rendered`, `_on_batch_progress`)
- UI action methods named `_<verb>_<noun>()` (e.g., `_load_front`, `_export_png`)
- Builder methods named `_build_<component>()` (e.g., `_build_left_panel`)

### Error Handling

- Workers catch `Exception` broadly and emit `error(str)` signals
- UI layer shows `QMessageBox.warning()` for user-facing errors
- Status bar displays transient status messages
- File operations wrapped in try/except with user notification
- Never silently swallow exceptions in user-facing code paths

---

## 4. Rendering Standards

### Physical Dimensions

All case measurements are in **real-world millimeters**, stored in `CaseType` dataclass:

```python
@dataclass(frozen=True)
class CaseType:
    name: str
    width: float    # front face width (mm)
    height: float   # front face height (mm)
    depth: float    # spine thickness (mm)
    platforms: tuple[str, ...]
```

### Output Specifications

| Target | Width | Format | Transparency |
|--------|-------|--------|-------------|
| RetroArch thumbnails | max 512px | PNG | RGBA where present |
| LaunchBox 3D boxart | 800-1200px | PNG | RGBA where present |
| Animation (APNG) | configurable | APNG | RGBA where present |
| Animation (GIF) | configurable | GIF | No (solid bg) |

"RGBA where present" is exact: a render whose alpha is fully opaque --
which is every render on a White or Black background -- is written as RGB.
Section 11 optimisation 3 does this, and an opaque alpha channel is a
quarter of the file spent on nothing.

Output width is bounded. `MAX_OUTPUT_WIDTH` in `core/renderer.py` is the hard
ceiling: `BoxRenderer` clamps a larger `output_width` down to it, and the
width control offers nothing above it. The animation targets above are
configurable within that bound, not unbounded.

### Rendering Pipeline

1. **Input validation** - Check front image exists
2. **Full cover detection** - Compare aspect ratio to `(2*width + depth) / height`
3. **Cover splitting** - If full cover: geometric + image-analysis spine detection
4. **Spine generation** - Platform-branded text with title, serial, colour
5. **Texture overlay** - Procedural case-type-specific emboss/deboss details
6. **Shading** - Uniform + directional gradient, applied after texture
7. **Perspective transform** - OpenCV `warpPerspective` where cv2 is present;
   PIL `PERSPECTIVE` with coefficient solving is the fallback
8. **Face compositing** - Front, spine, top, bottom faces onto canvas
9. **Edge highlights** - Subtle light/dark edge lines for depth
10. **Effects** - Shadow (optional), reflection (optional)
11. **Background** - Transparent, white, or black
12. **Downscale** - 2x supersampled to final resolution via LANCZOS

### Anti-Aliasing

- **2x supersampling** is the standard: render at 2x output width, then
  `Image.LANCZOS` downscale
- Replicate-edge padding prevents bleed at perspective edges:
  `cv2.copyMakeBorder(..., BORDER_REPLICATE)`, or `np.pad(mode='edge')` on the
  PIL fallback
- Canvas size must be consistent across all `_perspective_quad` calls and
  `alpha_composite` operations within a single render

### Viewing Angle

- Default: **30 degrees** (LaunchBox convention)
- User-adjustable: 5-60 degrees
- Angle affects perspective foreshortening of front face and spine visibility

---

## 5. Spine Detection

Full cover images (back + spine + front in one scan) use a two-stage detection:

### Stage 1: Geometric Estimation
Calculate expected spine position from case dimensions and image width.

### Stage 2: Image Analysis Refinement
- Sample **16 horizontal bands** across the image height
- Measure colour discontinuity at candidate spine boundaries
- Use **30th percentile** of band scores for robustness against noise
- Independently nudge left/right boundaries up to **15% of the expected
  spine width, clamped to 8-30 pixels**. The clamp is deliberate and is
  the reason the effective percentage varies with scan size: it keeps the
  search window usable on a small scan, where 15% is a couple of pixels,
  and bounded on a large one, where it would otherwise be wide enough to
  find a false edge
- Only accept nudge if improvement exceeds **20%** over geometric baseline
- Validate final spine width stays within **85-115%** of expected width
- Fall back to geometric on failure

### Manual Override
Users can fine-tune spine boundaries with +/- pixel offset sliders.
Three-panel split preview (back | spine | front) provides visual feedback.

---

## 6. UI Standards

### Theme System

The application uses a centralized theme system (`ui/themes.py`):

- Themes are defined as `Theme` dataclasses with named colour slots
- A single `generate_stylesheet()` function produces complete QSS from a theme
- Inline widget styles use theme colours via `get_active_theme()` for consistency
- Theme selection persisted in config under `ui.theme`
- Theme changes apply immediately without restart

### Colour Slot Naming

| Slot | Purpose |
|------|---------|
| `bg_darkest` | Main window / base background |
| `bg_dark` | Input fields, menus, secondary panels |
| `bg_mid` | Buttons, interactive elements |
| `bg_light` | Hover states |
| `bg_pressed` | Pressed/active states |
| `bg_preview` | Preview area background |
| `border` | Standard border colour |
| `border_accent` | Highlighted borders (e.g., spine preview) |
| `text_primary` | Main text |
| `text_secondary` | Secondary / label text |
| `text_dim` | Disabled / hint text |
| `accent` | Primary accent (selection, progress, handles) |
| `accent_dark` | Darker accent variant (status bar) |
| `accent_hover` | Accent on hover |
| `accent_text` | Text displayed on accent backgrounds |

### Widget Standards

- **All thumbnails**: Dark background (`bg_preview`), 1px solid border
- **Action buttons**: Bold text for primary actions (Generate)
- **Disabled elements**: Dimmed text (`text_dim`), no interaction feedback
- **Status bar**: Accent background with `accent_text`. Each theme picks its
  own `accent_text` for contrast against its own accent -- a light accent
  takes dark text, a darker one takes white. A new theme makes that choice
  rather than copying another theme's
- **Progress bar**: Accent-coloured fill, bordered frame
- **Busy overlay**: Semi-transparent dark scrim with animated spinner

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Open Front Cover | Ctrl+O |
| Open Back Cover | Ctrl+Shift+O |
| Export PNG | Ctrl+E |
| Export Animation | Ctrl+Shift+A |
| Batch Process | Ctrl+B |
| Generate | Ctrl+G / F5 |
| Copy to Clipboard | Ctrl+Shift+C |
| Toggle Comparison | Ctrl+D |
| Search Online | Ctrl+F |
| Quit | Ctrl+Q |

### Layout Structure

- **Left panel** (~280px): Image loading, spine config, case settings, action buttons
- **Right panel** (flex): Preview display with controls below
- **QSplitter** between panels for user resizing
- **QStackedWidget** for single preview / comparison toggle
- **Progress bar**: Hidden by default, shown during batch/animation operations

---

## 7. Configuration

### Storage

- **Path**: `~/.config/slipcase/config.json`
- **Permissions**: `chmod 600` (contains API credentials)
- **Format**: JSON with nested sections

### Schema

```
api/
  screenscraper/{username, password, devid, devpassword}
  thegamesdb/{api_key}
rendering/
  {angle, output_width, background, reflection, shadow, texture, supersample,
   compress_level}
ui/
  {last_platform, last_case_type, last_image_directory, window_geometry,
   recent_files, theme, auto_filename, last_export_directory}
```

### Persistence Rules

- Save on: window close, settings dialog OK, recent file added, image or
  export directory changed
- Load on: application start (merged with defaults)
- Deep merge: saved values override defaults; missing keys get default values
- Recent files: max 10 entries, most-recent-first, stale entries removed on access

---

## 8. API Integration

### Rate Limiting

All API clients extend `APIClient` base class with configurable `min_request_interval`
(default 1.0 second between requests). Rate limiting is enforced transparently.

### Client Configuration

| API | Auth Required | Credentials |
|-----|--------------|-------------|
| ScreenScraper | Yes (dev + user) | devid, devpassword, username, password |
| TheGamesDB | Yes (API key) | api_key |
| libretro | No | None (direct URL access) |

### Search Strategy

Online search queries each configured source in turn, inside one worker thread:
1. ScreenScraper (if configured) - up to 10 results
2. TheGamesDB (if configured) - up to 10 results
3. libretro (only where the platform appears in `LIBRETRO_SYSTEMS`) -
   direct name lookup. Platforms absent from that map never reach it;
   SLIP-0038 covers what a user is shown when every source is skipped.

Results are aggregated and displayed with source attribution.

---

## 9. Testing Standards

### Framework

- Tests are written as `unittest.TestCase` subclasses (stdlib).
- **pytest is the gate** -- pinned in `requirements-dev.txt` and run by
  `scripts/local-ci.sh`. `python3 -m unittest discover -s tests` runs the same
  suite, but a bare `def test_x()` is invisible to it, so write `TestCase`
  methods rather than bare functions.

### Test Organization

| File | Coverage Area |
|------|--------------|
| `test_renderer.py` | Case definitions, image utils, spine generation, end-to-end rendering, config |
| `test_regressions.py` | Locked fixes: aspect ratio, batch output paths, config durability, PNG export, export naming, render bounds |
| `test_security.py` | URL allowlist, redirect validation, credential scrubbing, download limits and deadline, accepted formats, TLS |
| `test_libretro.py` | libretro URL candidates and download short-circuit |
| `test_search_worker.py` | Search worker always finishes; source counting; frame totals |

### Test Utilities

- `TestImageUtils._make_test_image()` and `TestRenderer._make_cover()` are
  private helpers on those classes in `test_renderer.py`, not a shared module.
  A new test file defines its own.
- Tests use `tempfile` for filesystem operations

### Expectations

- All tests must pass before any commit
- New rendering features require corresponding test cases
- Test images are programmatically generated (no external fixtures)
- Keep the suite fast enough to run before every commit: no network, no sleeps

### Running Tests

```bash
python3 -m pytest tests/ -v
```

---

## 10. Security Standards

All security measures are **mandatory** and must be preserved in any code changes.

### Image Downloads
- **Domain allowlist**: `api/base.py` defines `ALLOWED_IMAGE_DOMAINS`, and
  `_is_allowed_url` gates **every** request -- JSON API calls as well as image
  downloads. It is re-checked on each redirect hop, so a 302 cannot move the
  fetch to another host or drop TLS. The constant's name is historical. New
  domains require explicit addition.
- **Decoder surface**: `_ALLOWED_IMAGE_FORMATS` limits decoding to PNG, JPEG
  and WEBP. Every accepted format is one more Pillow decoder reachable from a
  remote response, so adding one back is a deliberate decision.
- **Size limit**: `MAX_DOWNLOAD_BYTES = 50MB` — responses exceeding this are rejected before loading into memory.
- **TLS enforcement**: All API requests use `verify=True`. Never disable certificate verification.

### Credential Protection
- **Scrubbing**: `_sanitize_message()` strips credential values from error messages and URLs before display or logging. Pattern: `(devpassword|devid|sspassword|ssid|apikey|api_key|password)=***`
- **Config permissions**: Config directory `~/.config/slipcase/` created with `0o700`; config file saved with `chmod 600`.
- **No logging of secrets**: Never print, log, or emit API keys or passwords in status bar or error dialogs.

### Input Safety
- **Decompression bomb protection**: `MAX_IMAGE_PIXELS` is defined in
  `api/base.py` and applied there at import, so the download path is protected
  even when `main.py` never ran -- a test, a spawned batch child, library use.
  `main.py` imports the value rather than repeating it. Pillow only *warns* at
  this value and raises above 2x it, so `download_image()` also checks
  `width * height` before decoding.
- **No code execution**: User-provided text (titles, serials, filenames) is only rendered as image text via PIL, never passed to `eval`, `exec`, `subprocess`, or shell commands.
- **File dialogs**: Filter by image extensions to prevent accidental loading of non-image files.
- **Network**: HTTPS only. `timeout=(10, 30)` bounds the connect and each
  read; it does **not** bound the total, so `MAX_DOWNLOAD_SECONDS` caps one
  download's wall clock. A slow trickle needs both. Rate limiting via
  `APIClient._rate_limit()`.

---

## 11. Performance Standards

All optimisations listed here are **mandatory** and must be preserved in any code changes.

### PNG Export (`save_optimized_png`)
Used for every single-image PNG save (export, batch). The animated-export path
is exempt: a multi-frame APNG/GIF cannot route through a single-image saver.
Applies three imperceptible optimisations, plus compression:
1. **LSB strip**: `arr[:, :, :3] &= 0xFE` — zeroes lowest bit of RGB (~15% smaller)
2. **Alpha quantization**: Semi-transparent alpha rounded to multiples of 4 (preserves 0 and 255 exactly)
3. **RGB conversion**: Drops alpha channel when all pixels are fully opaque (~15% smaller)
4. **Compression**: zlib level from the `rendering.compress_level` config key.
   Default 6 (balances speed and size); 9 is ~5% smaller and 2-4x slower.

### Rendering Engine
- **No intermediate canvas in `_perspective_quad`**: Transform padded source directly to canvas-sized output, transparent outside the quad (`borderValue` under OpenCV, `fillcolor` under PIL). Never allocate an intermediate `src_canvas`.
- **Shadow blur on alpha only**: `generate_shadow()` works with `L` mode alpha channel, not full RGBA. ~4x faster Gaussian blur.
- **Combined top/bottom faces**: `_render_faces()` draws both faces on a single canvas (one `alpha_composite` instead of two).
- **Vectorized shading**: NumPy `np.linspace` with `np.newaxis` + `np.broadcast_to` for gradient overlays, not pixel-by-pixel loops. Broadcasting is deliberate over `np.tile`: it never materialises the repeated array.
- **Edge padding**: replicate-edge padding before the perspective transform -- `cv2.copyMakeBorder(..., BORDER_REPLICATE)`, or `np.pad(mode='edge')` on the PIL fallback.

### General
- Prefer in-place list operations over building separate lists (e.g., AnimationWorker normalises frames in-place).
- Use binary search for font size fitting (`_fit_text` in spine_generator).
- Cache font paths (`_font_path_cache` in spine_generator).

---

## 12. Memory Management Standards

All memory patterns listed here are **mandatory** and must be followed in any code changes.

### Renderer (`core/renderer.py`)
- **`del` large intermediates** immediately after their last use in `render()`:
  `front_tex`, `spine_tex`, `spine`, `front`, `spine_shaded`, `front_shaded`,
  `spine_dst`, `front_dst`, `faces`, `shadow`, `shadow_canvas`, `reflection`,
  `refl_canvas`, `bg`.
- **`_render_shadow`** returns cropped shadow directly — no extra canvas-sized allocation.

### Workers (`ui/workers.py`)
- **AnimationWorker**: Normalise frames in-place (`frames[i] = canvas`). Convert GIF frames in-place. Never create separate `normalized` or `rgb_frames` lists. `del frames` after save.
- **BatchWorker**: `img.load()` after `Image.open()`. `del img` after render. `del result` after save. Never accumulate images across loop iterations.

### QThread Lifecycle
- **All workers** must connect `finished.connect(worker.deleteLater)` at creation time.
- **`closeEvent`** must ask running workers to stop, wait for them, and clear all image references.
  Use `worker.requestInterruption()` and check `isInterruptionRequested()` in
  each worker's loop. **`quit()` alone does nothing here**: every worker
  overrides `run()` without calling `exec()`, so there is no event loop for
  `quit()` to reach and `wait()` would simply time out.
- **Never clear a worker reference while its thread is still running.**
  Dropping the last Python reference to a parentless live `QThread` destroys
  the C++ object mid-run and aborts the process. If `wait()` times out, keep
  the reference.

### File Handles
- Always call `img.load()` after `Image.open(path)` to read data into memory and release the file handle. PIL keeps file handles open for lazy loading otherwise.

### API Sessions
- API clients (`APIClient`) create `requests.Session` objects with connection pools.
- Worker threads must close API clients in `finally` blocks: `client.close()`.

### Caches and References
- `SearchDialog._preview_cache` and `_results` must be cleared on dialog close (both accept and reject paths).
- `PreviewWidget.clear_image()` sets both `_rendered_image` and `_source_pixmap` to `None`.
- `MainWindow.closeEvent` clears `_front_image`, `_back_image`, and all preview widgets.

---

## 13. File Naming

| Type | Convention | Example |
|------|-----------|---------|
| Python modules | `snake_case.py` | `case_types.py` |
| Test files | `test_<module>.py` | `test_renderer.py` |
| Config files | `lowercase.json` | `config.json` |
| Resource files | `snake_case.ext` | `case_colors.json` |
| Icons | `icon_<size>.png` | `icon_128.png` |

---

## 14. Dependencies

Runtime dependencies and their minimum versions are in `requirements.txt`.
`requirements.lock` pins exact versions, transitive ones included, for CI, and
`requirements-dev.txt` pins the tools the gate runs.

| Package | Purpose |
|---------|---------|
| PyQt6 >= 6.6 | GUI framework |
| Pillow >= 12.1.1 | Image processing and rendering |
| numpy >= 1.26 | Vectorized image operations |
| requests >= 2.31 | HTTP client for API access |
| opencv-python-headless >= 4.9 | Image processing support |
| scipy >= 1.12 | Image analysis (ndimage for spine detection) |

No additional runtime dependencies. No build system required beyond pip.

---

## Cold-eyes loop log

Rows are written by `review-contract`, one per loop. Columns are that skill's
four questions; Q4 is not asked of a standard.

| Loop | Date | Lanes | Q1 | Q2 | Q3 | Q4 | Outcome |
|------|------|-------|----|----|----|----|---------|
| 1 | 2026-09-03 | 3, cold — genre pinned `standard` | 9 | 3 | 2 | n/a | **14 verified, 14 fixed; 2 dismissed as true-but-immaterial.** First gate on this document (SLIP-0081), armed by the § 12 `closeEvent` rewrite — and **§ 12 verified clean**, so the trigger section was the one thing that held. **All three lanes independently found the same five**, the strongest signal in the run: `MAX_IMAGE_PIXELS` attributed to `main.py` when `api/base.py` is the sole definition *and* applies it (a conformer could delete the only copy protecting a test or a spawned batch child); "30-second timeout" where the code is a per-read bound plus a 60s wall clock, with `MAX_DOWNLOAD_SECONDS` unmentioned (deleting the deadline check restores SLIP-0065); the allowlist described as image-only when `_is_allowed_url` gates every request and re-checks each redirect hop (SLIP-0064); "all PNG saves … animation" against `CLAUDE.md`'s animation exemption, both marked mandatory; and `results_ready(list)` against `pyqtSignal(list, int)`. **Three findings came from the orchestrator rather than a lane** — two lanes raised them as open questions the packet could not settle: seven themes ship and five use white `accent_text`, so "dark in both themes" was false (it was introduced by SLIP-0075, whose author checked two); search is strictly sequential, not "in parallel", which closes SLIP-0045; and `Pillow >= 12.0` against `requirements.txt`'s `12.1.1`. **Two Q3s**: § 4 stated no output-width ceiling though the renderer bounds it and cites § 4 as its authority, and `_ALLOWED_IMAGE_FORMATS` (SLIP-0066) was recorded in no document, so a conformer could widen the decoder surface without breaching anything. **4a step 3's refute case caught a false claim in one of this run's own fixes** — "a wider request is refused" when `BoxRenderer` clamps; the project's own `test_a_width_past_the_ceiling_is_clamped` settles it. Collateral fixed in `CLAUDE.md`: a stale test count, and the same `np.pad` claim § 11 carried. This section did not exist before this run; the skeleton requires it. |
