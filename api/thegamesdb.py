"""TheGamesDB API client for game cover art search and download."""

from dataclasses import dataclass

from api.base import APIClient
from PIL import Image


@dataclass
class TheGamesDBResult:
    """A search result from TheGamesDB."""
    game_id: int
    name: str
    platform: str
    release_date: str
    front_url: str | None
    back_url: str | None
    clearlogo_url: str | None


class TheGamesDBAPI(APIClient):
    """Client for TheGamesDB API v1."""

    API_URL = "https://api.thegamesdb.net/v1"
    IMAGE_BASE = "https://cdn.thegamesdb.net/images/original"

    def __init__(self, api_key: str = ""):
        super().__init__(base_url=self.API_URL, min_request_interval=1.0)
        self.api_key = api_key

    @property
    def is_configured(self) -> bool:
        """Check if API key is set."""
        return bool(self.api_key)

    def search_game(self, name: str, platform_id: int | None = None) -> list[TheGamesDBResult]:
        """Search for a game by name.

        Args:
            name: Game name to search for.
            platform_id: Optional platform ID to filter.

        Returns:
            List of search results.
        """
        params = {
            "apikey": self.api_key,
            "name": name,
            "include": "boxart",
        }
        if platform_id is not None:
            params["filter[platform]"] = str(platform_id)

        data = self.get_json("Games/ByGameName", params=params)
        if not isinstance(data, dict):
            return []

        results = []
        games = data.get("data", {}).get("games", [])
        images = data.get("include", {}).get("boxart", {}).get("data", {})
        base_url = data.get("include", {}).get("boxart", {}).get("base_url", {})
        original_base = base_url.get("original", self.IMAGE_BASE + "/")

        for game in games:
            game_id = game.get("id", 0)
            game_images = images.get(str(game_id), [])

            front_url = None
            back_url = None

            for img in game_images:
                side = img.get("side", "")
                filename = img.get("filename", "")
                if side == "front" and not front_url:
                    front_url = original_base + filename
                elif side == "back" and not back_url:
                    back_url = original_base + filename

            results.append(TheGamesDBResult(
                game_id=game_id,
                name=game.get("game_title", ""),
                platform=str(game.get("platform", "")),
                release_date=game.get("release_date", ""),
                front_url=front_url,
                back_url=back_url,
                clearlogo_url=None,
            ))

        return results

    def download_front(self, result: TheGamesDBResult) -> Image.Image | None:
        """Download the front cover image."""
        if result.front_url:
            return self.download_image(result.front_url)
        return None

    def download_back(self, result: TheGamesDBResult) -> Image.Image | None:
        """Download the back cover image."""
        if result.back_url:
            return self.download_image(result.back_url)
        return None


# TheGamesDB platform IDs for common platforms
THEGAMESDB_PLATFORMS: dict[str, int] = {
    "NES": 7,
    "SNES": 6,
    "N64": 3,
    "Game Boy": 4,
    "Game Boy Color": 41,
    "GBA": 5,
    "DS": 8,
    "3DS": 4912,
    "GameCube": 2,
    "Wii": 9,
    "Switch": 4971,
    "Genesis": 18,
    "Mega Drive": 36,
    "Saturn": 17,
    "Dreamcast": 16,
    "PS1": 10,
    "PS2": 11,
    "PS3": 12,
    "PS4": 4919,
    "PS5": 4980,
    "PSP": 13,
    "Vita": 39,
    "Xbox": 14,
    "Xbox 360": 15,
    "Xbox One": 4920,
    "Xbox Series X": 4981,
    "PC": 1,
}
