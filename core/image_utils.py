"""Image utility functions for perspective transforms, shadows, reflections, and shading."""

from __future__ import annotations

from PIL import Image, ImageFilter
import numpy as np

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

from core.case_types import CaseType


def apply_directional_shading(
    image: Image.Image,
    direction: str = "left",
    intensity: float = 0.3,
) -> Image.Image:
    """Apply gradient shading via direct pixel multiplication.

    Darkens RGB channels by a gradient factor, avoiding the overhead
    of creating a full overlay image and alpha-compositing it.

    Args:
        image: RGBA image to shade.
        direction: 'left', 'right', 'top', or 'bottom' - which side is darker.
        intensity: 0.0 (no shading) to 1.0 (full black).

    Returns:
        Shaded RGBA image.
    """
    arr = np.array(image.convert("RGBA"))
    h, w = arr.shape[:2]

    if direction == "left":
        factor = np.linspace(1.0 - intensity, 1.0, w, dtype=np.float32)
        arr[:, :, :3] = (arr[:, :, :3] * factor[np.newaxis, :, np.newaxis]).astype(np.uint8)
    elif direction == "right":
        factor = np.linspace(1.0, 1.0 - intensity, w, dtype=np.float32)
        arr[:, :, :3] = (arr[:, :, :3] * factor[np.newaxis, :, np.newaxis]).astype(np.uint8)
    elif direction == "top":
        factor = np.linspace(1.0 - intensity, 1.0, h, dtype=np.float32)
        arr[:, :, :3] = (arr[:, :, :3] * factor[:, np.newaxis, np.newaxis]).astype(np.uint8)
    elif direction == "bottom":
        factor = np.linspace(1.0, 1.0 - intensity, h, dtype=np.float32)
        arr[:, :, :3] = (arr[:, :, :3] * factor[:, np.newaxis, np.newaxis]).astype(np.uint8)

    return Image.fromarray(arr, "RGBA")


def apply_uniform_shading(image: Image.Image, intensity: float = 0.15) -> Image.Image:
    """Apply uniform darkening via direct pixel multiplication."""
    arr = np.array(image.convert("RGBA"))
    arr[:, :, :3] = (arr[:, :, :3] * (1.0 - intensity)).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def generate_shadow(
    box_mask: Image.Image,
    offset: tuple[int, int] = (8, 12),
    blur_radius: int = 15,
    opacity: float = 0.5,
) -> Image.Image:
    """Generate a drop shadow from a box silhouette.

    Args:
        box_mask: RGBA image where alpha channel defines the box shape.
        offset: (x, y) shadow offset.
        blur_radius: Gaussian blur radius for shadow softness.
        opacity: Shadow opacity (0-1).

    Returns:
        RGBA image with shadow only.
    """
    w, h = box_mask.size
    shadow_size = (w + abs(offset[0]) + blur_radius * 4,
                   h + abs(offset[1]) + blur_radius * 4)

    # Work with alpha channel only — ~4x faster blur than RGBA
    alpha_arr = np.array(box_mask.split()[3], dtype=np.float32)
    alpha_arr = (alpha_arr * opacity).clip(0, 255).astype(np.uint8)

    paste_x = blur_radius * 2 + max(0, offset[0])
    paste_y = blur_radius * 2 + max(0, offset[1])

    # Build shadow alpha on NumPy array, blur with cv2 (multi-threaded) or PIL
    shadow_arr = np.zeros((shadow_size[1], shadow_size[0]), dtype=np.uint8)
    ah, aw = alpha_arr.shape
    shadow_arr[paste_y:paste_y + ah, paste_x:paste_x + aw] = alpha_arr

    if _HAS_CV2:
        # ksize is 2r+1 and therefore always odd.
        ksize = blur_radius * 2 + 1
        # Pass sigma explicitly. With sigmaX=0 OpenCV derives sigma from the
        # kernel (~9.5 at r=30) where PIL's GaussianBlur(radius) uses the
        # radius AS sigma -- so the same render produced a visibly different
        # shadow depending on whether OpenCV was importable.
        shadow_arr = cv2.GaussianBlur(shadow_arr, (ksize, ksize), blur_radius)
    else:
        shadow_alpha = Image.fromarray(shadow_arr, "L")
        shadow_alpha = shadow_alpha.filter(ImageFilter.GaussianBlur(blur_radius))
        shadow_arr = np.array(shadow_alpha)

    # Build RGBA: black pixels with blurred alpha
    result = np.zeros((shadow_size[1], shadow_size[0], 4), dtype=np.uint8)
    result[:, :, 3] = shadow_arr
    return Image.fromarray(result, "RGBA")


def generate_reflection(
    image: Image.Image,
    height_fraction: float = 0.35,
    start_opacity: float = 0.3,
) -> Image.Image:
    """Generate a floor reflection effect.

    Args:
        image: RGBA image to reflect.
        height_fraction: How much of the image height to reflect (0-1).
        start_opacity: Starting opacity at the top of reflection.

    Returns:
        RGBA image of just the reflection.
    """
    w, h = image.size
    reflect_h = int(h * height_fraction)
    if reflect_h <= 0:
        return Image.new("RGBA", (w, 1), (0, 0, 0, 0))

    # Flip vertically, then take the TOP of the flipped image -- which is the
    # BOTTOM of the source, the edge the reflection sits under. Cropping the
    # flipped image's bottom instead returns source rows reflect_h-1..0, i.e.
    # a mirror of the top of the artwork.
    flipped = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    reflection = flipped.crop((0, 0, w, reflect_h))

    # Apply gradient alpha fade
    r, g, b, a = reflection.split()
    a_arr = np.array(a, dtype=np.float32)
    gradient = np.linspace(start_opacity, 0.0, reflect_h).reshape(-1, 1)
    gradient = np.broadcast_to(gradient, (reflect_h, w))
    a_arr = (a_arr * gradient).clip(0, 255).astype(np.uint8)
    reflection = Image.merge("RGBA", (r, g, b, Image.fromarray(a_arr, mode="L")))

    return reflection


def extract_dominant_edge_color(
    image: Image.Image,
    edge: str = "left",
    sample_width: int = 5,
) -> tuple[int, int, int]:
    """Extract the dominant color from an edge of the image.

    Args:
        image: Input image.
        edge: Which edge to sample ('left', 'right', 'top', 'bottom').
        sample_width: Number of pixels to sample from the edge.

    Returns:
        (R, G, B) tuple of the dominant color.
    """
    img = image.convert("RGB")
    w, h = img.size

    if edge == "left":
        region = img.crop((0, 0, min(sample_width, w), h))
    elif edge == "right":
        region = img.crop((max(0, w - sample_width), 0, w, h))
    elif edge == "top":
        region = img.crop((0, 0, w, min(sample_width, h)))
    elif edge == "bottom":
        region = img.crop((0, max(0, h - sample_width), w, h))
    else:
        region = img.crop((0, 0, min(sample_width, w), h))

    # Quantize to find dominant color
    small = region.resize((1, 1), Image.Resampling.LANCZOS)
    r, g, b = small.getpixel((0, 0))
    return (int(r), int(g), int(b))


def is_full_cover(image: Image.Image, case_type: CaseType, tolerance: float = 0.15) -> bool:
    """Detect whether an image is a full cover (back + spine + front) based on aspect ratio.

    A full cover has aspect ratio ~= (2*width + depth) / height.
    A front-only cover has aspect ratio ~= width / height (portrait).

    Args:
        image: Input image to test.
        case_type: Case type with real-world dimensions.
        tolerance: How much deviation from expected AR is allowed (0.15 = 15%).

    Returns:
        True if image appears to be a full cover.
    """
    img_ar = image.size[0] / image.size[1]
    full_ar = (2 * case_type.width + case_type.depth) / case_type.height
    return abs(img_ar - full_ar) / full_ar <= tolerance


def detect_spine_bounds(
    image: Image.Image, case_type: CaseType,
) -> tuple[int, int]:
    """Detect the left and right x-coordinates of the spine in a full cover.

    Uses a two-stage approach:
    1. Geometric baseline from case dimensions and image height.
    2. Image-based refinement using multi-band vertical edge analysis to
       find physical fold lines near the geometric estimate.

    Returns:
        (left_x, right_x) spine boundary positions in image coordinates.
    """
    w, h = image.size

    # Stage 1: geometric baseline
    geo_left, geo_right, spine_px = _geometric_spine_bounds(w, h, case_type)

    # Stage 2: refine using image analysis
    try:
        ref_left, ref_right = _refine_spine_bounds(
            image, geo_left, geo_right, spine_px,
        )
        return ref_left, ref_right
    except Exception:
        return geo_left, geo_right


def _geometric_spine_bounds(
    w: int, h: int, case_type: CaseType,
) -> tuple[int, int, int]:
    """Pure geometric spine detection from case dimensions.

    Returns:
        (left_x, right_x, spine_width_px)
    """
    px_per_mm = h / case_type.height
    back_px = round(case_type.width * px_per_mm)
    spine_px = round(case_type.depth * px_per_mm)
    front_px = back_px

    total_panels = back_px + spine_px + front_px
    offset = max(0, w - total_panels) // 2

    spine_left = offset + back_px
    spine_right = spine_left + spine_px

    spine_left = max(0, min(spine_left, w - 1))
    spine_right = max(spine_left + 1, min(spine_right, w))

    return spine_left, spine_right, spine_px


def _refine_spine_bounds(
    image: Image.Image,
    geo_left: int,
    geo_right: int,
    expected_sw: int,
) -> tuple[int, int]:
    """Refine spine boundaries using multi-band colour discontinuity.

    At a physical fold line the colours on the left and right sides come
    from different panels, producing a consistent colour jump across most
    of the image height.  Artwork edges, by contrast, only appear in
    specific rows.

    For each candidate boundary position near the geometric estimate, we
    measure the colour difference between thin strips on each side across
    multiple horizontal bands.  The 30th percentile across bands gives a
    robust "consistency" measure.

    Each boundary is independently nudged up to ``nudge_max`` pixels from
    the geometric estimate towards the nearest strong consistent edge.
    If no significantly stronger edge is found, the geometric position is
    kept.
    """
    arr = np.array(image.convert("RGB"), dtype=np.float32)
    h, w, _ = arr.shape

    n_bands = 16
    strip_w = max(4, min(8, expected_sw // 10))
    y_margin = int(h * 0.03)
    band_h = max(1, (h - 2 * y_margin) // n_bands)

    # Pre-compute per-band running-mean colour for each column.
    from scipy.ndimage import uniform_filter1d as uf1d
    band_means = []
    for i in range(n_bands):
        y0 = y_margin + i * band_h
        y1 = y0 + band_h
        col_mean = arr[y0:y1, :, :].mean(axis=0)  # (w, 3)
        rm = uf1d(col_mean, size=strip_w, axis=0)  # (w, 3)
        band_means.append(rm)
    band_means = np.array(band_means)  # (n_bands, w, 3)

    half = strip_w // 2

    def _boundary_scores(center: int, radius: int) -> tuple[int, np.ndarray]:
        """Return boundary score for each x in [center-radius, center+radius]."""
        lo = max(half + 1, center - radius)
        hi = min(w - half - 1, center + radius + 1)
        left_m = band_means[:, lo - half:hi - half, :]
        right_m = band_means[:, lo + half:hi + half, :]
        diffs = np.sqrt(np.sum((right_m - left_m) ** 2, axis=2))
        return lo, np.percentile(diffs, 30, axis=0)

    # Nudge each boundary independently within a small radius.
    # Only accept the nudge if the new score is significantly better (>20%).
    nudge_max = max(8, min(30, int(expected_sw * 0.15)))

    def _nudge(geo_x: int) -> int:
        lo, scores = _boundary_scores(geo_x, nudge_max)
        geo_idx = geo_x - lo
        if geo_idx < 0 or geo_idx >= len(scores):
            return geo_x
        geo_score = scores[geo_idx]
        best_idx = int(np.argmax(scores))
        best_score = scores[best_idx]
        # Only nudge if the new position is meaningfully better
        if best_score > geo_score * 1.2:
            return lo + best_idx
        return geo_x

    ref_left = _nudge(geo_left)
    ref_right = _nudge(geo_right)

    # Ensure spine width stays within 85-115% of expected
    ref_sw = ref_right - ref_left
    if ref_sw < expected_sw * 0.85 or ref_sw > expected_sw * 1.15:
        return geo_left, geo_right

    return ref_left, ref_right


def split_full_cover(
    image: Image.Image, case_type: CaseType,
    left_offset: int = 0,
    right_offset: int = 0,
) -> tuple[Image.Image, Image.Image, Image.Image]:
    """Split a full cover image into back, spine, and front portions.

    Calculates spine boundaries from the case dimensions and image analysis,
    then applies a small inward trim on the front and back crops so that
    their edges contain only their own panel content (no spine bleed).
    The spine absorbs the trimmed pixels on each side; since it is resized
    to the target width by the renderer, the extra few pixels are negligible.

    Args:
        image: Full cover image (back + spine + front, left to right).
        case_type: Case type with real-world dimensions.
        left_offset: Pixel offset for the left spine boundary (start).
            Positive moves the boundary right (wider spine, narrower back).
        right_offset: Pixel offset for the right spine boundary (end).
            Positive moves the boundary right (narrower spine, wider front).

    Returns:
        (back, spine, front) as three separate RGBA images.
    """
    w, h = image.size
    left_x, right_x = detect_spine_bounds(image, case_type)

    left_x = max(0, min(left_x + left_offset, w - 2))
    right_x = max(left_x + 1, min(right_x + right_offset, w))

    # Trim a few pixels inward on front/back so the perspective-transform
    # edge padding never samples spine content.  The spine widens slightly
    # to absorb the trimmed area (resized to target width anyway).
    trim = max(1, round(w * 0.001))
    back_end = max(0, left_x - trim)
    front_start = min(w, right_x + trim)

    back = image.crop((0, 0, back_end, h)).convert("RGBA")
    spine = image.crop((back_end, 0, front_start, h)).convert("RGBA")
    front = image.crop((front_start, 0, w, h)).convert("RGBA")

    return back, spine, front
