"""A jewel case's faces, built from its booklet and back card (SLIP-0106 § 4.4).

A jewel case has no wrap. The front shows the booklet beside a strip of bare
tray plastic at the hinge. The back card is folded at both ends, so its
middle is the back and its two end strips show on the case's two sides.
BoxRenderer.render and build_box_model both build their faces here, so the
still render and the box file cannot differ.
"""

import logging
from dataclasses import dataclass

from PIL import Image

from core.case_types import CaseType
from core.image_utils import _fold_band_means, _nudge, is_full_cover, split_full_cover
from core.spine_generator import generate_spine

_log = logging.getLogger(__name__)

# Most pixels per mm a face is built at. LaunchBox's 1200 px at 2x
# supersampling needs about 15.5 px/mm on a PAL case at 30 degrees.
JEWEL_PX_PER_MM_MAX = 16


@dataclass
class JewelFaces:
    """A jewel case's pictured faces, each as seen from outside, upright."""
    front: Image.Image          # RGBA, case W x H: hinge strip + booklet
    back: Image.Image | None    # RGBA, case W x H: card middle on plastic
    hinge: Image.Image          # RGBA, case D x H: the spine on the front's left
    opening: Image.Image        # RGBA, case D x H: the side opposite


def back_has_strips(image: Image.Image, case_type: CaseType) -> bool:
    """Whether a back scan is the whole card, end strips included.

    The scan's width/height is compared with the card's ratio with strips
    and without them, relatively, and the nearer wins. A 15% band, as
    is_full_cover uses, cannot tell the standard card's two ratios apart:
    they are 8.7% apart.
    """
    card_w, card_h = case_type.jewel.back_card
    with_strips = card_w / card_h
    without = (card_w - 2 * case_type.jewel.strip) / card_h
    ratio = image.width / image.height
    return abs(ratio - with_strips) / with_strips < abs(ratio - without) / without


def detect_strip_folds(image: Image.Image, case_type: CaseType) -> tuple[int, int]:
    """The x of a back card scan's two folds: the card's geometry, each fold
    then moved by the same edge search spine detection uses.

    No 85-115% width check: the folds bound the middle, not a spine.
    """
    w = image.width
    strip_px = round(w * case_type.jewel.strip / case_type.jewel.back_card[0])
    geo_left, geo_right = strip_px, w - strip_px
    try:
        band_means = _fold_band_means(image, strip_px)
        return (_nudge(band_means, geo_left, strip_px),
                _nudge(band_means, geo_right, strip_px))
    except (ValueError, IndexError) as e:
        _log.warning("fold refinement failed, using the geometric estimate: %s", e)
        return geo_left, geo_right


def split_back_card(
    image: Image.Image, case_type: CaseType,
    left_offset: int = 0, right_offset: int = 0,
    folds: tuple[int, int] | None = None,
) -> tuple[Image.Image, Image.Image, Image.Image]:
    """(left strip, middle, right strip) of a back card scan, as RGBA.

    The offsets move each fold, positive to the right. Each fold is then
    clamped to at least one pixel from either edge and from the other, so
    any scan at least 3 px wide and any offsets give three non-empty parts.
    `folds` is detect_strip_folds' result, if the caller already has it.
    """
    w, h = image.size
    left_x, right_x = folds or detect_strip_folds(image, case_type)
    left_x = max(1, min(left_x + left_offset, w - 2))
    right_x = max(left_x + 1, min(right_x + right_offset, w - 1))
    return (image.crop((0, 0, left_x, h)).convert("RGBA"),
            image.crop((left_x, 0, right_x, h)).convert("RGBA"),
            image.crop((right_x, 0, w, h)).convert("RGBA"))


def _on_plastic(image: Image.Image, size_mm: tuple[float, float],
                face_mm: tuple[float, float], p: float,
                plastic: tuple[int, int, int]) -> Image.Image:
    """`image` resized to `size_mm` and centred on a `face_mm` face of plastic."""
    face = Image.new("RGBA", (max(1, round(face_mm[0] * p)), max(1, round(face_mm[1] * p))),
                     (*plastic, 255))
    w, h = max(1, round(size_mm[0] * p)), max(1, round(size_mm[1] * p))
    face.alpha_composite(image.convert("RGBA").resize((w, h), Image.Resampling.LANCZOS),
                         ((face.width - w) // 2, (face.height - h) // 2))
    return face


def jewel_faces(
    front_image: Image.Image,
    back_image: Image.Image | None,
    case_type: CaseType,
    *,
    title: str,
    serial: str,
    platform: str,
    spine_color: tuple[int, int, int] | None,
    spine_left_offset: int,
    spine_right_offset: int,
    full_cover: bool | None,
    back_strips: bool | None,
) -> JewelFaces:
    """Build a jewel case's faces from the loaded front and back.

    `full_cover` says whether the front is a wrap (None detects it), and
    `back_strips` whether the back is the whole card (None detects it). The
    offsets move the wrap's spine bounds when the front is a wrap, and the
    back card's folds otherwise. Each face takes the first source it has:
    back from the card's middle, else the wrap's back; hinge from the card's
    right strip, else the wrap's spine, else a generated spine; opening from
    the card's left strip, else a generated spine. A scan is seen from
    behind, where the hinge is on the right, so its right strip is the hinge.
    """
    jewel = case_type.jewel
    plastic = case_type.plastic or (0, 0, 0)
    W, H, D = case_type.width, case_type.height, case_type.depth
    card_w, card_h = jewel.back_card
    middle_mm = (card_w - 2 * jewel.strip, card_h)
    strip_mm = (jewel.strip, card_h)

    wrap_back = wrap_spine = None
    booklet = front_image
    if full_cover is None:
        full_cover = is_full_cover(front_image, case_type)
    if full_cover:
        wrap_back, wrap_spine, booklet = split_full_cover(
            front_image, case_type,
            left_offset=spine_left_offset, right_offset=spine_right_offset,
        )

    booklet_w, booklet_h = jewel.booklet
    p = min(booklet.height / booklet_h, JEWEL_PX_PER_MM_MAX)

    # Front: the booklet with equal top, bottom and right margins; the strip
    # left of it is the hinge strip, bare tray seen through the lid.
    front = Image.new("RGBA", (max(1, round(W * p)), max(1, round(H * p))), (*plastic, 255))
    margin = (H - booklet_h) / 2
    front.alpha_composite(
        booklet.convert("RGBA").resize(
            (max(1, round(booklet_w * p)), max(1, round(booklet_h * p))),
            Image.Resampling.LANCZOS),
        (round((W - margin - booklet_w) * p), round(margin * p)),
    )

    left_strip = right_strip = middle = None
    if back_image is not None:
        if back_strips is None:
            back_strips = back_has_strips(back_image, case_type)
        # Three parts need three pixels.
        if back_strips and back_image.width >= 3:
            # With a wrap loaded the sliders belong to the wrap.
            offsets = (0, 0) if full_cover else (spine_left_offset, spine_right_offset)
            left_strip, middle, right_strip = split_back_card(
                back_image, case_type, left_offset=offsets[0], right_offset=offsets[1])
        else:
            middle = back_image

    def generated() -> Image.Image:
        return generate_spine(
            title=title or "Game",
            spine_width=max(round(D * p), 4),
            spine_height=front.height,
            platform=platform,
            serial=serial,
            bg_color=spine_color,
        ).convert("RGBA")

    back_src = middle if middle is not None else wrap_back
    hinge_src = right_strip if right_strip is not None else wrap_spine
    return JewelFaces(
        front=front,
        back=_on_plastic(back_src, middle_mm, (W, H), p, plastic)
        if back_src is not None else None,
        hinge=_on_plastic(hinge_src, strip_mm, (D, H), p, plastic)
        if hinge_src is not None else generated(),
        opening=_on_plastic(left_strip, strip_mm, (D, H), p, plastic)
        if left_strip is not None else generated(),
    )
