"""3D box rendering engine - composites front, spine, and top faces with perspective."""

import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import numpy as np
from PIL import Image, ImageDraw, ImageOps

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

from core.case_types import CaseType
from core.case_texture import generate_front_texture, generate_spine_texture
from core.image_utils import (
    apply_directional_shading,
    apply_uniform_shading,
    case_edge_colours,
    generate_reflection,
    generate_shadow,
    inset_in_rim,
    is_full_cover,
    split_full_cover,
    upright_spine,
)
from core.jewel import jewel_faces
from core.spine_generator import generate_spine

# Perspective projection parameters
_TOP_ANGLE_RATIO = 0.3       # Top face angle as fraction of viewing angle
_MAX_TOP_ANGLE = 8.0          # Maximum top face angle in degrees
_V_SHRINK_BASE = 0.96         # Vertical shrink base (far edge foreshortening)
_V_SHRINK_ANGLE_FACTOR = 0.12 # Additional shrink per 90 degrees of angle

# The camera behind RetroDB's 3D boxes, fitted to their silhouettes
# (SLIP-0120). ScreenScraper and ES-DE renders share it: the far edge is 0.775
# of the near edge whatever the box's width, so the distance scales with the
# width, and it is given in front widths. Top and bottom slope equally, so the
# camera is level with the box's middle and sees neither face.
RETRODB_ANGLE = 35
RETRODB_CAMERA_DISTANCE = 1.98

# Largest output width the renderer will honour. The working canvas is
# output_width * supersample wide and roughly 1.3x that tall in RGBA, with
# several layers alive at once, so 8192 reached about 1.4 GB per layer.
# Image.MAX_IMAGE_PIXELS guards decoding, not Image.new, so it never covered
# this. STANDARDS.md section 4 documents no target above 1200px (SLIP-0037).
MAX_OUTPUT_WIDTH = 2048

# Layout spacing (multiplied by supersample scale)
_CANVAS_PAD = 20              # Horizontal/vertical canvas padding
_CANVAS_TOP_PAD = 5           # Extra top padding for face overhang

# The hanging tab, judged from LaunchBox's Genesis images; a real one is
# unmeasured. Outline and slot are (across, up), each from 0 to 1.
_TAB_WIDTH_MM = 50
_TAB_HEIGHT_MM = 13
_TAB_SHADE = 0.8              # As the top face it stands on
_TAB_OUTLINE = ((0, 0), (0, 0.85), (0.02, 0.95), (0.06, 1), (0.94, 1),
                (0.98, 0.95), (1, 0.85), (1, 0))
_TAB_SLOT = ((0.2, 0.08), (0.2, 0.28), (0.24, 0.36), (0.4, 0.36), (0.44, 0.52),
             (0.56, 0.52), (0.6, 0.36), (0.76, 0.36), (0.8, 0.28), (0.8, 0.08))
_EDGE_PAD = 6                 # Edge padding for perspective transform anti-aliasing

# Shadow parameters
_SHADOW_OFFSET = (3, 6)       # (x, y) offset before scale
_SHADOW_BLUR = 8              # Blur radius before scale
_SHADOW_OPACITY = 0.4
_SHADOW_PASTE_OFFSET = (3, 8) # Paste offset before scale
# How far the shadow reaches right of and below the box, before scale: both
# offsets plus the blur's spread. The canvas keeps at least this much room on
# those sides, or the shadow is cut off square at the edge (SLIP-0032).
_SHADOW_REACH = (
    _SHADOW_OFFSET[0] + _SHADOW_PASTE_OFFSET[0] + 2 * _SHADOW_BLUR,
    _SHADOW_OFFSET[1] + _SHADOW_PASTE_OFFSET[1] + 2 * _SHADOW_BLUR,
)

# Reflection: its height as a share of the box's, and its strongest opacity.
_REFLECTION_HEIGHT = 0.25
_REFLECTION_OPACITY = 0.25

# Shading intensities
_SPINE_UNIFORM_SHADE = 0.25
_SPINE_DIRECTIONAL_SHADE = 0.15
_FRONT_DIRECTIONAL_SHADE = 0.08

# Edge highlight opacities
_HIGHLIGHT_ALPHA = 0.3
_DARK_EDGE_ALPHA = 0.15

# How far a jewel case's top and bottom are lifted toward white. Bare plastic
# drawn in the front border's own colour merged with it into one thick band
# (the user, 2026-10-21); lit edges read as separate surfaces.
_JEWEL_EDGE_LIFT = 0.3


def _camera_scales(
    width: float, depth: float, angle: float, camera_distance: float | None,
) -> tuple[float, float]:
    """How much smaller the far edges of the front and the spine look than
    the near edge. No camera distance means no perspective scaling."""
    if camera_distance is None:
        return 1.0, 1.0
    a = math.radians(angle)
    distance = camera_distance * width
    return (distance / (distance + width * math.sin(a)),
            distance / (distance + depth * math.cos(a)))


def visible_width_mm(
    case_type: CaseType, angle: float, camera_distance: float | None = None,
) -> float:
    """Front plus spine as seen from `angle` degrees, in millimetres."""
    a = math.radians(angle)
    front_scale, spine_scale = _camera_scales(
        case_type.width, case_type.depth, angle, camera_distance)
    return (case_type.width * math.cos(a) * front_scale
            + case_type.depth * math.sin(a) * spine_scale)


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
        fit_angle: float | None = None,
        camera_distance: float | None = None,
    ):
        """`fit_angle` sizes the box as it is sized at that angle rather than
        its own. An animation passes its widest angle, so every frame shares
        one scale and the box does not grow as it turns (SLIP-0105).

        `camera_distance`, in front widths, draws the box through a level,
        true perspective camera instead of the default view (SLIP-0120)."""
        self.case_type = case_type
        self.angle = angle
        self.fit_angle = angle if fit_angle is None else fit_angle
        self.camera_distance = camera_distance
        self.output_width = min(max(int(output_width), 1), MAX_OUTPUT_WIDTH)
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
        full_cover: bool | None = None,
        view: str = "front",
        back_strips: bool | None = None,
        spine_image: Image.Image | None = None,
    ) -> Image.Image:
        """Render the 3D box.

        Args:
            front_image: Front cover image (required), or a full-cover wrap.
            back_image: Back cover image, shown by the back view. A full-cover
                wrap supplies one when this is None.
            title: Game title for spine text.
            serial: Game serial number for spine.
            platform: Platform name for spine template.
            spine_color: Override spine background color.
            case_color: Override case plastic color for top/bottom faces.
            spine_left_offset: Pixel offset for left spine boundary.
            spine_right_offset: Pixel offset for right spine boundary.
            full_cover: Whether front_image is a back + spine + front wrap.
                None detects it from the aspect ratio; True or False overrules
                that, since a landscape front-only image can fall inside the
                detected band (SLIP-0051).
            view: "front" shows the front cover with the spine on its left;
                "back" shows the back cover with the spine on its right, as
                the box is seen from behind (SLIP-0033). Raises ValueError
                for "back" when there is no back cover.
            back_strips: For a jewel case, whether back_image is the whole
                back card with its end strips. None detects it.
            spine_image: A spine picture the user loaded. It wins over the
                split or generated spine, as a loaded back wins over a split
                one; one lying on its side is stood upright (upright_spine).

        Returns:
            RGBA image of the rendered 3D box.
        """
        scale = self.supersample
        w = self.output_width * scale

        # Compute box dimensions in pixels based on case proportions
        box_dims = self._compute_box_dimensions(w, self.fit_angle)
        front_w = box_dims["front_w"]
        front_h = box_dims["front_h"]
        spine_w = box_dims["spine_w"]

        # A jewel case's faces come from its booklet and back card, built
        # where build_box_model builds them too (SLIP-0106 § 4.4).
        extracted_spine = None
        jewel = self.case_type.layout == "jewel"
        if jewel:
            faces = jewel_faces(
                front_image, back_image, self.case_type,
                title=title, serial=serial, platform=platform,
                spine_color=spine_color,
                spine_left_offset=spine_left_offset,
                spine_right_offset=spine_right_offset,
                full_cover=full_cover, back_strips=back_strips,
                view_angle=self.angle,
            )
            front_image, back_image = faces.front, faces.back
            extracted_spine = faces.hinge
            del faces
        else:
            # Detect full cover (back + spine + front) and split if needed
            if full_cover is None:
                full_cover = is_full_cover(front_image, self.case_type)
            if full_cover:
                _back, extracted_spine, front_image = split_full_cover(
                    front_image, self.case_type,
                    left_offset=spine_left_offset, right_offset=spine_right_offset,
                )
                if back_image is None:
                    back_image = _back
        if spine_image is not None:
            extracted_spine = upright_spine(spine_image)

        # The back view is the front view mirrored: flip the back cover and
        # the spine, lay the box out as usual, then flip the finished box
        # back. The text reads the right way round and the spine lands on
        # the back cover's right, where it is on a real case seen from behind.
        if view not in ("front", "back"):
            raise ValueError(f"view must be 'front' or 'back', not {view!r}")
        from_behind = view == "back"
        if from_behind:
            if back_image is None:
                raise ValueError(
                    "The back view needs a back cover: load one, or use a "
                    "full-cover scan (back + spine + front)"
                )
            front_image = back_image

        if self.case_type.view_from_below:
            return self._render_from_below(
                front_image, title, serial, platform, spine_color, case_color)

        # Prepare the visible face (front cover, or back cover from behind)
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
        if from_behind:
            front = ImageOps.mirror(front)
            spine = ImageOps.mirror(spine)
        # Both views lay the opening side out on the right.
        front = inset_in_rim(front, self.case_type, case_color, opening="right")
        spine = inset_in_rim(spine, self.case_type, case_color, opening=None)

        # Compute 3D projection points
        angle_rad = math.radians(self.angle)
        top_angle_rad = math.radians(min(self.angle * _TOP_ANGLE_RATIO, _MAX_TOP_ANGLE))

        # Foreshortening factors
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Projected widths
        front_scale, spine_scale = _camera_scales(
            front_w, spine_w, self.angle, self.camera_distance)
        proj_front_w = int(front_w * cos_a * front_scale)
        proj_spine_w = int(spine_w * sin_a * spine_scale)
        # A level camera sees neither the top nor the bottom.
        proj_top_h = (0 if self.camera_distance is not None
                      else int(spine_w * math.sin(top_angle_rad) * cos_a))

        # A zero-width projection makes a destination quad with two identical
        # corners. numpy's solve then raises LinAlgError and OpenCV silently
        # produces a garbage matrix. Neither is reachable from the spinner's
        # 128px minimum, but BoxRenderer takes any width and the batch and
        # animation paths construct one directly (SLIP-0057).
        if proj_front_w < 1 or proj_spine_w < 1:
            raise ValueError(
                f"output_width {self.output_width} is too small to render "
                f"{self.case_type.name} at {self.angle} degrees: the projected "
                f"front is {proj_front_w}px and the spine {proj_spine_w}px, "
                "and both must be at least 1"
            )

        # Vertical perspective shrink for the far edge
        v_shrink = _V_SHRINK_BASE - (self.angle / 90.0) * _V_SHRINK_ANGLE_FACTOR

        # Canvas dimensions (room for top and bottom faces). The padding
        # leaves _CANVAS_PAD // 2 right of the box and _CANVAS_PAD -
        # _CANVAS_TOP_PAD below it; the shadow may need more on both sides.
        shadow_w = shadow_h = 0
        if self.show_shadow:
            shadow_w = max(0, _SHADOW_REACH[0] - _CANVAS_PAD // 2) * scale
            shadow_h = max(0, _SHADOW_REACH[1] - (_CANVAS_PAD - _CANVAS_TOP_PAD)) * scale
        total_w = proj_spine_w + proj_front_w + _CANVAS_PAD * scale + shadow_w
        # The width this canvas would have at fit_angle. The final downscale
        # fits that width, not this one, to output_width (SLIP-0105).
        fit_rad = math.radians(self.fit_angle)
        fit_front_scale, fit_spine_scale = _camera_scales(
            front_w, spine_w, self.fit_angle, self.camera_distance)
        fit_w = (total_w - proj_spine_w - proj_front_w
                 + int(front_w * math.cos(fit_rad) * fit_front_scale)
                 + int(spine_w * math.sin(fit_rad) * fit_spine_scale))
        # RetroDB's boxes have no hanging tab, so a level camera draws none.
        tab_h = (round(_TAB_HEIGHT_MM * front_h / self.case_type.height)
                 if self.case_type.hanging_tab and self.camera_distance is None else 0)
        total_h = front_h + proj_top_h * 2 + tab_h + _CANVAS_PAD * scale + shadow_h
        reflection_space = front_h // 3 if self.show_reflection else 0
        canvas_h = total_h + reflection_space

        # Case texture overlay (applied before shading so it gets naturally lit)
        if self.show_texture:
            front_tex = generate_front_texture(self.case_type, front_w, front_h,
                                               back=from_behind)
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
        oy = proj_top_h + tab_h + _CANVAS_TOP_PAD * scale

        # --- Warp spine and front in parallel (both release the GIL) ---
        # How far each far edge (the spine's left, the front's right) is
        # pulled in at top and bottom.
        far_shrink = int(front_h * (1 - v_shrink) / 2)
        spine_shrink = far_shrink
        if self.camera_distance is not None:
            far_shrink = int(front_h * (1 - front_scale) / 2)
            spine_shrink = int(front_h * (1 - spine_scale) / 2)
        spine_args = dict(
            image=spine_shaded, src_w=spine_w, src_h=front_h,
            dst_tl=(ox, oy + spine_shrink),
            dst_tr=(ox + proj_spine_w, oy),
            dst_br=(ox + proj_spine_w, oy + front_h),
            dst_bl=(ox, oy + front_h - spine_shrink),
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
        # The arg dicts hold the only other references to the two shaded
        # images, so deleting the names alone frees nothing.
        del spine_shaded, front_shaded, spine_args, front_args

        # Composites must be sequential (layer ordering)
        canvas = Image.alpha_composite(canvas, spine_dst)
        del spine_dst
        canvas = Image.alpha_composite(canvas, front_dst)
        del front_dst

        if tab_h:
            top_color, _, _ = case_edge_colours(front_image, self.case_type, case_color)
            self._draw_hanging_tab(
                canvas, top_color, tab_h,
                left=ox + proj_spine_w, width=proj_front_w,
                base_y=oy - proj_top_h, drop=far_shrink, front_h=front_h,
            )

        # --- Top and bottom faces (drawn on single layer to save an allocation) ---
        if proj_top_h > 3:
            top_color, bottom_color, _ = case_edge_colours(
                front_image, self.case_type, case_color)
            # A jewel case's top and bottom are bare tray plastic, lifted.
            if jewel:
                top_color = bottom_color = tuple(
                    round(c + (255 - c) * _JEWEL_EDGE_LIFT) for c in top_color)
            faces = self._render_faces(
                front_w=front_w,
                spine_w=spine_w,
                proj_front_w=proj_front_w,
                proj_spine_w=proj_spine_w,
                proj_top_h=proj_top_h,
                ox=ox, oy=oy,
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
                                       front_h, far_shrink, spine_shrink,
                                       proj_top_h, scale)

        # --- Back view: flip the finished box back the right way round ---
        # Before the shadow and reflection, so both still fall right and down.
        # Mirroring moves the box into the room kept right of it for the
        # shadow, so the crop slides it back by that much; what it drops on
        # the left is empty.
        if from_behind:
            canvas = ImageOps.mirror(canvas).crop(
                (shadow_w, 0, shadow_w + canvas.size[0], canvas.size[1])
            )

        # --- Shadow ---
        if self.show_shadow:
            shadow = self._render_shadow(canvas, scale)
            canvas = Image.alpha_composite(shadow, canvas)
            del shadow

        # --- Reflection ---
        if self.show_reflection:
            box_bottom = oy + front_h + proj_top_h
            # Reflect the box, not the whole canvas: the canvas carries
            # reflection_space blank rows below box_bottom, so mirroring it
            # whole would reflect empty space.
            box_region = canvas.crop((0, 0, canvas.size[0], box_bottom))
            reflection = generate_reflection(
                box_region, height_fraction=_REFLECTION_HEIGHT,
                start_opacity=_REFLECTION_OPACITY,
            )
            del box_region
            refl_canvas = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            refl_canvas.paste(reflection, (0, box_bottom + 2 * scale))
            del reflection
            if self.camera_distance is not None:
                edge_xs = [ox, ox + proj_spine_w, ox + proj_spine_w + proj_front_w]
                rises = [spine_shrink, 0, far_shrink]
                if from_behind:
                    # Where the mirroring and its crop above moved the box.
                    edge_xs = [total_w - 1 - shadow_w - x for x in reversed(edge_xs)]
                    rises.reverse()
                refl_canvas = self._lift_reflection(refl_canvas, edge_xs, rises)
            canvas = Image.alpha_composite(canvas, refl_canvas)
            del refl_canvas

        # --- Background ---
        if self.background != "transparent":
            bg_color = self._parse_bg_color(self.background)
            bg = Image.new("RGBA", canvas.size, bg_color)
            canvas = Image.alpha_composite(bg, canvas)
            del bg

        # Downscale from supersampled size.
        # Both axes MUST use the same factor. The canvas is not
        # output_width * scale wide -- _compute_box_dimensions frames the box
        # at 85% of the target -- so dividing height by `scale` while pinning
        # width to output_width stretched every render horizontally by 12-14%,
        # against the real-world millimetre proportions CaseType exists to
        # preserve. Height is derived from the width instead. At its own
        # angle fit_w is the canvas width, so final_w is output_width.
        factor = self.output_width / fit_w
        final_w = max(1, round(canvas.size[0] * factor))
        final_h = max(1, round(canvas.size[1] * factor))
        canvas = canvas.resize((final_w, final_h), Image.Resampling.LANCZOS)

        # Crop out excess transparency
        bbox = canvas.getbbox()
        if bbox:
            canvas = canvas.crop(bbox)

        return canvas

    def _render_from_below(
        self,
        face: Image.Image,
        title: str,
        serial: str,
        platform: str,
        spine_color: tuple[int, int, int] | None,
        case_color: tuple[int, int, int] | None,
    ) -> Image.Image:
        """Draw `face` with the box's long bottom edge showing beneath it.

        RetroDB's view of a landscape box is its usual camera turned a quarter
        turn, so the box is drawn standing on its end through that camera, then
        turned: the left spine becomes the bottom edge and its text reads left
        to right. No cover service supplies a bottom edge, so a generated spine
        in the cover's bottom colour stands in for it. `angle` is the tilt.

        Shadow and reflection are added after the turn, so they fall downwards.
        """
        ct = self.case_type
        if spine_color is None:
            _, spine_color, _ = case_edge_colours(face, ct, case_color)
        standing = replace(ct, width=ct.height, height=ct.width, view_from_below=False)
        distance = (RETRODB_CAMERA_DISTANCE if self.camera_distance is None
                    else self.camera_distance)
        # The standing box's height becomes the output's width. Sized from
        # fit_angle alone, so every frame of an animation shares one scale.
        standing_width = round(
            self.output_width * visible_width_mm(standing, self.fit_angle, distance)
            / ct.width)
        box = BoxRenderer(
            standing, angle=self.angle, output_width=standing_width,
            show_reflection=False, show_shadow=False,
            show_texture=self.show_texture, supersample=self.supersample,
            fit_angle=self.fit_angle, camera_distance=distance,
        ).render(
            face.transpose(Image.Transpose.ROTATE_270), title=title, serial=serial,
            platform=platform, spine_color=spine_color, case_color=case_color,
            full_cover=False,
        ).transpose(Image.Transpose.ROTATE_90)

        # The canvas, room for the shadow included, is output_width wide, as a
        # normal render's is. Nothing here scales the shadow: this is final size.
        left = _CANVAS_PAD // 2
        right = max(left, _SHADOW_REACH[0]) if self.show_shadow else left
        below = _SHADOW_REACH[1] if self.show_shadow else _CANVAS_PAD - _CANVAS_TOP_PAD
        fit_width = max(1, self.output_width - left - right)
        box = box.resize(
            (fit_width, max(1, round(box.height * fit_width / box.width))),
            Image.Resampling.LANCZOS,
        )
        # Sized from the box's width, which the tilt leaves alone: an animation
        # lines its frames up by their bottoms, so this must not vary.
        reflection_h = round(fit_width * ct.height / ct.width * _REFLECTION_HEIGHT)
        reflection_space = reflection_h * 4 // 3 if self.show_reflection else 0
        canvas = Image.new(
            "RGBA",
            (self.output_width,
             _CANVAS_TOP_PAD + box.height + below + reflection_space),
            (0, 0, 0, 0),
        )
        canvas.paste(box, (left, _CANVAS_TOP_PAD))
        if self.show_shadow:
            canvas = Image.alpha_composite(self._render_shadow(canvas, 1), canvas)
        if self.show_reflection:
            reflection = generate_reflection(
                box, height_fraction=reflection_h / box.height,
                start_opacity=_REFLECTION_OPACITY,
            )
            canvas.alpha_composite(reflection, (left, _CANVAS_TOP_PAD + box.height + 2))
            del reflection
        del box

        if self.background != "transparent":
            bg = Image.new("RGBA", canvas.size, self._parse_bg_color(self.background))
            canvas = Image.alpha_composite(bg, canvas)
            del bg
        bbox = canvas.getbbox()
        return canvas.crop(bbox) if bbox else canvas

    @staticmethod
    def _lift_reflection(
        reflection: Image.Image, edge_xs: list[int], rises: list[int],
    ) -> Image.Image:
        """Slide each column of a reflection layer up to a sloping bottom edge.

        The reflection is flipped about the box's lowest line. Where the
        bottom edge has risen above that line by `rises[i]` at `edge_xs[i]`,
        the mirrored edge sits as far below it, so the column moves twice that.
        """
        pixels = np.asarray(reflection)
        height, width = pixels.shape[:2]
        columns = np.arange(width)
        lift = np.rint(2 * np.interp(columns, edge_xs, rises)).astype(int)
        rows = np.arange(height)[:, None] + lift
        lifted = pixels[np.minimum(rows, height - 1), columns]
        lifted[rows >= height] = 0
        return Image.fromarray(lifted, "RGBA")

    def _compute_box_dimensions(self, target_width: int, angle: float) -> dict:
        """Compute pixel dimensions for box faces, fitting the box as seen at
        `angle` to the target width."""
        ct = self.case_type
        pixels_per_mm = (target_width * 0.85) / visible_width_mm(
            ct, angle, self.camera_distance)

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
            # Both call sites already pass an image of exactly this size, so
            # resizing was a full INTER_LANCZOS4 pass over ~1.3 MP for no
            # change, twice per render -- and resampling already-resized cover
            # art costs sharpness (SLIP-0043).
            if image.size != (src_w, src_h):
                img_arr = cv2.resize(img_arr, (src_w, src_h),
                                     interpolation=cv2.INTER_LANCZOS4)
            padded_arr = cv2.copyMakeBorder(img_arr, pad, pad, pad, pad,
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
        resized = image
        if image.size != (src_w, src_h):
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
        for (dx, dy), (sx, sy) in zip(dst_points, src_points, strict=True):
            matrix.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy])
            matrix.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy])

        A = np.array(matrix, dtype=np.float64)
        B = np.array([c for pt in src_points for c in pt], dtype=np.float64)
        coeffs = np.linalg.solve(A, B)
        return list(coeffs)

    def _draw_hanging_tab(
        self,
        canvas: Image.Image,
        color: tuple[int, int, int],
        tab_h: int,
        left: int, width: int,
        base_y: int, drop: int, front_h: int,
    ) -> None:
        """Draw a slotted tab, in perspective, on the top face's back edge.

        `left` and `width` are the front's projected span. The back edge falls
        by `drop` across that span, and the tab shortens with it.
        """
        share = _TAB_WIDTH_MM / self.case_type.width
        start = (1 - share) / 2

        def point(across: float, up: float) -> tuple[float, float]:
            along = start + across * share
            height = tab_h * (1 - along * 2 * drop / front_h)
            return (left + along * width, base_y + along * drop - up * height)

        draw = ImageDraw.Draw(canvas)
        shade = tuple(int(c * _TAB_SHADE) for c in color)
        draw.polygon([point(*p) for p in _TAB_OUTLINE], fill=(*shade, 255))
        # Writes clear pixels: the slot shows what is behind the box.
        draw.polygon([point(*p) for p in _TAB_SLOT], fill=(0, 0, 0, 0))

    def _render_faces(
        self,
        front_w: int, spine_w: int,
        proj_front_w: int, proj_spine_w: int, proj_top_h: int,
        ox: int, oy: int,
        front_h: int, far_shrink: int,
        canvas_size: tuple[int, int],
        top_color: tuple[int, int, int],
        bottom_color: tuple[int, int, int],
    ) -> Image.Image:
        """Render top and bottom faces on a single layer."""
        canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        # --- Top face ---
        tr, tg, tb = top_color
        spine_top_l = (ox, oy + far_shrink)
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
        spine_bot_l = (ox, oy + front_h - far_shrink)
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
        front_h: int, far_shrink: int, spine_shrink: int, proj_top_h: int,
        scale: int,
    ) -> Image.Image:
        """Draw subtle edge lines for definition."""
        draw = ImageDraw.Draw(canvas)
        edge_color = (255, 255, 255, int(255 * _HIGHLIGHT_ALPHA))
        dark_edge = (0, 0, 0, int(255 * _DARK_EDGE_ALPHA))

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

        # Bottom edge lines. They belong on the bottom face; with none to sit
        # on they would cut a see-through line across the cover, since drawing
        # replaces a pixel's alpha.
        if self.camera_distance is not None:
            return canvas
        spine_bot_l = (ox, oy + front_h - spine_shrink + proj_top_h)
        spine_bot_r = (ox + proj_spine_w, oy + front_h + proj_top_h)
        front_bot_r = (ox + proj_spine_w + proj_front_w, oy + front_h - far_shrink + proj_top_h)

        draw.line([spine_bot_l, spine_bot_r], fill=dark_edge, width=max(1, scale))
        draw.line([spine_bot_r, front_bot_r], fill=dark_edge, width=max(1, scale))

        return canvas

    def _render_shadow(self, canvas: Image.Image, scale: int) -> Image.Image:
        """Generate the box's drop shadow, aligned to and sized as the canvas.

        generate_shadow pads its image by 2 * blur_radius on each side so the
        blur has room, and places the silhouette inside that padding. Cropping
        from (0, 0) kept the padding and pushed the shadow 2 * blur further
        right and down than its offsets say (SLIP-0032), so the crop starts
        at the padding instead, less the paste offset. A crop reaching past
        the shadow's edge is filled transparent.
        """
        blur = _SHADOW_BLUR * scale
        shadow = generate_shadow(
            canvas,
            offset=(_SHADOW_OFFSET[0] * scale, _SHADOW_OFFSET[1] * scale),
            blur_radius=blur,
            opacity=_SHADOW_OPACITY,
        )
        left = 2 * blur - _SHADOW_PASTE_OFFSET[0] * scale
        top = 2 * blur - _SHADOW_PASTE_OFFSET[1] * scale
        cw, ch = canvas.size
        return shadow.crop((left, top, left + cw, top + ch))

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
            try:
                r = int(bg[1:3], 16)
                g = int(bg[3:5], 16)
                b = int(bg[5:7], 16)
            except ValueError:
                # A hand-edited config can carry '#zzzzzz'; fall through to
                # transparent rather than raising out of render().
                return (0, 0, 0, 0)
            return (r, g, b, 255)
        return (0, 0, 0, 0)
