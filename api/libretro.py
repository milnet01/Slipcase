"""libretro-thumbnails direct access for cover art."""

import re
from PIL import Image
from api.base import APIClient


class LibretroThumbnails(APIClient):
    """Direct access to libretro-thumbnails repository for cover art."""

    BASE_URL = "https://thumbnails.libretro.com"

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
        return f"{self.BASE_URL}/{system}/Named_Boxarts/{safe_name}.png"

    def download_boxart(self, system: str, game_name: str) -> Image.Image | None:
        """Download a game's boxart from libretro-thumbnails.

        Args:
            system: libretro system name.
            game_name: Game name.

        Returns:
            PIL Image or None if not found.
        """
        url = self.get_boxart_url(system, game_name)
        return self.download_image(url)


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
