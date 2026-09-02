# Subsystems

The module map review tooling reads to partition this codebase. Without it a
review groups files by directory, and a directory is not a subsystem: `ui/`
holds the window, the dialogs, the theming and the background workers, which
are four concerns reviewed against four different contracts.

## Module map

- render-engine — Turns a flat cover into a 3D box: perspective transform, shading, reflection, shadow, and the PNG write. `core/renderer.py`, `core/case_texture.py`, `core/png_utils.py`
- image-analysis — Decides what an input image is and manufactures what it lacks: full-cover detection and splitting, spine location, generated spine art. `core/image_utils.py`, `core/spine_generator.py`
- case-model — The real-world measurements every render is built from, the platform-to-case mapping, and the persisted settings. `core/case_types.py`, `core/config.py`, `core/version.py`
- api-clients — Everything that talks to a third party, reviewed against the security invariants in `CLAUDE.md` and `SECURITY.md`. `api/base.py`, `api/screenscraper.py`, `api/thegamesdb.py`, `api/libretro.py`
- main-window — Menu and toolbar construction, the load-render-export flow, and the window's own state. The largest file in the project, and the one most worth splitting further when a review has the budget (SLIP-0025). `ui/main_window.py`
- workers — The QThread and process-pool workers for batch rendering, animation export and search, reviewed against the memory and cleanup rules in `CLAUDE.md`. `ui/workers.py`
- dialogs — The screens reached from the main window, and the preview surface. `ui/search_dialog.py`, `ui/settings_dialog.py`, `ui/animation_dialog.py`, `ui/preview_widget.py`
- theming — Palette definitions and stylesheet generation. `ui/themes.py`
- entry-point — Process start-up: the decompression-bomb ceiling, theme selection, and constructing the window. `main.py`

The authoritative file-to-subsystem assignment is `.indie-review/partition.json`,
which this document describes in prose. Change both together.
