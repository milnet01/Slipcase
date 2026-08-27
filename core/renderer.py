"""3D box rendering engine - composites front, spine, and top faces with perspective."""

import math
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image, ImageDraw

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

# Perspective projection parameters
_TOP_ANGLE_RATIO = 0.3       # Top face angle as fraction of viewing angle
_MAX_TOP_ANGLE = 8.0          # Maximum top face angle in degrees
_V_SHRINK_BASE = 0.96         # Vertical shrink base (far edge foreshortening)
_V_SHRINK_ANGLE_FACTOR = 0.12 # Additional shrink per 90 degrees of angle

# Layout spacing (multiplied by supersample scale)
_CANVAS_PAD = 20              # Horizontal/vertical canvas padding
_CANVAS_TOP_PAD = 5           # Extra top padding for face overhang
_EDGE_PAD = 6                 # Edge padding for perspective transform anti-aliasing

# Shadow parameters
_SHADOW_OFFSET = (3, 6)       # (x, y) offset before scale
_SHADOW_BLUR = 8              # Blur radius before scale
_SHADOW_OPACITY = 0.4
_SHADOW_PASTE_OFFSET = (3, 8) # Paste offset before scale

# Shading intensities
_SPINE_UNIFORM_SHADE = 0.25
_SPINE_DIRECTIONAL_SHADE = 0.15
_FRONT_DIRECTIONAL_SHADE = 0.08

# Edge highlight opacities
_HIGHLIGHT_ALPHA = 0.3
_DARK_EDGE_ALPHA = 0.15

from core.case_types import CaseType
from core.case_texture import generate_front_texture, generate_spine_texture
from core.image_utils import (
    apply_directional_shading,
    apply_uniform_shading,
    extract_dominant_edge_color,
    generate_reflection,
    generate_shadow,
    is_full_cover,
    split_full_cover,
)
from core.spine_generator import generate_spine


class BoxRenderer:
    """Renders a 3D box from cover art images using perspective projection."""

    def __init__(
        self,
        case_type: CaseType,
        angle: float = 30.0,
        output_width: int = 512,
        show_reflection: bool = True,
        show_shadow: bool = True,
        show_texture: bool = True,
        supersample: int = 2,
        background: str = "transparent",
    ):
        self.case_type = case_type
        self.angle = angle
        self.output_width = output_width
        self.show_reflection = show_reflection
        self.show_shadow = show_shadow
        self.show_texture = show_texture
        self.supersample = supersample
        self.background = background

    def render(
        self,
        front_image: Image.Image,
        back_image: Image.Image | None = None,
        title: str = "",
        serial: str = "",
        platform: str = "",
        spine_color: tuple[int, int, int] | None = None,
        case_color: tuple[int, int, int] | None = None,
        spine_left_offset: int = 0,
        spine_right_offset: int = 0,
    ) -> Image.Image:
        """Render the 3D box.

        Args:
            front_image: Front cover image (required).
            back_image: Back cover image (optional, unused in current view).
            title: Game title for spine text.
            serial: Game serial number for spine.
            platform: Platform name for spine template.
            spine_color: Override spine background color.
            case_color: Override case plastic color for top/bottom faces.
            spine_left_offset: Pixel offset for left spine boundary.
            spine_right_offset: Pixel offset for right spine boundary.

        Returns:
            RGBA image of the rendered 3D box.
        """
        scale = self.supersample
        w = self.output_width * scale

        # Compute box dimensions in pixels based on case proportions
        box_dims = self._compute_box_dimensions(w)
        front_w = box_dims["front_w"]
        front_h = box_dims["front_h"]
        spine_w = box_dims["spine_w"]

        # Detect full cover (back + spine + front) and split if needed
        extracted_spine = None
        if is_full_cover(front_image, self.case_type):
            _back, extracted_spine, front_image = split_full_cover(
                front_image, self.case_type,
                left_offset=spine_left_offset, right_offset=spine_right_offset,
            )
            if back_image is None:
                back_image = _back

        # Prepare the front face
        front = front_image.convert("RGBA").resize(
            (front_w, front_h), Image.Resampling.LANCZOS
        )

        # Use extracted spine from full cover, or generate a synthetic one
        if extracted_spine is not None:
            spine = extracted_spine.resize(
                (spine_w, front_h), Image.Resampling.LANCZOS,
            )
        else:
            spine = generate_spine(
                title=title or "Game",
                spine_width=spine_w,
                spine_height=front_h,
                platform=platform,
                serial=serial,
                bg_color=spine_color,
            )

        # Compute 3D projection points
        angle_rad = math.radians(self.angle)
        top_angle_rad = math.radians(min(self.angle * _TOP_ANGLE_RATIO, _MAX_TOP_ANGLE))

        # Foreshortening factors
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Projected widths
        proj_front_w = int(front_w * cos_a)
        proj_spine_w = int(spine_w * sin_a)
        proj_top_h = int(spine_w * math.sin(top_angle_rad) * cos_a)

        # Vertical perspective shrink for the far edge
        v_shrink = _V_SHRINK_BASE - (self.angle / 90.0) * _V_SHRINK_ANGLE_FACTOR

        # Canvas dimensions (room for top and bottom faces)
        total_w = proj_spine_w + proj_front_w + _CANVAS_PAD * scale
        total_h = front_h + proj_top_h * 2 + _CANVAS_PAD * scale
        reflection_space = front_h // 3 if self.show_reflection else 0
        canvas_h = total_h + reflection_space

        # Case texture overlay (applied before shading so it gets naturally lit)
        if self.show_texture:
            front_tex = generate_front_texture(self.case_type, front_w, front_h)
            front = Image.alpha_composite(front, front_tex)
            del front_tex
            spine_tex = generate_spine_texture(self.case_type, spine_w, front_h)
            spine = Image.alpha_composite(spine, spine_tex)
            del spine_tex

        # Shading
        spine_shaded = apply_uniform_shading(spine, intensity=_SPINE_UNIFORM_SHADE)
        del spine
        spine_shaded = apply_directional_shading(
            spine_shaded, direction="left", intensity=_SPINE_DIRECTIONAL_SHADE,
        )

        front_shaded = apply_directional_shading(
            front, direction="right", intensity=_FRONT_DIRECTIONAL_SHADE,
        )
        del front

        # Create canvas (full size including reflection space)
        canvas = Image.new("RGBA", (total_w, canvas_h), (0, 0, 0, 0))

        # Offset for shadow/reflection space
        ox = (_CANVAS_PAD // 2) * scale
        oy = proj_top_h + _CANVAS_TOP_PAD * scale

        # --- Warp spine and front in parallel (both release the GIL) ---
        far_shrink = int(front_h * (1 - v_shrink) / 2)
        spine_args = dict(
            image=spine_shaded, src_w=spine_w, src_h=front_h,
            dst_tl=(ox, oy + int(front_h * (1 - v_shrink) / 2)),
            dst_tr=(ox + proj_spine_w, oy),
            dst_br=(ox + proj_spine_w, oy + front_h),
            dst_bl=(ox, oy + front_h - int(front_h * (1 - v_shrink) / 2)),
            canvas_size=(total_w, canvas_h),
        )
        front_args = dict(
            image=front_shaded, src_w=front_w, src_h=front_h,
            dst_tl=(ox + proj_spine_w, oy),
            dst_tr=(ox + proj_spine_w + proj_front_w, oy + far_shrink),
            dst_br=(ox + proj_spine_w + proj_front_w, oy + front_h - far_shrink),
            dst_bl=(ox + proj_spine_w, oy + front_h),
            canvas_size=(total_w, canvas_h),
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            spine_future = pool.submit(self._perspective_quad, **spine_args)
            front_future = pool.submit(self._perspective_quad, **front_args)
            spine_dst = spine_future.result()
            front_dst = front_future.result()
        del spine_shaded, front_shaded

        # Composites must be sequential (layer ordering)
        canvas = Image.alpha_composite(canvas, spine_dst)
        del spine_dst
        canvas = Image.alpha_composite(canvas, front_dst)
        del front_dst

        # --- Top and bottom faces (drawn on single layer to save an allocation) ---
        if proj_top_h > 3:
            top_color = case_color or extract_dominant_edge_color(front_image, edge="top")
            bottom_color = case_color or extract_dominant_edge_color(front_image, edge="bottom")
            faces = self._render_faces(
                front_w=front_w,
                spine_w=spine_w,
                proj_front_w=proj_front_w,
                proj_spine_w=proj_spine_w,
                proj_top_h=proj_top_h,
                ox=ox, oy=oy,
                v_shrink=v_shrink,
                front_h=front_h,
                far_shrink=far_shrink,
                canvas_size=(total_w, canvas_h),
                top_color=top_color,
                bottom_color=bottom_color,
            )
            canvas = Image.alpha_composite(canvas, faces)
            del faces

        # --- Edge highlights ---
        canvas = self._add_edge_lines(canvas, ox, oy, proj_spine_w, proj_front_w,
                                       front_h, far_shrink, proj_top_h, v_shrink, scale)

        # --- Shadow ---
        if self.show_shadow:
            shadow = self._render_shadow(canvas, scale)
            shadow_canvas = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            shadow_canvas.paste(shadow, (_SHADOW_PASTE_OFFSET[0] * scale, _SHADOW_PASTE_OFFSET[1] * scale))
            del shadow
            canvas = Image.alpha_composite(shadow_canvas, canvas)
            del shadow_canvas

        # --- Reflection ---
        if self.show_reflection:
            box_bottom = oy + front_h + proj_top_h
            reflection = generate_reflection(canvas, height_fraction=0.25, start_opacity=0.25)
            refl_canvas = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            refl_canvas.paste(reflection, (0, box_bottom + 2 * scale))
            del reflection
            canvas = Image.alpha_composite(canvas, refl_canvas)
            del refl_canvas

        # --- Background ---
        if self.background != "transparent":
            bg_color = self._parse_bg_color(self.background)
            bg = Image.new("RGBA", canvas.size, bg_color)
            canvas = Image.alpha_composite(bg, canvas)
            del bg

        # Downscale from supersampled size
        final_w = self.output_width
        final_h = int(canvas.size[1] / scale)
        canvas = canvas.resize((final_w, final_h), Image.Resampling.LANCZOS)

        # Crop out excess transparency
        bbox = canvas.getbbox()
        if bbox:
            canvas = canvas.crop(bbox)

        return canvas

    def _compute_box_dimensions(self, target_width: int) -> dict:
        """Compute pixel dimensions for box faces based on case type and target width."""
        ct = self.case_type
        angle_rad = math.radians(self.angle)

        # Total visible width = front * cos(angle) + spine * sin(angle)
        total_ratio = ct.width * math.cos(angle_rad) + ct.depth * math.sin(angle_rad)
        pixels_per_mm = (target_width * 0.85) / total_ratio

        front_w = int(ct.width * pixels_per_mm)
        front_h = int(ct.height * pixels_per_mm)
        spine_w = max(int(ct.depth * pixels_per_mm), 4)

        return {"front_w": front_w, "front_h": front_h, "spine_w": spine_w}

    def _perspective_quad(
        self,
        image: Image.Image,
        src_w: int, src_h: int,
        dst_tl: tuple, dst_tr: tuple, dst_br: tuple, dst_bl: tuple,
        canvas_size: tuple[int, int],
    ) -> Image.Image:
        """Warp image into a perspective quadrilateral on a canvas.

        Uses OpenCV warpPerspective when available (multi-threaded, faster),
        falling back to PIL's transform.
        """
        pad = _EDGE_PAD
        src_points = [(pad, pad), (pad + src_w, pad),
                      (pad + src_w, pad + src_h), (pad, pad + src_h)]
        dst_points = [dst_tl, dst_tr, dst_br, dst_bl]

        if _HAS_CV2:
            img_arr = np.array(image)
            resized_arr = cv2.resize(img_arr, (src_w, src_h),
                                     interpolation=cv2.INTER_LANCZOS4)
            padded_arr = cv2.copyMakeBorder(resized_arr, pad, pad, pad, pad,
                                            cv2.BORDER_REPLICATE)
            src_pts = np.float32(src_points)
            dst_pts = np.float32(dst_points)
            M = cv2.getPerspectiveTransform(src_pts, dst_pts)
            result_arr = cv2.warpPerspective(
                padded_arr, M, canvas_size,
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0, 0),
            )
            return Image.fromarray(result_arr, "RGBA")

        # PIL fallback
        resized = image.resize((src_w, src_h), Image.Resampling.LANCZOS)
        padded = Image.fromarray(
            np.pad(np.array(resized), ((pad, pad), (pad, pad), (0, 0)), mode="edge")
        )
        coeffs = self._find_coeffs(src_points, dst_points)
        return padded.transform(
            canvas_size,
            Image.Transform.PERSPECTIVE,
            coeffs,
            Image.Resampling.BICUBIC,
            fillcolor=(0, 0, 0, 0),
        )

    @staticmethod
    def _find_coeffs(
        src_points: list[tuple],
        dst_points: list[tuple],
    ) -> list[float]:
        """Find perspective transform coefficients mapping dst -> src coordinates.

        PIL's PERSPECTIVE transform maps output pixels to input pixels,
        so we need to solve for the inverse mapping.  Only used when OpenCV
        is not available.
        """
        matrix = []
        for (dx, dy), (sx, sy) in zip(dst_points, src_points):
            matrix.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy])
            matrix.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy])

        A = np.array(matrix, dtype=np.float64)
        B = np.array([c for pt in src_points for c in pt], dtype=np.float64)
        coeffs = np.linalg.solve(A, B)
        return list(coeffs)

    def _render_faces(
        self,
        front_w: int, spine_w: int,
        proj_front_w: int, proj_spine_w: int, proj_top_h: int,
        ox: int, oy: int,
        v_shrink: float, front_h: int, far_shrink: int,
        canvas_size: tuple[int, int],
        top_color: tuple[int, int, int],
        bottom_color: tuple[int, int, int],
    ) -> Image.Image:
        """Render top and bottom faces on a single layer."""
        canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        spine_far_y_offset = int(front_h * (1 - v_shrink) / 2)

        # --- Top face ---
        tr, tg, tb = top_color
        spine_top_l = (ox, oy + spine_far_y_offset)
        spine_top_r = (ox + proj_spine_w, oy)
        front_top_r = (ox + proj_spine_w + proj_front_w, oy + far_shrink)

        draw.polygon([
            (spine_top_l[0], spine_top_l[1] - proj_top_h),
            (spine_top_r[0], spine_top_r[1] - proj_top_h),
            spine_top_r, spine_top_l,
        ], fill=(int(tr * 0.7), int(tg * 0.7), int(tb * 0.7), 200))

        draw.polygon([
            (spine_top_r[0], spine_top_r[1] - proj_top_h),
            (front_top_r[0], front_top_r[1] - proj_top_h),
            front_top_r, spine_top_r,
        ], fill=(int(tr * 0.8), int(tg * 0.8), int(tb * 0.8), 180))

        # --- Bottom face ---
        br, bg, bb = bottom_color
        spine_bot_l = (ox, oy + front_h - spine_far_y_offset)
        spine_bot_r = (ox + proj_spine_w, oy + front_h)
        front_bot_r = (ox + proj_spine_w + proj_front_w, oy + front_h - far_shrink)

        draw.polygon([
            spine_bot_l, spine_bot_r,
            (spine_bot_r[0], spine_bot_r[1] + proj_top_h),
            (spine_bot_l[0], spine_bot_l[1] + proj_top_h),
        ], fill=(int(br * 0.5), int(bg * 0.5), int(bb * 0.5), 200))

        draw.polygon([
            spine_bot_r, front_bot_r,
            (front_bot_r[0], front_bot_r[1] + proj_top_h),
            (spine_bot_r[0], spine_bot_r[1] + proj_top_h),
        ], fill=(int(br * 0.6), int(bg * 0.6), int(bb * 0.6), 180))

        return canvas

    def _add_edge_lines(
        self, canvas: Image.Image,
        ox: int, oy: int,
        proj_spine_w: int, proj_front_w: int,
        front_h: int, far_shrink: int, proj_top_h: int,
        v_shrink: float, scale: int,
    ) -> Image.Image:
        """Draw subtle edge lines for definition."""
        draw = ImageDraw.Draw(canvas)
        edge_color = (255, 255, 255, int(255 * _HIGHLIGHT_ALPHA))
        dark_edge = (0, 0, 0, int(255 * _DARK_EDGE_ALPHA))

        spine_far_y_offset = int(front_h * (1 - v_shrink) / 2)

        # Spine-front edge (vertical, top to bottom including faces)
        draw.line(
            [(ox + proj_spine_w, oy - proj_top_h),
             (ox + proj_spine_w, oy + front_h + proj_top_h)],
            fill=edge_color, width=max(1, scale),
        )

        # Front right edge (top to bottom including faces)
        draw.line(
            [(ox + proj_spine_w + proj_front_w, oy + far_shrink - proj_top_h),
             (ox + proj_spine_w + proj_front_w, oy + front_h - far_shrink + proj_top_h)],
            fill=dark_edge, width=max(1, scale),
        )

        # Bottom edge lines
        spine_bot_l = (ox, oy + front_h - spine_far_y_offset + proj_top_h)
        spine_bot_r = (ox + proj_spine_w, oy + front_h + proj_top_h)
        front_bot_r = (ox + proj_spine_w + proj_front_w, oy + front_h - far_shrink + proj_top_h)

        draw.line([spine_bot_l, spine_bot_r], fill=dark_edge, width=max(1, scale))
        draw.line([spine_bot_r, front_bot_r], fill=dark_edge, width=max(1, scale))

        return canvas

    def _render_shadow(self, canvas: Image.Image, scale: int) -> Image.Image:
        """Generate a drop shadow for the box."""
        shadow = generate_shadow(
            canvas,
            offset=(_SHADOW_OFFSET[0] * scale, _SHADOW_OFFSET[1] * scale),
            blur_radius=_SHADOW_BLUR * scale,
            opacity=_SHADOW_OPACITY,
        )
        # Crop shadow to canvas size if needed
        cw, ch = canvas.size
        sw, sh = shadow.size
        if sw > cw or sh > ch:
            shadow = shadow.crop((0, 0, min(sw, cw), min(sh, ch)))
        return shadow

    @staticmethod
    def _parse_bg_color(bg: str) -> tuple[int, int, int, int]:
        """Parse background color string."""
        bg = bg.strip().lower()
        if bg in ("transparent", "none", ""):
            return (0, 0, 0, 0)
        if bg == "white":
            return (255, 255, 255, 255)
        if bg == "black":
            return (0, 0, 0, 255)
        if bg.startswith("#") and len(bg) == 7:
            r = int(bg[1:3], 16)
            g = int(bg[3:5], 16)
            b = int(bg[5:7], 16)
            return (r, g, b, 255)
        return (0, 0, 0, 0)
