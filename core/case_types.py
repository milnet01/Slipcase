"""Case type definitions with real-world dimensions for game box rendering."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CaseType:
    """A game case type with real-world dimensions in millimeters."""
    name: str
    width: float   # mm, front face width
    height: float  # mm, front face height
    depth: float   # mm, spine depth
    platforms: tuple[str, ...]

    @property
    def aspect_ratio(self) -> float:
        """Front face width/height ratio."""
        return self.width / self.height

    @property
    def depth_ratio(self) -> float:
        """Depth relative to front width."""
        return self.depth / self.width


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
    "CD Jewel Case": CaseType(
        name="CD Jewel Case",
        width=125, height=142, depth=10.4,
        platforms=("PS1", "Saturn", "Dreamcast", "PC"),
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
