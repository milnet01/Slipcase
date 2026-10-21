"""The region a cover's file name declares, from its "(Europe)"-style tags (SLIP-0106 § 4.2)."""

import re

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


def detect_region(file_name: str) -> str:
    """The region a cover's file name declares, NTSC_U when none does.

    Every group is read, not only the first: "Tomb Raider (PSX) (USA)" puts
    a platform tag first. Callers pass the file's name alone, so no folder
    name decides a region.
    """
    for group in _GROUP_RE.findall(file_name):
        for part in group.split(","):
            region = _REGION_WORDS.get(part.strip().casefold())
            if region is not None:
                return region
    return NTSC_U
