"""libretro-thumbnails direct access for cover art."""

import re
from urllib.parse import quote

from PIL import Image

from api.base import APIClient


class LibretroThumbnails(APIClient):
    """Direct access to libretro-thumbnails repository for cover art."""

    BASE_URL = "https://thumbnails.libretro.com"

    # Region tags appended to a bare title when the exact name misses.
    # Ordered by library coverage; the empty string keeps the exact name
    # first, for a caller that already holds the full ROM name.
    REGION_SUFFIXES: tuple[str, ...] = (
        "", " (USA)", " (World)", " (Europe)", " (Japan)",
    )

    def __init__(self):
        super().__init__(base_url=self.BASE_URL, min_request_interval=0.5)

    @property
    def is_configured(self) -> bool:
        """Always available - no auth required."""
        return True

    @staticmethod
    def sanitize_name(name: str) -> str:
        """Sanitize a game name for libretro thumbnail URLs.

        Special chars &*/:`<>?\\| and " are replaced with _.
        """
        return re.sub(r'[&*/:`<>?\\|"]', '_', name)

    def get_boxart_url(self, system: str, game_name: str) -> str:
        """Build the URL for a game's boxart thumbnail.

        Args:
            system: libretro system name (e.g., "Sony - PlayStation 2").
            game_name: Game name (will be sanitized).

        Returns:
            Full URL to the thumbnail image.
        """
        safe_name = self.sanitize_name(game_name)
        # libretro's rule is about the FILENAME; the result still has to be
        # URL-safe. '#' would start a fragment and '%' would be re-quoted,
        # so both would silently 404 without this.
        return (
            f"{self.BASE_URL}/{quote(system, safe='')}"
            f"/Named_Boxarts/{quote(safe_name, safe='')}.png"
        )

    def candidate_urls(self, system: str, game_name: str) -> list[str]:
        """Ordered URLs to try for one game, most likely first.

        A libretro thumbnail is named after the full No-Intro ROM name, which
        carries a region tag: the SNES cover for Super Mario World is stored as
        "Super Mario World (USA).png". A bare title 404s, so searching for what
        a person actually types found nothing at all until 2026-09-02.

        The exact name is tried first, so a caller that already holds the full
        ROM name pays nothing for this. The tags after it are ordered by how
        much of the library they cover.

        The names are case-sensitive, so a title typed all in lower case is
        tried again capitalised (SLIP-0116). A title with any capital is
        taken as the user typed it, and costs no extra requests.
        """
        names = [game_name]
        if game_name == game_name.lower() and game_name != self.capitalise(game_name):
            names.append(self.capitalise(game_name))
        return [
            self.get_boxart_url(system, name + suffix)
            for name in names
            for suffix in self.REGION_SUFFIXES
        ]

    # Words No-Intro names keep in lower case inside a title.
    _SMALL_WORDS = frozenset(
        ("a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to", "vs"))

    @classmethod
    def capitalise(cls, title: str) -> str:
        """`title` capitalised as No-Intro names are: every word, except
        small words that do not start the title or a part after " - "."""
        words = title.split(" ")
        return " ".join(
            word[:1].upper() + word[1:]
            if i == 0 or words[i - 1] == "-" or word not in cls._SMALL_WORDS else word
            for i, word in enumerate(words)
        )

    def download_boxart(self, system: str, game_name: str) -> Image.Image | None:
        """Download a game's boxart from libretro-thumbnails.

        Tries the exact name, then the common region tags, and stops at the
        first hit. A total miss costs one request per candidate.

        Args:
            system: libretro system name.
            game_name: Game name.

        Returns:
            PIL Image or None if no candidate resolved.
        """
        for url in self.candidate_urls(system, game_name):
            img = self.download_image(url)
            if img is not None:
                return img
        return None


# Map platform names to libretro system directory names
LIBRETRO_SYSTEMS: dict[str, str] = {
    "NES": "Nintendo - Nintendo Entertainment System",
    "SNES": "Nintendo - Super Nintendo Entertainment System",
    "N64": "Nintendo - Nintendo 64",
    "Game Boy": "Nintendo - Game Boy",
    "Game Boy Color": "Nintendo - Game Boy Color",
    "GBA": "Nintendo - Game Boy Advance",
    "DS": "Nintendo - Nintendo DS",
    "3DS": "Nintendo - Nintendo 3DS",
    "GameCube": "Nintendo - GameCube",
    "Wii": "Nintendo - Wii",
    "Switch": "Nintendo - Switch",
    "Genesis": "Sega - Mega Drive - Genesis",
    "Mega Drive": "Sega - Mega Drive - Genesis",
    "Saturn": "Sega - Saturn",
    "Dreamcast": "Sega - Dreamcast",
    "PS1": "Sony - PlayStation",
    "PS2": "Sony - PlayStation 2",
    "PS3": "Sony - PlayStation 3",
    "PS4": "Sony - PlayStation 4",
    "PSP": "Sony - PlayStation Portable",
    "Vita": "Sony - PlayStation Vita",
    "Xbox": "Microsoft - Xbox",
    "Xbox 360": "Microsoft - Xbox 360",
    "PC": "DOS",
}
