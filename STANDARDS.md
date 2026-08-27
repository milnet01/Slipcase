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
by rendering, batch processing, animation export, or network requests.

| Worker | Purpose | Signals |
|--------|---------|---------|
| `RenderWorker` | Single 3D render | `rendered(Image)`, `error(str)` |
| `BatchWorker` | Multi-file processing | `progress(int,int,str)`, `finished_signal(int)` |
| `AnimationWorker` | Multi-angle animation | `progress(int,int)`, `finished_signal(str)` |
| `SearchWorker` | API game search | `results_ready(list)`, `finished_signal()` |
| `PreviewWorker` | Thumbnail download | `preview_ready(Image,int)` |
| `DownloadWorker` | Full image download | `image_ready(Image,Image)` |

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
| RetroArch thumbnails | max 512px | PNG | Yes (RGBA) |
| LaunchBox 3D boxart | 800-1200px | PNG | Yes (RGBA) |
| Animation (APNG) | configurable | APNG | Yes (RGBA) |
| Animation (GIF) | configurable | GIF | No (solid bg) |

### Rendering Pipeline

1. **Input validation** - Check front image exists
2. **Full cover detection** - Compare aspect ratio to `(2*width + depth) / height`
3. **Cover splitting** - If full cover: geometric + image-analysis spine detection
4. **Spine generation** - Platform-branded text with title, serial, colour
5. **Texture overlay** - Procedural case-type-specific emboss/deboss details
6. **Shading** - Uniform + directional gradient, applied after texture
7. **Perspective transform** - PIL `PERSPECTIVE` with coefficient solving
8. **Face compositing** - Front, spine, top, bottom faces onto canvas
9. **Edge highlights** - Subtle light/dark edge lines for depth
10. **Effects** - Shadow (optional), reflection (optional)
11. **Background** - Transparent, white, or black
12. **Downscale** - 2x supersampled to final resolution via LANCZOS

### Anti-Aliasing

- **2x supersampling** is the standard: render at 2x output width, then
  `Image.LANCZOS` downscale
- Edge padding with `np.pad(mode='edge')` prevents bleed at perspective edges
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
- Independently nudge left/right boundaries up to **15% of spine width**
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
- **Status bar**: Accent background with white text for visibility
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
  {angle, output_width, background, reflection, shadow, texture, supersample}
ui/
  {last_platform, last_case_type, last_image_directory, window_geometry,
   recent_files, theme}
```

### Persistence Rules

- Save on: window close, settings dialog OK, recent file added, image directory changed
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

Online search queries all configured APIs in parallel (within a single worker thread):
1. ScreenScraper (if configured) - up to 10 results
2. TheGamesDB (if configured) - up to 10 results
3. libretro (always) - direct name lookup

Results are aggregated and displayed with source attribution.

---

## 9. Testing Standards

### Framework

- **unittest** (stdlib) - no external test runner required
- Run: `python3 -m unittest discover -s tests`

### Test Organization

| Test Class | Coverage Area |
|-----------|--------------|
| `TestCaseTypes` | Case definitions, platform mapping, dimensions |
| `TestImageUtils` | Edge colour extraction, reflection, shading |
| `TestSpineGenerator` | Spine text rendering, platform branding |
| `TestRenderer` | End-to-end rendering, effects, all case types |
| `TestConfig` | Configuration defaults, persistence, get/set |

### Test Utilities

- `_make_test_image(w, h, color)` - Generates solid RGBA test images
- `_make_cover()` - Standard 400x560 RGBA test cover
- Tests use `tempfile` for filesystem operations

### Expectations

- All tests must pass before any commit
- New rendering features require corresponding test cases
- Test images are programmatically generated (no external fixtures)
- Tests must complete in under 5 seconds total

### Running Tests

```bash
python3 -m pytest tests/ -v
```

---

## 10. Security Standards

All security measures are **mandatory** and must be preserved in any code changes.

### Image Downloads
- **Domain allowlist**: `api/base.py` defines `ALLOWED_IMAGE_DOMAINS` — only URLs matching these domains (or subdomains) are downloaded. New domains require explicit addition.
- **Size limit**: `MAX_DOWNLOAD_BYTES = 50MB` — responses exceeding this are rejected before loading into memory.
- **TLS enforcement**: All API requests use `verify=True`. Never disable certificate verification.

### Credential Protection
- **Scrubbing**: `_sanitize_message()` strips credential values from error messages and URLs before display or logging. Pattern: `(devpassword|devid|sspassword|ssid|apikey|api_key|password)=***`
- **Config permissions**: Config directory `~/.config/slipcase/` created with `0o700`; config file saved with `chmod 600`.
- **No logging of secrets**: Never print, log, or emit API keys or passwords in status bar or error dialogs.

### Input Safety
- **Decompression bomb protection**: `Image.MAX_IMAGE_PIXELS = 178_956_970` set in `main.py`
- **No code execution**: User-provided text (titles, serials, filenames) is only rendered as image text via PIL, never passed to `eval`, `exec`, `subprocess`, or shell commands.
- **File dialogs**: Filter by image extensions to prevent accidental loading of non-image files.
- **Network**: HTTPS only; 30-second timeout; rate limiting via `APIClient._rate_limit()`

---

## 11. Performance Standards

All optimisations listed here are **mandatory** and must be preserved in any code changes.

### PNG Export (`_save_optimized_png`)
Used for all PNG saves (single export, batch, animation). Applies three imperceptible optimisations:
1. **LSB strip**: `arr[:, :, :3] &= 0xFE` — zeroes lowest bit of RGB (~15% smaller)
2. **Alpha quantization**: Semi-transparent alpha rounded to multiples of 4 (preserves 0 and 255 exactly)
3. **RGB conversion**: Drops alpha channel when all pixels are fully opaque (~15% smaller)
4. **Max compression**: `compress_level=9` for zlib

### Rendering Engine
- **No intermediate canvas in `_perspective_quad`**: Transform padded source directly to canvas-sized output via `fillcolor=(0,0,0,0)`. Never allocate an intermediate `src_canvas`.
- **Shadow blur on alpha only**: `generate_shadow()` works with `L` mode alpha channel, not full RGBA. ~4x faster Gaussian blur.
- **Combined top/bottom faces**: `_render_faces()` draws both faces on a single canvas (one `alpha_composite` instead of two).
- **Vectorized shading**: NumPy `np.linspace` + `np.tile` for gradient overlays, not pixel-by-pixel loops.
- **Edge padding**: `np.pad(mode='edge')` for perspective transform boundary padding.

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
- **`closeEvent`** must wait for running workers (`worker.quit()` + `worker.wait(2000)`) and clear all image references.

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

All dependencies specified in `requirements.txt` with minimum versions:

| Package | Purpose |
|---------|---------|
| PyQt6 >= 6.6 | GUI framework |
| Pillow >= 12.0 | Image processing and rendering |
| numpy >= 1.26 | Vectorized image operations |
| requests >= 2.31 | HTTP client for API access |
| opencv-python-headless >= 4.9 | Image processing support |
| scipy >= 1.12 | Image analysis (ndimage for spine detection) |

No additional runtime dependencies. No build system required beyond pip.
