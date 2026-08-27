"""Generate spine images from platform templates with game title and serial number."""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


_RESOURCES = Path(__file__).parent.parent / "resources"

# Load platform colors
_CASE_COLORS: dict = {}
_colors_path = _RESOURCES / "case_colors.json"
if _colors_path.exists():
    with open(_colors_path) as f:
        _CASE_COLORS = json.load(f)


# Platform-specific branding for the spine strip.
#   "logo" - top portion of strip (e.g. PlayStation symbol representation)
#   "name" - bottom portion of strip, large (e.g. "PS4")
#   "strip_pct" - how much of spine height the branding strip takes up
PLATFORM_BRANDING: dict[str, dict] = {
    "PS1": {"logo": "PS", "name": "", "strip_pct": 0.15},
    "PS2": {"logo": "PS", "name": "PS2", "strip_pct": 0.15},
    "PS3": {"logo": "PS", "name": "PS3", "strip_pct": 0.13},
    "PS4": {"logo": "PS", "name": "PS4", "strip_pct": 0.14},
    "PS5": {"logo": "PS", "name": "PS5", "strip_pct": 0.14},
    "PSP": {"logo": "PS", "name": "PSP", "strip_pct": 0.14},
    "Vita": {"logo": "PS", "name": "VITA", "strip_pct": 0.14},
    "Xbox": {"logo": "", "name": "XBOX", "strip_pct": 0.13},
    "Xbox 360": {"logo": "XBOX", "name": "360", "strip_pct": 0.15},
    "Xbox One": {"logo": "XBOX", "name": "ONE", "strip_pct": 0.13},
    "Xbox Series X": {"logo": "XBOX", "name": "SERIES X", "strip_pct": 0.13},
    "Wii": {"logo": "", "name": "Wii", "strip_pct": 0.12},
    "Switch": {"logo": "Nintendo", "name": "SWITCH", "strip_pct": 0.15},
    "NES": {"logo": "Nintendo", "name": "NES", "strip_pct": 0.15},
    "SNES": {"logo": "Nintendo", "name": "SNES", "strip_pct": 0.15},
    "N64": {"logo": "Nintendo", "name": "64", "strip_pct": 0.15},
    "GameCube": {"logo": "Nintendo", "name": "GCN", "strip_pct": 0.15},
    "Genesis": {"logo": "SEGA", "name": "GENESIS", "strip_pct": 0.15},
    "Mega Drive": {"logo": "SEGA", "name": "MEGA DRIVE", "strip_pct": 0.15},
    "Saturn": {"logo": "SEGA", "name": "SATURN", "strip_pct": 0.15},
    "Dreamcast": {"logo": "SEGA", "name": "DREAMCAST", "strip_pct": 0.15},
    "Game Boy": {"logo": "Nintendo", "name": "GAME BOY", "strip_pct": 0.15},
    "Game Boy Color": {"logo": "Nintendo", "name": "GBC", "strip_pct": 0.15},
    "GBA": {"logo": "Nintendo", "name": "GBA", "strip_pct": 0.15},
    "DS": {"logo": "Nintendo", "name": "DS", "strip_pct": 0.15},
    "3DS": {"logo": "Nintendo", "name": "3DS", "strip_pct": 0.15},
    "PC": {"logo": "", "name": "PC", "strip_pct": 0.10},
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


_font_path_cache: dict[bool, str | None] = {}


def _get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Get a suitable font, falling back to default if needed."""
    if bold not in _font_path_cache:
        if bold:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
            ]
        else:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
            ]
        _font_path_cache[bold] = None
        for fp in candidates:
            if Path(fp).exists():
                _font_path_cache[bold] = fp
                break

    path = _font_path_cache[bold]
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _fit_text(text: str, max_width: int, max_height: int, bold: bool = True) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, int, int]:
    """Find the largest font size that fits text within bounds.

    Returns (font, text_width, text_height).
    """
    lo, hi = 6, max_height
    best_font = _get_font(6, bold=bold)
    bbox = best_font.getbbox(text)
    best_tw, best_th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    while lo <= hi:
        mid = (lo + hi) // 2
        font = _get_font(mid, bold=bold)
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        if tw <= max_width and th <= max_height:
            best_font, best_tw, best_th = font, tw, th
            lo = mid + 1
        else:
            hi = mid - 1

    return best_font, best_tw, best_th


def _render_rotated_text(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    color: tuple[int, int, int, int],
) -> Image.Image:
    """Render text and rotate 90 degrees CW (reads top-to-bottom).

    This matches the standard game case convention where you tilt your
    head to the right to read the spine.
    """
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    text_img = Image.new("RGBA", (tw + 4, th + 4), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_img)
    draw.text((-bbox[0] + 2, -bbox[1] + 2), text, fill=color, font=font)
    return text_img.rotate(-90, expand=True, resample=Image.Resampling.BICUBIC)


def _render_brand_strip(
    platform: str,
    strip_width: int,
    strip_height: int,
    brand_color: tuple[int, int, int],
    text_color: tuple[int, int, int, int],
) -> Image.Image:
    """Render the platform branding strip.

    Real game cases have a branded strip at the top of the spine with:
    - A logo/symbol at the top (e.g. PlayStation PS symbol)
    - The platform name/number below in large text (e.g. "PS4")

    The logo portion takes ~40% and the name takes ~60% of the strip.
    """
    strip = Image.new("RGBA", (strip_width, strip_height), (*brand_color, 255))
    max_thickness = int(strip_width * 0.75)

    branding = PLATFORM_BRANDING.get(platform)
    if not branding:
        # Fallback: just render the platform name
        font, _, _ = _fit_text(platform, max_width=strip_height - 4,
                               max_height=max_thickness, bold=True)
        txt_img = _render_rotated_text(platform, font, text_color)
        x = (strip_width - txt_img.width) // 2
        y = (strip_height - txt_img.height) // 2
        strip.paste(txt_img, (x, y), txt_img)
        return strip

    logo = branding["logo"]
    name = branding["name"]

    if logo and name:
        # Two-part layout: logo on top (~40%), name below (~60%)
        logo_zone = int(strip_height * 0.40)
        name_zone = strip_height - logo_zone
        gap = 1

        # Logo text (smaller, lighter)
        logo_font, _, _ = _fit_text(
            logo, max_width=logo_zone - gap * 2,
            max_height=int(max_thickness * 0.55), bold=True,
        )
        logo_img = _render_rotated_text(logo, logo_font, text_color)
        lx = (strip_width - logo_img.width) // 2
        ly = (logo_zone - logo_img.height) // 2
        strip.paste(logo_img, (lx, ly), logo_img)

        # Platform name (large, bold)
        name_font, _, _ = _fit_text(
            name, max_width=name_zone - gap * 2,
            max_height=int(max_thickness * 0.85), bold=True,
        )
        name_img = _render_rotated_text(name, name_font, text_color)
        nx = (strip_width - name_img.width) // 2
        ny = logo_zone + (name_zone - name_img.height) // 2
        strip.paste(name_img, (nx, ny), name_img)

    elif name:
        # Single element
        font, _, _ = _fit_text(
            name, max_width=strip_height - 4,
            max_height=max_thickness, bold=True,
        )
        txt_img = _render_rotated_text(name, font, text_color)
        x = (strip_width - txt_img.width) // 2
        y = (strip_height - txt_img.height) // 2
        strip.paste(txt_img, (x, y), txt_img)

    elif logo:
        font, _, _ = _fit_text(
            logo, max_width=strip_height - 4,
            max_height=max_thickness, bold=True,
        )
        txt_img = _render_rotated_text(logo, font, text_color)
        x = (strip_width - txt_img.width) // 2
        y = (strip_height - txt_img.height) // 2
        strip.paste(txt_img, (x, y), txt_img)

    return strip


def generate_spine(
    title: str,
    spine_width: int,
    spine_height: int,
    platform: str = "",
    serial: str = "",
    bg_color: tuple[int, int, int] | None = None,
    text_color: tuple[int, int, int] | None = None,
) -> Image.Image:
    """Generate a platform-templated spine image with a branding strip.

    The spine layout follows real game case conventions:
    - Platform branding color strip at top (25-35% height depending on
      platform) with logo symbol and platform name
    - Main body with the game title centered
    - Serial number at the bottom in very small text, split across lines

    Args:
        title: Game title text.
        spine_width: Width of the spine in pixels (the thin dimension).
        spine_height: Height of the spine in pixels.
        platform: Platform name for template colors/branding.
        serial: Game serial number (e.g. "SLUS-20946").
        bg_color: Override body background color. If None, uses platform template.
        text_color: Override text color. If None, uses platform accent.

    Returns:
        RGBA spine image.
    """
    # Determine colors from platform template
    platform_colors = _CASE_COLORS.get(platform, {})

    brand_color = _hex_to_rgb(platform_colors.get("brand", "#404040"))
    if bg_color is None:
        body_hex = platform_colors.get("spine", "#2B2B2B")
        body_color = _hex_to_rgb(body_hex)
    else:
        body_color = bg_color

    if text_color is None:
        accent_hex = platform_colors.get("accent")
        if accent_hex:
            text_color = _hex_to_rgb(accent_hex)
        else:
            brightness = (body_color[0] * 299 + body_color[1] * 587 + body_color[2] * 114) / 1000
            text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)

    # Auto-contrast for brand strip text
    brand_brightness = (brand_color[0] * 299 + brand_color[1] * 587 + brand_color[2] * 114) / 1000
    brand_text_color = (0, 0, 0, 255) if brand_brightness > 128 else (255, 255, 255, 255)

    text_rgba = (*text_color, 255)
    dim_rgba = (*text_color, 120)

    # Layout zones — strip size is platform-dependent
    branding = PLATFORM_BRANDING.get(platform, {})
    strip_pct = branding.get("strip_pct", 0.20)
    brand_strip_h = int(spine_height * strip_pct)
    serial_zone_h = int(spine_height * 0.08)
    pad = int(spine_height * 0.015)
    title_zone_h = spine_height - brand_strip_h - serial_zone_h - pad * 2

    max_text_thickness = int(spine_width * 0.75)

    # Create spine with body color
    spine = Image.new("RGBA", (spine_width, spine_height), (*body_color, 255))
    draw = ImageDraw.Draw(spine)

    # --- Platform branding strip at top ---
    brand_strip = _render_brand_strip(
        platform, spine_width, brand_strip_h, brand_color, brand_text_color,
    )
    spine.paste(brand_strip, (0, 0), brand_strip)

    # Separator line between brand strip and body
    body_brightness = (body_color[0] * 299 + body_color[1] * 587 + body_color[2] * 114) / 1000
    if body_brightness < 80:
        sep_color = (255, 255, 255, 35)
    else:
        sep_color = (0, 0, 0, 35)
    draw.line([(0, brand_strip_h), (spine_width, brand_strip_h)], fill=sep_color, width=1)

    # --- Game title (center of body, bold) ---
    if title:
        title_y_start = brand_strip_h + pad
        title_font, _, _ = _fit_text(
            title, max_width=title_zone_h, max_height=max_text_thickness,
            bold=True,
        )
        title_img = _render_rotated_text(title, title_font, text_rgba)
        tx = (spine_width - title_img.width) // 2
        ty = title_y_start + (title_zone_h - title_img.height) // 2
        spine.paste(title_img, (tx, ty), title_img)

    # --- Serial number (bottom, very small, split into lines) ---
    if serial:
        # Split serial into prefix and number (e.g. "PLJM-16944" -> "PLJM" "16944")
        parts = serial.replace("-", " ").split()
        if len(parts) >= 2:
            _draw_serial_lines(spine, parts, spine_width, spine_height,
                               serial_zone_h, max_text_thickness, dim_rgba)
        else:
            # Single part, render as-is
            serial_font, _, _ = _fit_text(
                serial, max_width=serial_zone_h,
                max_height=int(max_text_thickness * 0.35),
                bold=False,
            )
            serial_img = _render_rotated_text(serial, serial_font, dim_rgba)
            sx = (spine_width - serial_img.width) // 2
            sy = spine_height - serial_zone_h + (serial_zone_h - serial_img.height) // 2
            spine.paste(serial_img, (sx, sy), serial_img)

    # --- Subtle edge lines for definition ---
    edge_avg = (body_color[0] + body_color[1] + body_color[2]) / 3
    edge_alpha = 40 if edge_avg < 128 else 30
    draw.line([(0, 0), (0, spine_height)], fill=(255, 255, 255, edge_alpha), width=1)
    draw.line([(spine_width - 1, 0), (spine_width - 1, spine_height)],
              fill=(0, 0, 0, edge_alpha), width=1)

    return spine


def _draw_serial_lines(
    spine: Image.Image,
    parts: list[str],
    spine_width: int,
    spine_height: int,
    serial_zone_h: int,
    max_text_thickness: int,
    color: tuple[int, int, int, int],
) -> None:
    """Draw serial number split across multiple lines at the bottom of the spine.

    Real game cases show the serial prefix and number on separate lines
    in very small text at the bottom of the spine.
    """
    line_h = serial_zone_h // len(parts)
    max_h = int(max_text_thickness * 0.30)

    for i, part in enumerate(parts):
        font, _, _ = _fit_text(part, max_width=line_h - 1, max_height=max_h, bold=False)
        img = _render_rotated_text(part, font, color)
        x = (spine_width - img.width) // 2
        y = spine_height - serial_zone_h + i * line_h + (line_h - img.height) // 2
        spine.paste(img, (x, y), img)
