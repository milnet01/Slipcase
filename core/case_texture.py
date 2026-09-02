"""Procedural case texture overlays for realistic physical case features.

Generates semi-transparent RGBA overlays that simulate embossed/debossed
details found on real game cases: DVD ridge lines, Blu-ray logo indents,
cartridge box fold lines, etc.
"""

import math

from PIL import Image, ImageDraw

from core.case_types import CaseType


def generate_front_texture(case_type: CaseType, width: int, height: int) -> Image.Image:
    """Generate a front face texture overlay for the given case type.

    Returns an RGBA image with subtle emboss/deboss features drawn as
    semi-transparent highlight/shadow pairs.
    """
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    name = case_type.name

    if name == "DVD Case":
        _draw_dvd_front(draw, width, height)
    elif name == "Blu-ray Case":
        _draw_bluray_front(draw, width, height)
    elif name in ("CD Jewel Case",):
        _draw_jewel_front(draw, width, height)
    elif name in ("NES Cartridge Box", "SNES Cartridge Box",
                   "N64 Cartridge Box", "Genesis Clamshell",
                   "Game Boy Box", "GBA Box", "Universal Cart Case"):
        _draw_cardboard_front(draw, width, height)
    elif name == "Switch Case":
        _draw_switch_front(draw, width, height)
    elif name in ("DS Case", "3DS Case"):
        _draw_ds_front(draw, width, height)
    elif name in ("PSP Case", "PS Vita Case"):
        _draw_psp_front(draw, width, height)

    return overlay


def generate_spine_texture(case_type: CaseType, width: int, height: int) -> Image.Image:
    """Generate a spine texture overlay for the given case type."""
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    name = case_type.name

    if name == "DVD Case":
        _draw_dvd_spine(draw, width, height)
    elif name == "Blu-ray Case":
        _draw_bluray_spine(draw, width, height)
    elif name in ("NES Cartridge Box", "SNES Cartridge Box",
                   "N64 Cartridge Box", "Genesis Clamshell",
                   "Game Boy Box", "GBA Box", "Universal Cart Case"):
        _draw_cardboard_spine(draw, width, height)

    return overlay


# --- DVD Case ---

def _draw_dvd_front(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    """DVD case: border indent + subtle horizontal ridges."""
    # Border indent lines (~3% from edges)
    margin_x = int(w * 0.03)
    margin_y = int(h * 0.02)
    lw = max(1, w // 200)

    # Outer indent (shadow on outside, highlight on inside)
    _draw_indent_rect(draw, margin_x, margin_y,
                      w - margin_x, h - margin_y, lw)

    # Horizontal ridges near top and bottom (DVD latch area)
    ridge_y_top = int(h * 0.06)
    ridge_y_bot = int(h * 0.94)
    for ry in (ridge_y_top, ridge_y_bot):
        _draw_hline_emboss(draw, margin_x + lw, w - margin_x - lw, ry, lw)

    # Center hub circle indent (faint)
    cx, cy = w // 2, h // 2
    r = int(min(w, h) * 0.08)
    _draw_circle_indent(draw, cx, cy, r, lw)


def _draw_dvd_spine(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    """DVD spine: vertical groove lines along edges."""
    lw = max(1, w // 10)
    # Left groove
    draw.line([(lw, 0), (lw, h)], fill=(0, 0, 0, 12), width=lw)
    draw.line([(lw + lw, 0), (lw + lw, h)], fill=(255, 255, 255, 8), width=lw)
    # Right groove
    draw.line([(w - lw * 2, 0), (w - lw * 2, h)], fill=(0, 0, 0, 12), width=lw)
    draw.line([(w - lw, 0), (w - lw, h)], fill=(255, 255, 255, 8), width=lw)


# --- Blu-ray Case ---

def _draw_bluray_front(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    """Blu-ray case: border indent + curved spine-edge groove."""
    margin_x = int(w * 0.025)
    margin_y = int(h * 0.018)
    lw = max(1, w // 200)

    _draw_indent_rect(draw, margin_x, margin_y,
                      w - margin_x, h - margin_y, lw)

    # Spine-edge curved groove (left side, slight curve inward)
    groove_x = int(w * 0.04)
    for dy in range(0, h, max(1, h // 80)):
        curve = int(math.sin(dy / h * math.pi) * w * 0.005)
        x = groove_x + curve
        draw.line([(x, dy), (x, min(dy + max(1, h // 80), h))],
                  fill=(0, 0, 0, 10), width=lw)
        draw.line([(x + lw, dy), (x + lw, min(dy + max(1, h // 80), h))],
                  fill=(255, 255, 255, 6), width=lw)

    # Top latch ridge
    ridge_y = int(h * 0.04)
    _draw_hline_emboss(draw, margin_x + lw, w - margin_x - lw, ridge_y, lw)


def _draw_bluray_spine(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    """Blu-ray spine: subtle vertical grooves."""
    lw = max(1, w // 8)
    draw.line([(lw, 0), (lw, h)], fill=(0, 0, 0, 10), width=lw)
    draw.line([(w - lw, 0), (w - lw, h)], fill=(255, 255, 255, 6), width=lw)


# --- CD Jewel Case ---

def _draw_jewel_front(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    """Jewel case: clear plastic edge and center hub."""
    lw = max(1, w // 200)
    margin = int(w * 0.02)
    _draw_indent_rect(draw, margin, margin, w - margin, h - margin, lw)

    # Center CD hub
    cx, cy = w // 2, int(h * 0.55)
    r = int(min(w, h) * 0.12)
    _draw_circle_indent(draw, cx, cy, r, lw)
    # Inner ring
    r2 = int(r * 0.4)
    _draw_circle_indent(draw, cx, cy, r2, lw)


# --- Cartridge/Cardboard boxes ---

def _draw_cardboard_front(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    """Cardboard box: fold lines.

    No texture grain: the docstring promised it and the body never drew
    it (SLIP-0080). Whether the texture set should be richer is
    SLIP-0034's question, not a silent gap here.
    """
    lw = max(1, w // 200)

    # Top fold line
    fold_y = int(h * 0.02)
    _draw_hline_emboss(draw, 0, w, fold_y, lw)

    # Bottom fold line
    fold_y2 = int(h * 0.98)
    _draw_hline_emboss(draw, 0, w, fold_y2, lw)

    # Subtle vertical fold marks at edges
    fold_x = int(w * 0.015)
    draw.line([(fold_x, 0), (fold_x, h)], fill=(0, 0, 0, 8), width=lw)
    fold_x2 = int(w * 0.985)
    draw.line([(fold_x2, 0), (fold_x2, h)], fill=(0, 0, 0, 8), width=lw)


def _draw_cardboard_spine(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    """Cardboard spine: fold crease lines."""
    lw = max(1, w // 8)
    # Fold creases along both edges
    draw.line([(0, 0), (0, h)], fill=(0, 0, 0, 15), width=lw)
    draw.line([(w - 1, 0), (w - 1, h)], fill=(0, 0, 0, 15), width=lw)


# --- Switch Case ---

def _draw_switch_front(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    """Switch case: border indent + game card slot outline."""
    margin_x = int(w * 0.025)
    margin_y = int(h * 0.02)
    lw = max(1, w // 200)

    _draw_indent_rect(draw, margin_x, margin_y,
                      w - margin_x, h - margin_y, lw)

    # Game card slot (small rectangle, upper center)
    slot_w = int(w * 0.15)
    slot_h = int(h * 0.08)
    slot_x = (w - slot_w) // 2
    slot_y = int(h * 0.08)
    _draw_indent_rect(draw, slot_x, slot_y,
                      slot_x + slot_w, slot_y + slot_h, lw)


# --- DS / 3DS Case ---

def _draw_ds_front(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    """DS/3DS case: border indent."""
    margin_x = int(w * 0.025)
    margin_y = int(h * 0.02)
    lw = max(1, w // 200)
    _draw_indent_rect(draw, margin_x, margin_y,
                      w - margin_x, h - margin_y, lw)

    # Latch ridge at top
    ridge_y = int(h * 0.05)
    _draw_hline_emboss(draw, margin_x, w - margin_x, ridge_y, lw)


# --- PSP / Vita ---

def _draw_psp_front(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    """PSP/Vita case: border indent.

    No UMD or card slot is drawn; see SLIP-0080.
    """
    margin_x = int(w * 0.03)
    margin_y = int(h * 0.02)
    lw = max(1, w // 200)
    _draw_indent_rect(draw, margin_x, margin_y,
                      w - margin_x, h - margin_y, lw)


# --- Drawing primitives ---

def _draw_indent_rect(draw: ImageDraw.ImageDraw,
                      x1: int, y1: int, x2: int, y2: int,
                      lw: int) -> None:
    """Draw a rectangular indent (shadow on top-left, highlight on bottom-right)."""
    shadow = (0, 0, 0, 18)
    highlight = (255, 255, 255, 12)
    # Top and left edges (shadow - pressed in)
    draw.line([(x1, y1), (x2, y1)], fill=shadow, width=lw)
    draw.line([(x1, y1), (x1, y2)], fill=shadow, width=lw)
    # Bottom and right edges (highlight - raised lip)
    draw.line([(x1, y2), (x2, y2)], fill=highlight, width=lw)
    draw.line([(x2, y1), (x2, y2)], fill=highlight, width=lw)


def _draw_hline_emboss(draw: ImageDraw.ImageDraw,
                       x1: int, x2: int, y: int, lw: int) -> None:
    """Draw a horizontal embossed line (shadow + highlight pair)."""
    draw.line([(x1, y), (x2, y)], fill=(0, 0, 0, 15), width=lw)
    draw.line([(x1, y + lw), (x2, y + lw)], fill=(255, 255, 255, 10), width=lw)


def _draw_circle_indent(draw: ImageDraw.ImageDraw,
                        cx: int, cy: int, r: int, lw: int) -> None:
    """Draw a circular indent (ellipse with shadow/highlight effect)."""
    # Shadow arc (upper half)
    draw.arc([(cx - r, cy - r), (cx + r, cy + r)], 180, 360,
             fill=(0, 0, 0, 12), width=lw)
    # Highlight arc (lower half)
    draw.arc([(cx - r, cy - r), (cx + r, cy + r)], 0, 180,
             fill=(255, 255, 255, 8), width=lw)
