"""The six faces of a game box, for the turnable 3D viewer and the box file.

build_box_model decides the faces the way BoxRenderer.render does, but keeps
them flat and unshaded: a viewer turns the box, so it applies the lighting
(SLIP-0104 § 4.2).
"""

from dataclasses import dataclass

from PIL import Image, ImageOps

from core.case_texture import generate_front_texture, generate_spine_texture
from core.case_types import CaseType
from core.image_utils import extract_dominant_edge_color, is_full_cover, split_full_cover
from core.spine_generator import generate_spine

# Longest edge of any face picture. A 1600 x 1600 noise picture saves to
# about 6.7 MB, under RetroDB's 10 MB import limit (SLIP-0104 § 4.1).
FACE_MAX_EDGE = 1600


@dataclass
class BoxModel:
    """A box's real size, its plain-face colours and its pictured faces.

    Each picture shows its face from outside the box, standing upright, as
    RGB. The spine is on the front's left as seen from the front.
    """
    case_type: CaseType
    top: tuple[int, int, int]
    bottom: tuple[int, int, int]
    edge: tuple[int, int, int]
    front: Image.Image
    spine: Image.Image
    back: Image.Image | None


def _scaled(image: Image.Image, aspect: float) -> Image.Image:
    """`image` resized to width/height `aspect`, as large as the source allows
    on both axes and no larger than FACE_MAX_EDGE, as RGBA."""
    src_w, src_h = image.size
    h = max(1, int(min(src_h, src_w / aspect, FACE_MAX_EDGE, FACE_MAX_EDGE / aspect)))
    w = max(1, min(src_w, FACE_MAX_EDGE, round(h * aspect)))
    return image.convert("RGBA").resize((w, h), Image.Resampling.LANCZOS)


def _flatten(image: Image.Image, colour: tuple[int, int, int]) -> Image.Image:
    """`image` laid on an opaque `colour`, as RGB."""
    background = Image.new("RGBA", image.size, (*colour, 255))
    return Image.alpha_composite(background, image).convert("RGB")


def build_box_model(
    front_image: Image.Image,
    back_image: Image.Image | None,
    case_type: CaseType,
    *,
    title: str,
    serial: str,
    platform: str,
    spine_color: tuple[int, int, int] | None,
    case_color: tuple[int, int, int] | None,
    spine_left_offset: int,
    spine_right_offset: int,
    full_cover: bool | None,
    show_texture: bool,
) -> BoxModel:
    """Build the faces from BoxRenderer.render's face inputs.

    A full cover is split with the same offsets render uses, and a loaded
    back cover wins over the split one. With no full cover the spine is
    generated at the front height's scale. With `show_texture` set, each face
    carries the case overlay at its own size; the back carries the front
    overlay mirrored, as render's back view lays it.
    """
    split_spine = None
    if full_cover is None:
        full_cover = is_full_cover(front_image, case_type)
    if full_cover:
        split_back, split_spine, front_image = split_full_cover(
            front_image, case_type,
            left_offset=spine_left_offset, right_offset=spine_right_offset,
        )
        if back_image is None:
            back_image = split_back

    top = case_color or extract_dominant_edge_color(front_image, edge="top")
    bottom = case_color or extract_dominant_edge_color(front_image, edge="bottom")
    edge = case_color or top

    face_aspect = case_type.width / case_type.height
    front = _scaled(front_image, face_aspect)
    back = _scaled(back_image, face_aspect) if back_image is not None else None
    if split_spine is not None:
        spine = _scaled(split_spine, case_type.depth / case_type.height)
    else:
        h = front.size[1]
        spine = generate_spine(
            title=title or "Game",
            spine_width=max(round(case_type.depth * h / case_type.height), 4),
            spine_height=h,
            platform=platform,
            serial=serial,
            bg_color=spine_color,
        ).convert("RGBA")

    if show_texture:
        front = Image.alpha_composite(
            front, generate_front_texture(case_type, *front.size))
        spine = Image.alpha_composite(
            spine, generate_spine_texture(case_type, *spine.size))
        if back is not None:
            back = Image.alpha_composite(
                back, ImageOps.mirror(generate_front_texture(case_type, *back.size)))

    return BoxModel(
        case_type=case_type, top=top, bottom=bottom, edge=edge,
        front=_flatten(front, edge),
        spine=_flatten(spine, edge),
        back=_flatten(back, edge) if back is not None else None,
    )
