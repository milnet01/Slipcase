"""Case type definitions with real-world dimensions for game box rendering."""

from dataclasses import dataclass


@dataclass(frozen=True)
class JewelGeometry:
    """The paper inside a jewel case, in mm. W x H, W across the front."""
    booklet: tuple[float, float]    # front insert
    back_card: tuple[float, float]  # back insert laid flat, both end strips included
    strip: float                    # width of one end strip


@dataclass(frozen=True)
class CaseType:
    """A game case type with real-world dimensions in millimeters."""
    name: str
    width: float   # mm, front face width
    height: float  # mm, front face height
    depth: float   # mm, spine depth
    platforms: tuple[str, ...]
    # None: the wrap layout, one back + spine + front cover (SLIP-0106).
    jewel: JewelGeometry | None = None
    # Bare plastic colour; the wrap layout ignores it for now.
    plastic: tuple[int, int, int] | None = None

    @property
    def layout(self) -> str:
        """Either "wrap" (back + spine + front) or "jewel" (booklet and back card)."""
        return "wrap" if self.jewel is None else "jewel"

    @property
    def aspect_ratio(self) -> float:
        """Front face width/height ratio."""
        return self.width / self.height

    @property
    def depth_ratio(self) -> float:
        """Depth relative to front width."""
        return self.depth / self.width


# The standard jewel case's paper: a 120 mm booklet, and a 150 x 118 mm back
# card with a 6 mm strip at each end.
_STANDARD_PAPER = JewelGeometry(booklet=(120, 120), back_card=(150, 118), strip=6)
_BLACK_TRAY = (0x10, 0x10, 0x10)

CASE_TYPES: dict[str, CaseType] = {
    "DVD Case": CaseType(
        name="DVD Case",
        width=135, height=190, depth=14,
        platforms=("PS2", "Wii", "Xbox", "Xbox 360", "PC", "GameCube"),
    ),
    "Blu-ray Case": CaseType(
        name="Blu-ray Case",
        width=135, height=171, depth=12.5,
        platforms=("PS3", "PS4", "PS5", "Xbox One", "Xbox Series X"),
    ),
    # Jewel cases stand landscape: the back card folds at the ends of its
    # long side, so the folds sit on the case's two 125 mm edges, one being
    # the hinge (SLIP-0106 § 2). Every one is a music CD case in its maker's
    # plastic; only the PS1 PAL case is thicker (the user, 2026-10-21).
    # Regional variants list no platform, so each platform keeps one
    # default; REGIONAL_CASES picks the variant.
    "CD Jewel Case": CaseType(
        name="CD Jewel Case",
        # "PC" is deliberately NOT listed here: it is claimed by DVD Case
        # above, and PLATFORM_CASE_MAP is built by overwriting, so listing it
        # twice silently gave the later entry the platform and made the
        # mapping depend on CASE_TYPES' insertion order.
        width=142, height=125, depth=10,
        platforms=("Saturn",),
        jewel=_STANDARD_PAPER, plastic=_BLACK_TRAY,
    ),
    "PS1 Jewel Case (NTSC-U)": CaseType(
        name="PS1 Jewel Case (NTSC-U)",
        width=142, height=125, depth=10.4,
        platforms=("PS1",),
        jewel=_STANDARD_PAPER, plastic=_BLACK_TRAY,
    ),
    # Only thicker than the standard case. Its back card is measured from a
    # PAL scan: wider, with end strips that wrap the 18 mm sides.
    "PS1 Jewel Case (PAL)": CaseType(
        name="PS1 Jewel Case (PAL)",
        width=142, height=125, depth=18,
        platforms=(),
        jewel=JewelGeometry(booklet=(120, 120), back_card=(158, 118), strip=13.5),
        plastic=_BLACK_TRAY,
    ),
    "PS1 Jewel Case (NTSC-J)": CaseType(
        name="PS1 Jewel Case (NTSC-J)",
        width=142, height=125, depth=10,
        platforms=(),
        jewel=_STANDARD_PAPER, plastic=_BLACK_TRAY,
    ),
    "Dreamcast Jewel Case (NTSC-U)": CaseType(
        name="Dreamcast Jewel Case (NTSC-U)",
        width=142, height=125, depth=10.4,
        platforms=("Dreamcast",),
        # A clear tray has no colour of its own: a pale grey stands in.
        jewel=_STANDARD_PAPER, plastic=(0xC8, 0xCC, 0xD0),
    ),
    "Dreamcast Jewel Case (NTSC-J)": CaseType(
        name="Dreamcast Jewel Case (NTSC-J)",
        width=142, height=125, depth=10.4,
        platforms=(),
        jewel=_STANDARD_PAPER, plastic=(0xF0, 0xF0, 0xF0),
    ),
    "Dreamcast Jewel Case (PAL)": CaseType(
        name="Dreamcast Jewel Case (PAL)",
        width=142, height=125, depth=10.4,
        platforms=(),
        jewel=_STANDARD_PAPER, plastic=(0x2A, 0x4F, 0x9E),
    ),
    "NES Cartridge Box": CaseType(
        name="NES Cartridge Box",
        width=127, height=175, depth=22,
        platforms=("NES",),
    ),
    "SNES Cartridge Box": CaseType(
        name="SNES Cartridge Box",
        width=127, height=175, depth=30,
        platforms=("SNES",),
    ),
    "N64 Cartridge Box": CaseType(
        name="N64 Cartridge Box",
        width=127, height=175, depth=25,
        platforms=("N64",),
    ),
    "Genesis Clamshell": CaseType(
        name="Genesis Clamshell",
        width=135, height=195, depth=23,
        platforms=("Genesis", "Mega Drive"),
    ),
    "Game Boy Box": CaseType(
        name="Game Boy Box",
        width=79, height=112, depth=30,
        platforms=("Game Boy", "Game Boy Color"),
    ),
    "GBA Box": CaseType(
        name="GBA Box",
        width=79, height=112, depth=22,
        platforms=("GBA",),
    ),
    "DS Case": CaseType(
        name="DS Case",
        width=122, height=135, depth=14,
        platforms=("DS",),
    ),
    "3DS Case": CaseType(
        name="3DS Case",
        width=122, height=135, depth=12,
        platforms=("3DS",),
    ),
    "PSP Case": CaseType(
        name="PSP Case",
        width=105, height=170, depth=14,
        platforms=("PSP",),
    ),
    "PS Vita Case": CaseType(
        name="PS Vita Case",
        width=107, height=135, depth=12,
        platforms=("Vita",),
    ),
    "Switch Case": CaseType(
        name="Switch Case",
        width=104, height=169, depth=10.5,
        platforms=("Switch",),
    ),
    "Universal Cart Case": CaseType(
        name="Universal Cart Case",
        width=135, height=185, depth=24.5,
        platforms=(),
    ),
}

# Map platform names to their default case type
PLATFORM_CASE_MAP: dict[str, str] = {}
for case_name, case in CASE_TYPES.items():
    for platform in case.platforms:
        PLATFORM_CASE_MAP[platform] = case_name

# All known platform names sorted
ALL_PLATFORMS: list[str] = sorted(PLATFORM_CASE_MAP.keys())


def get_case_for_platform(platform: str) -> CaseType | None:
    """Get the default case type for a platform name."""
    case_name = PLATFORM_CASE_MAP.get(platform)
    if case_name:
        return CASE_TYPES[case_name]
    return None


# (platform, region) -> its regional case, where it differs from the default.
REGIONAL_CASES: dict[tuple[str, str], str] = {
    ("PS1", "PAL"): "PS1 Jewel Case (PAL)",
    ("PS1", "NTSC-J"): "PS1 Jewel Case (NTSC-J)",
    ("Dreamcast", "NTSC-J"): "Dreamcast Jewel Case (NTSC-J)",
    ("Dreamcast", "PAL"): "Dreamcast Jewel Case (PAL)",
}


def case_for(platform: str, region: str) -> CaseType | None:
    """The case for `platform` in `region`: its regional variant, else the
    platform's default case, else None."""
    case_name = REGIONAL_CASES.get((platform, region))
    if case_name:
        return CASE_TYPES[case_name]
    return get_case_for_platform(platform)
