"""A cover's region: from its file name's "(Europe)"-style tags (SLIP-0106 § 4.2),
or, when the name has none, from marks printed on its artwork (SLIP-0119)."""

import re

import cv2
import numpy as np
from PIL import Image

NTSC_U, PAL, NTSC_J = "NTSC-U", "PAL", "NTSC-J"

# Region words, compared case-blind against whole comma-separated parts of a
# parenthesised group, never as substrings: "Europa" is a title, not Europe.
_REGION_WORDS: dict[str, str] = {
    **dict.fromkeys(("usa", "us", "canada", "world"), NTSC_U),
    **dict.fromkeys((
        "europe", "eu", "uk", "germany", "france", "spain", "italy",
        "netherlands", "sweden", "scandinavia", "nordic", "denmark", "norway",
        "finland", "portugal", "belgium", "austria", "switzerland", "greece",
        "australia", "new zealand",
    ), PAL),
    **dict.fromkeys(("japan", "jp", "asia", "korea", "taiwan", "hong kong"), NTSC_J),
}

_GROUP_RE = re.compile(r"\(([^()]*)\)")


def region_from_name(file_name: str) -> str | None:
    """The region a cover's file name declares, None when it declares none.

    Every group is read, not only the first: "Tomb Raider (PSX) (USA)" puts
    a platform tag first. Callers pass the file's name alone, so no folder
    name decides a region.
    """
    for group in _GROUP_RE.findall(file_name):
        for part in group.split(","):
            region = _REGION_WORDS.get(part.strip().casefold())
            if region is not None:
                return region
    return None


def detect_region(file_name: str) -> str:
    """The region a cover's file name declares, NTSC_U when none does."""
    return region_from_name(file_name) or NTSC_U


# How much of each column of a wordmark is bright, in percent, left to right.
# Learned from clean RetroDB covers (SLIP-0119). Comparing these needs no OCR
# and ships no logo image.
_PLAYSTATION_FOOTER = (
    66, 67, 67, 6, 0, 3, 9, 9, 10, 13, 21, 19, 15, 4, 0, 0, 6, 65, 65, 65,
    7, 0, 0, 10, 34, 43, 48, 33, 24, 22, 20, 14, 11, 38, 65, 65, 58, 0, 0, 0,
    3, 15, 32, 56, 75, 73, 49, 34, 33, 34, 33, 22, 11, 1, 0, 0, 0, 7, 21, 25,
    26, 26, 25, 24, 27, 36, 58, 54, 44, 13, 0, 0, 0, 32, 64, 65, 50, 12, 10, 7,
    0, 0, 9, 33, 43, 48, 34, 24, 22, 20, 14, 11, 36, 67, 67, 64, 0, 0, 0, 6,
    61, 65, 65, 30, 10, 9, 2, 0, 0, 0, 51, 67, 67, 38, 0, 0, 0, 22, 54, 60,
    63, 42, 16, 13, 11, 11, 13, 18, 48, 63, 59, 47, 6, 0, 0, 0, 57, 67, 67, 28,
    0, 0, 0, 0, 0, 3, 55, 67, 67, 37, 0, 0, 2, 10, 9, 17, 10, 15, 8, 11,
)
_DREAMCAST_HEADER = (
    0, 0, 0, 0, 1, 78, 81, 76, 18, 12, 12, 12, 12, 12, 12, 14, 15, 19, 30, 56,
    53, 38, 1, 2, 39, 44, 31, 13, 12, 12, 14, 15, 23, 31, 33, 27, 23, 21, 21, 21,
    24, 29, 27, 13, 0, 1, 14, 18, 19, 19, 21, 22, 27, 34, 30, 7, 0, 22, 43, 37,
    12, 12, 11, 12, 14, 26, 38, 33, 15, 12, 12, 12, 14, 22, 33, 27, 16, 16, 26, 24,
    17, 14, 12, 11, 10, 10, 11, 9, 0, 0, 9, 16, 18, 19, 21, 21, 23, 32, 32, 21,
    5, 21, 31, 29, 25, 21, 19, 17, 13, 11, 9, 11, 55, 66, 42, 10, 10, 9, 1, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 22, 33, 36, 39, 41, 44,
    42, 42, 44, 42, 43, 42, 39, 23, 19, 14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
)

# Thresholds rest on covers labelled by libretro's file names: at these values
# neither mark fires on a USA or Japan cover sampled (SLIP-0119). A wrong
# override is no better than the default, so each sits above every such cover.
_PS1_FOOTER_MATCH = 0.40
_PS1_FOOTER_DARK = 0.55
_DC_HEADER_MATCH = 0.37
_DC_HEADER_BLUE = 0.50

_MARK_WIDTH = 512
_BRIGHT = 150
# Width over height of an image the marks may be looked for on. Thresholds were
# set on single covers, so a wrap (back, spine and front in one) keeps the
# default; the limit on height also bounds the resize, whatever the image's size.
_COVER_ASPECT = (0.5, 1.4)


def _mark_match(gray: np.ndarray, mark: tuple[int, ...],
                bands: tuple[tuple[float, float], ...],
                widths: tuple[float, ...]) -> float:
    """How well `mark` fits any of `bands` (shares of the height) at any of
    `widths` (shares of the width), from 0 to 1."""
    height, width = gray.shape
    template = np.asarray(mark, dtype=np.float32).reshape(1, -1)
    best = 0.0
    for top, bottom in bands:
        band = gray[int(height * top):int(height * bottom)]
        columns = (band > _BRIGHT).mean(axis=0).astype(np.float32).reshape(1, -1)
        if columns.std() == 0:
            continue
        for share in widths:
            sized = cv2.resize(template, (int(width * share), 1), interpolation=cv2.INTER_AREA)
            match = cv2.matchTemplate(columns, sized, cv2.TM_CCOEFF_NORMED)
            best = max(best, float(match.max()))
    return best


def _has_ps1_pal_footer(rgb: np.ndarray, gray: np.ndarray) -> bool:
    """The black strip across the foot of a PAL PS1 cover, with the wordmark."""
    height = gray.shape[0]
    dark = float((gray[int(height * .90):int(height * .96)] < 90).mean())
    if dark < _PS1_FOOTER_DARK:
        return False
    return _mark_match(
        gray, _PLAYSTATION_FOOTER,
        ((.86, .96), (.87, .97), (.88, .98), (.89, .99)),
        (.5, .55, .6, .65, .7, .75, .8, .85, .9),
    ) >= _PS1_FOOTER_MATCH


def _has_dreamcast_pal_header(rgb: np.ndarray, gray: np.ndarray) -> bool:
    """The blue band across the head of a PAL Dreamcast cover: the wordmark
    and the swirl box. Blue sky alone has neither; a wordmark-sized title on
    other art is not blue."""
    height = gray.shape[0]
    red, green, blue = (rgb[int(height * .015):int(height * .115)][..., i].astype(np.int16)
                        for i in range(3))
    if float(((blue > red + 25) & (blue > green + 5) & (blue > 70)).mean()) < _DC_HEADER_BLUE:
        return False
    return _mark_match(
        gray, _DREAMCAST_HEADER,
        ((.01, .105), (.02, .115), (.03, .125)),
        (470 / _MARK_WIDTH, 485 / _MARK_WIDTH, 500 / _MARK_WIDTH),
    ) >= _DC_HEADER_MATCH


# Only marks tested against covers of every region. PS2 has none: European
# covers share no one mark, as each country's rating badge differs. Nothing
# here names Japan: the PS1 corner logo fired on too few Japanese covers.
_PAL_MARKS = {"PS1": _has_ps1_pal_footer, "Dreamcast": _has_dreamcast_pal_header}


def artwork_can_tell(platform: str) -> bool:
    """Whether region_from_artwork has any mark to look for on this platform."""
    return platform in _PAL_MARKS


def region_from_artwork(image: Image.Image, platform: str) -> str | None:
    """The region `image`'s printed marks show, None when they show none.

    None is the common answer and says nothing about the cover: the caller
    keeps its default.
    """
    test = _PAL_MARKS.get(platform)
    if test is None or not _COVER_ASPECT[0] <= image.width / image.height <= _COVER_ASPECT[1]:
        return None
    flat = Image.new("RGBA", image.size, "black")
    flat.alpha_composite(image.convert("RGBA"))
    small = flat.convert("RGB").resize(
        (_MARK_WIDTH, max(1, round(_MARK_WIDTH * image.height / image.width))),
        Image.Resampling.BILINEAR)
    rgb = np.asarray(small)
    gray = np.asarray(small.convert("L"))
    return PAL if test(rgb, gray) else None


def cover_region(file_name: str, image: Image.Image | None, platform: str) -> str:
    """A cover's region: its file name's, else its artwork's, else NTSC_U."""
    named = region_from_name(file_name)
    if named is not None:
        return named
    if image is not None:
        return region_from_artwork(image, platform) or NTSC_U
    return NTSC_U
