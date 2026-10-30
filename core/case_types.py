"""Case type definitions with real-world dimensions for game box rendering."""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class JewelGeometry:
    """The paper inside a jewel case, in mm. W x H, W across the front."""
    booklet: tuple[float, float]    # front insert
    back_card: tuple[float, float]  # back insert laid flat, both end strips included
    strip: float                    # width of one end strip


@dataclass(frozen=True)
class TrayPrint:
    """The panel printed on the inside of a clear tray's back card, seen
    through the front's hinge strip. It is the same on every game. An empty
    `text` prints none."""
    text: str
    paper: tuple[int, int, int]
    ink: tuple[int, int, int]
    length: float           # mm the text runs along the strip
    reads_up: bool          # bottom to top on an upright case
    swirl: bool = False     # Dreamcast's orange swirl after the first word
    # mm across the strip, from its outer edge, of a band of printed ribs in
    # `ink` fading into `paper`; None for no ribs.
    ribs: tuple[float, float] | None = None


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
    # Bare plastic colour; on a clear case, its tint (SLIP-0107).
    plastic: tuple[int, int, int] | None = None
    # A jewel lid clear only over the booklet: the hinge strip is the tray's
    # matte plastic, so the lid's gloss stops at the booklet's side.
    matte_hinge_strip: bool = False
    # Fine vertical ridges across a black hinge strip, on the front (PAL PS1).
    ridged_hinge_strip: bool = False
    # A see-through jewel tray: the front's hinge strip shows this panel of
    # the back card through it (SLIP-0115).
    tray_print: TrayPrint | None = None
    # Text moulded in a panel on a jewel tray's front hinge strip (SLIP-0112).
    strip_logo: str | None = None
    # Text moulded into the plastic of the top and bottom edges (SLIP-0110).
    moulded_logo: str | None = None
    # Overlay family for the wrap layout: "dvd", "bluray", "switch", "ds",
    # "psp", "cardboard", or None for no overlay (SLIP-0107).
    texture: str | None = None
    # Clear or tinted plastic: the cover shows through, so the edges keep
    # the cover's colour, tinted by `plastic` when set, and the front shines.
    clear: bool = False

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
_BLACK_KEEP = (0x14, 0x14, 0x14)
_WHITE_KEEP = (0xEE, 0xEE, 0xEE)
_BLUE_TINT = (0x2A, 0x6C, 0xD0)
_GREEN_TINT = (0x2E, 0x9E, 0x3A)
# What the user's US cases show through the clear tray (photos, 2026-10-21):
# six Dreamcast games' "Sega Dreamcast" on white, length estimated from those
# photos; and on PS1, black with a printed ribbed band, measured from the
# inside of Crash Bandicoot's back card. The user asked for that band on every
# NTSC PS1 case until a case can be opened (2026-10-21). Ink levels follow the
# user's DuckStation PS1 covers and LaunchBox Sonic Adventure box (2026-10-30).
_PS1_NTSC_TRAY_PRINT = TrayPrint(text="", paper=(0x00, 0x00, 0x00),
                                 ink=(0x78, 0x78, 0x7C), length=0, reads_up=True,
                                 ribs=(6.1, 18.5))
_DREAMCAST_US_TRAY_PRINT = TrayPrint(text="Sega Dreamcast", paper=(0xF4, 0xF4, 0xF2),
                                     ink=(0x18, 0x18, 0x18), length=67, reads_up=True,
                                     swirl=True)

CASE_TYPES: dict[str, CaseType] = {
    # Keep cases: one printed sheet wraps back + spine + front under a clear
    # sleeve. Sizes and colours per console and region (SLIP-0107 § 4.1);
    # colours the sources do not give are judged by eye. A clear case
    # shows the cover through its plastic; `plastic` then tints it.
    "PS2 DVD Case": CaseType(
        name="PS2 DVD Case",
        width=135, height=190, depth=14,
        platforms=("PS2",),
        plastic=_BLACK_KEEP, texture="dvd",
    ),
    "PS2 DVD Case (PAL)": CaseType(
        name="PS2 DVD Case (PAL)",
        width=135, height=190, depth=14,
        platforms=(),
        plastic=(0x1F, 0x4E, 0xA8), texture="dvd",
    ),
    "Wii DVD Case": CaseType(
        name="Wii DVD Case",
        width=135, height=190, depth=14,
        platforms=("Wii",),
        plastic=_WHITE_KEEP, texture="dvd",
    ),
    "GameCube DVD Case": CaseType(
        name="GameCube DVD Case",
        width=135, height=190, depth=14,
        platforms=("GameCube",),
        plastic=_BLACK_KEEP, texture="dvd",
    ),
    "GameCube Case (NTSC-J)": CaseType(
        name="GameCube Case (NTSC-J)",
        width=107, height=149, depth=17,
        platforms=(),
        clear=True, texture="dvd",
    ),
    "PC DVD Case": CaseType(
        name="PC DVD Case",
        width=135, height=190, depth=14,
        platforms=("PC",),
        plastic=_BLACK_KEEP, texture="dvd",
    ),
    "Xbox Case": CaseType(
        name="Xbox Case",
        width=129, height=189, depth=13,
        platforms=("Xbox",),
        plastic=(0x5C, 0xB0, 0x2E), texture="dvd",
    ),
    "Xbox 360 Case": CaseType(
        name="Xbox 360 Case",
        width=133, height=187, depth=13,
        platforms=("Xbox 360",),
        plastic=(0x6C, 0xC0, 0x40), clear=True, texture="dvd",
    ),
    "PS3 Blu-ray Case": CaseType(
        name="PS3 Blu-ray Case",
        width=135, height=171.5, depth=13,
        platforms=("PS3",),
        plastic=(0xF0, 0xF0, 0xF0), clear=True, texture="bluray",
    ),
    "PS4 Blu-ray Case": CaseType(
        name="PS4 Blu-ray Case",
        width=135, height=171.5, depth=13,
        platforms=("PS4",),
        plastic=_BLUE_TINT, clear=True, texture="bluray",
    ),
    "PS5 Blu-ray Case": CaseType(
        name="PS5 Blu-ray Case",
        width=135, height=171.5, depth=13,
        platforms=("PS5",),
        plastic=_BLUE_TINT, clear=True, texture="bluray",
    ),
    "Xbox One Case": CaseType(
        name="Xbox One Case",
        width=135, height=171.5, depth=13,
        platforms=("Xbox One",),
        plastic=_GREEN_TINT, clear=True, texture="bluray",
    ),
    "Xbox Series X Case": CaseType(
        name="Xbox Series X Case",
        width=135, height=171.5, depth=13,
        platforms=("Xbox Series X",),
        plastic=_GREEN_TINT, clear=True, texture="bluray",
    ),
    # Jewel cases stand landscape: the back card folds at the ends of its
    # long side, so the folds sit on the case's two 125 mm edges, one being
    # the hinge (SLIP-0106 § 2). Every one is a music CD case in its maker's
    # plastic; only the PS1 PAL case is thicker (the user, 2026-10-21).
    # Regional variants list no platform, so each platform keeps one
    # default; REGIONAL_CASES picks the variant.
    "CD Jewel Case": CaseType(
        name="CD Jewel Case",
        # "PC" is deliberately NOT listed here: it is claimed by PC DVD Case
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
        tray_print=_PS1_NTSC_TRAY_PRINT,
    ),
    # Only thicker than the standard case. Its back card is measured from a
    # PAL scan: wider, with end strips that wrap the 18 mm sides. Its black
    # parts are matte, its clear parts glossy (the user, 2026-10-21).
    "PS1 Jewel Case (PAL)": CaseType(
        name="PS1 Jewel Case (PAL)",
        width=142, height=125, depth=18,
        platforms=(),
        jewel=JewelGeometry(booklet=(120, 120), back_card=(158, 118), strip=13.5),
        plastic=_BLACK_TRAY, matte_hinge_strip=True, ridged_hinge_strip=True,
        moulded_logo="PlayStation",
    ),
    "PS1 Jewel Case (NTSC-J)": CaseType(
        name="PS1 Jewel Case (NTSC-J)",
        width=142, height=125, depth=10,
        platforms=(),
        jewel=_STANDARD_PAPER, plastic=_BLACK_TRAY,
        tray_print=_PS1_NTSC_TRAY_PRINT,
    ),
    "Dreamcast Jewel Case (NTSC-U)": CaseType(
        name="Dreamcast Jewel Case (NTSC-U)",
        width=142, height=125, depth=10.4,
        platforms=("Dreamcast",),
        # A clear tray has no colour of its own: a pale grey stands in.
        jewel=_STANDARD_PAPER, plastic=(0xC8, 0xCC, 0xD0),
        tray_print=_DREAMCAST_US_TRAY_PRINT,
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
        strip_logo="Dreamcast",
    ),
    "NES Cartridge Box": CaseType(
        name="NES Cartridge Box",
        width=127, height=175, depth=22,
        platforms=("NES",),
        texture="cardboard",
    ),
    # US and PAL SNES and N64 boxes lie landscape; the Japanese ones stand
    # portrait. Sources: docs/research/SLIP-0108-cartridge-boxes.md.
    "SNES Cartridge Box": CaseType(
        name="SNES Cartridge Box",
        # A US Chrono Trigger box, 7 x 5 x 1.25 in.
        width=178, height=127, depth=32,
        platforms=("SNES",),
        texture="cardboard",
    ),
    "Super Famicom Cartridge Box": CaseType(
        name="Super Famicom Cartridge Box",
        width=105, height=190, depth=30,
        platforms=(),
        texture="cardboard",
    ),
    "N64 Cartridge Box": CaseType(
        name="N64 Cartridge Box",
        # Unmeasured: the SNES box's size, inside the 181 x 127 x 32 mm a
        # protector seller gives.
        width=178, height=127, depth=32,
        platforms=("N64",),
        texture="cardboard",
    ),
    "N64 Cartridge Box (NTSC-J)": CaseType(
        name="N64 Cartridge Box (NTSC-J)",
        width=138, height=190, depth=30,
        platforms=(),
        texture="cardboard",
    ),
    "Genesis Clamshell": CaseType(
        name="Genesis Clamshell",
        width=135, height=195, depth=23,
        platforms=("Genesis", "Mega Drive"),
        texture="cardboard",
    ),
    "Game Boy Box": CaseType(
        name="Game Boy Box",
        width=79, height=112, depth=30,
        platforms=("Game Boy", "Game Boy Color"),
        texture="cardboard",
    ),
    "GBA Box": CaseType(
        name="GBA Box",
        width=79, height=112, depth=22,
        platforms=("GBA",),
        texture="cardboard",
    ),
    "DS Case": CaseType(
        name="DS Case",
        width=122, height=135, depth=15,
        platforms=("DS",),
        plastic=_BLACK_KEEP, texture="ds",
    ),
    "DS Case (PAL)": CaseType(
        name="DS Case (PAL)",
        width=122, height=135, depth=20,
        platforms=(),
        clear=True, texture="ds",
    ),
    "3DS Case": CaseType(
        name="3DS Case",
        width=122, height=135, depth=12,
        platforms=("3DS",),
        plastic=_WHITE_KEEP, texture="ds",
    ),
    "PSP Case": CaseType(
        name="PSP Case",
        width=99, height=168, depth=14,
        platforms=("PSP",),
        clear=True, texture="psp",
    ),
    "PS Vita Case": CaseType(
        name="PS Vita Case",
        width=105, height=135, depth=12,
        platforms=("Vita",),
        plastic=(0x1E, 0x50, 0xB4), texture="psp",
    ),
    "Switch Case": CaseType(
        name="Switch Case",
        width=104, height=170, depth=10,
        platforms=("Switch",),
        clear=True, texture="switch",
    ),
    "Universal Cart Case": CaseType(
        name="Universal Cart Case",
        width=135, height=185, depth=24.5,
        platforms=(),
        texture="cardboard",
    ),
}

# Edition and special-colour cases, picked by hand (SLIP-0113): the
# standard case in another plastic. Colours from Wikipedia, Keep case,
# per docs/research/SLIP-0113-edition-cases.md; every RGB is judged by eye.
_SILVER = (0xB4, 0xB8, 0xBE)
_RED_KEEP = (0xB0, 0x1C, 0x1C)
_EDITION_PLASTIC: dict[str, tuple[str, dict]] = {
    "PS2 Platinum Case (PAL)": ("PS2 DVD Case", {"plastic": _SILVER}),
    "PS2 DVD Case (navy)": ("PS2 DVD Case", {"plastic": (0x1A, 0x24, 0x4C)}),
    "PS2 DVD Case (red)": ("PS2 DVD Case", {"plastic": _RED_KEEP}),
    "PS2 DVD Case (white)": ("PS2 DVD Case", {"plastic": _WHITE_KEEP}),
    "PS2 DVD Case (clear)": ("PS2 DVD Case", {"plastic": None, "clear": True}),
    "PS3 Greatest Hits Case": ("PS3 Blu-ray Case", {"plastic": _RED_KEEP, "clear": False}),
    "PS3 Platinum Case (PAL)": ("PS3 Blu-ray Case", {"plastic": _SILVER, "clear": False}),
    "Xbox Platinum Hits Case": ("Xbox Case", {"plastic": _SILVER}),
    "Xbox 360 Platinum Hits Case": ("Xbox 360 Case", {"plastic": (0x90, 0x94, 0x9A)}),
    "Xbox 360 Kinect Case": ("Xbox 360 Case", {"plastic": (0x8A, 0x3C, 0xC8)}),
    "GameCube Player's Choice Case (PAL)": ("GameCube DVD Case", {"plastic": _SILVER}),
    "GameCube DVD Case (blue)": ("GameCube DVD Case", {"plastic": (0x1F, 0x4E, 0xA8)}),
    "GameCube DVD Case (red)": ("GameCube DVD Case", {"plastic": _RED_KEEP}),
    "Wii DVD Case (red)": ("Wii DVD Case", {"plastic": _RED_KEEP}),
    "Wii DVD Case (yellow)": ("Wii DVD Case", {"plastic": (0xF2, 0xC8, 0x14)}),
    "Wii DVD Case (black)": ("Wii DVD Case", {"plastic": _BLACK_KEEP}),
}
# edition -> the standard case it recolours
EDITIONS: dict[str, str] = {name: base for name, (base, _) in _EDITION_PLASTIC.items()}
for _name, (_base, _changes) in _EDITION_PLASTIC.items():
    CASE_TYPES[_name] = replace(CASE_TYPES[_base], name=_name, platforms=(), **_changes)

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
    ("PS2", "PAL"): "PS2 DVD Case (PAL)",
    ("DS", "PAL"): "DS Case (PAL)",
    ("GameCube", "NTSC-J"): "GameCube Case (NTSC-J)",
    ("SNES", "NTSC-J"): "Super Famicom Cartridge Box",
    ("N64", "NTSC-J"): "N64 Cartridge Box (NTSC-J)",
}


def case_for(platform: str, region: str) -> CaseType | None:
    """The case for `platform` in `region`: its regional variant, else the
    platform's default case, else None."""
    case_name = REGIONAL_CASES.get((platform, region))
    if case_name:
        return CASE_TYPES[case_name]
    return get_case_for_platform(platform)


_CARTRIDGE_PLATFORMS = ("NES", "SNES", "N64", "Genesis", "Mega Drive",
                        "Game Boy", "Game Boy Color", "GBA")

# platform -> cases picked only by hand, beyond its default and regional
# cases (SLIP-0113), editions included.
EXTRA_CASES: dict[str, tuple[str, ...]] = {
    "PC": ("CD Jewel Case",),
    **{platform: ("Universal Cart Case",) for platform in _CARTRIDGE_PLATFORMS},
}
for _name, _base in EDITIONS.items():
    _platform = CASE_TYPES[_base].platforms[0]
    EXTRA_CASES[_platform] = (*EXTRA_CASES.get(_platform, ()), _name)


def cases_for_platform(platform: str) -> list[str]:
    """The case list's entries for `platform`: its default case, then its
    regional cases, then its hand-picked extras (SLIP-0113)."""
    names = [PLATFORM_CASE_MAP[platform]] if platform in PLATFORM_CASE_MAP else []
    names += [name for (p, _region), name in REGIONAL_CASES.items() if p == platform]
    names += EXTRA_CASES.get(platform, ())
    return list(dict.fromkeys(names))
