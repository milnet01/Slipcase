"""ScreenScraper API client for game cover art search and download."""

from dataclasses import dataclass

from api.base import APIClient
from PIL import Image


# Region priority for selecting best media (matches RetroDB)
REGION_PRIORITY = ["us", "wor", "eu", "uk", "jp", "ss"]


@dataclass
class ScreenScraperResult:
    """A search result from ScreenScraper."""
    game_id: int
    name: str
    platform: str
    front_url: str | None = None
    back_url: str | None = None
    spine_url: str | None = None
    box3d_url: str | None = None
    wheel_url: str | None = None


def _select_best_media(media_list: list[dict]) -> dict | None:
    """Select best media item based on region priority."""
    if not media_list:
        return None
    for region in REGION_PRIORITY:
        for m in media_list:
            if (m.get("region") or "").lower() == region:
                return m
    return media_list[0]


def _parse_medias(medias: list[dict]) -> dict[str, str]:
    """Parse media list and select best URL for each type we care about.

    Returns dict mapping our keys to URLs.
    """
    # Group media by type
    by_type: dict[str, list[dict]] = {}
    for m in medias:
        mtype = m.get("type", "")
        if mtype not in by_type:
            by_type[mtype] = []
        by_type[mtype].append(m)

    result = {}
    type_map = {
        "box-2D": "front",
        "box-2D-back": "back",
        "box-2D-side": "spine",
        "box-3D": "box3d",
        "wheel": "wheel",
    }
    for ss_type, our_key in type_map.items():
        if ss_type in by_type:
            best = _select_best_media(by_type[ss_type])
            if best and best.get("url"):
                result[our_key] = best["url"]

    return result


class ScreenScraperAPI(APIClient):
    """Client for the ScreenScraper API v2."""

    API_URL = "https://api.screenscraper.fr/api2"

    def __init__(
        self,
        devid: str = "",
        devpassword: str = "",
        username: str = "",
        password: str = "",
    ):
        super().__init__(base_url=self.API_URL, min_request_interval=1.2)
        self.devid = devid
        self.devpassword = devpassword
        self.username = username
        self.password = password

    def _auth_params(self) -> list[tuple[str, str]]:
        """Build ordered authentication parameters.

        Parameter order matters: devid/devpassword MUST come before ssid/sspassword.
        Returns list of tuples to preserve order.
        """
        params = []
        if self.devid and self.devpassword:
            params.append(("devid", self.devid))
            params.append(("devpassword", self.devpassword))
        params.append(("softname", "BoxArt3D"))
        if self.username:
            params.append(("ssid", self.username))
            params.append(("sspassword", self.password))
        params.append(("output", "json"))
        return params

    @property
    def is_configured(self) -> bool:
        """Check if API credentials are set.

        ScreenScraper requires the developer pair as well as the user
        account; without all four it rejects the request, so reporting
        'configured' on the username alone turns a setup mistake into an
        empty result list.
        """
        return bool(self.username and self.devid and self.devpassword)

    def search_game(self, name: str, system_id: int | None = None) -> list[ScreenScraperResult]:
        """Search for a game by name.

        Args:
            name: Game name to search for.
            system_id: Optional ScreenScraper system ID to filter by.

        Returns:
            List of search results with media URLs.
        """
        params = self._auth_params()
        params.append(("recherche", name))
        if system_id is not None:
            params.append(("systemeid", str(system_id)))

        data = self.get_json("jeuRecherche.php", params=params)
        if not isinstance(data, dict):
            # Quota exhaustion and outages are answered with non-JSON or a
            # bare list; treat that as no results rather than an AttributeError.
            return []

        results = []
        for game in data.get("response", {}).get("jeux", []):
            result = self._parse_game(game)
            if result:
                results.append(result)
        return results

    def download_front(self, result: ScreenScraperResult) -> Image.Image | None:
        """Download the front cover image."""
        if result.front_url:
            return self.download_image(result.front_url)
        return None

    def download_back(self, result: ScreenScraperResult) -> Image.Image | None:
        """Download the back cover image."""
        if result.back_url:
            return self.download_image(result.back_url)
        return None

    def download_spine(self, result: ScreenScraperResult) -> Image.Image | None:
        """Download the spine/side image."""
        if result.spine_url:
            return self.download_image(result.spine_url)
        return None

    def download_box3d(self, result: ScreenScraperResult) -> Image.Image | None:
        """Download the pre-rendered 3D box art."""
        if result.box3d_url:
            return self.download_image(result.box3d_url)
        return None

    def _parse_game(self, game: dict) -> ScreenScraperResult | None:
        """Parse a game dict from the API response."""
        try:
            game_id = int(game.get("id", 0))

            # Get best name (prefer US > World > SS > first available)
            names = game.get("noms", [])
            name = ""
            for region in REGION_PRIORITY:
                for n in names:
                    if (n.get("region") or "").lower() == region:
                        name = n.get("text", "")
                        break
                if name:
                    break
            if not name and names:
                name = names[0].get("text", "")

            system = game.get("systeme", {}).get("text", "")

            # Parse media URLs with region priority
            medias = game.get("medias", [])
            media_urls = _parse_medias(medias)

            return ScreenScraperResult(
                game_id=game_id,
                name=name,
                platform=system,
                front_url=media_urls.get("front"),
                back_url=media_urls.get("back"),
                spine_url=media_urls.get("spine"),
                box3d_url=media_urls.get("box3d"),
                wheel_url=media_urls.get("wheel"),
            )
        except (AttributeError, KeyError, ValueError, TypeError):
            return None


# ScreenScraper system IDs for common platforms
SCREENSCRAPER_SYSTEMS: dict[str, int] = {
    "NES": 3,
    "SNES": 4,
    "N64": 14,
    "Game Boy": 9,
    "Game Boy Color": 10,
    "GBA": 12,
    "DS": 15,
    "3DS": 17,
    "GameCube": 13,
    "Wii": 16,
    "Switch": 225,
    "Genesis": 1,
    "Mega Drive": 1,
    "Saturn": 22,
    "Dreamcast": 23,
    "PS1": 57,
    "PS2": 58,
    "PS3": 59,
    "PS4": 60,
    "PS5": 307,
    "PSP": 61,
    "Vita": 62,
    "Xbox": 32,
    "Xbox 360": 33,
    "Xbox One": 34,
    "Xbox Series X": 308,
    "PC": 135,
}
