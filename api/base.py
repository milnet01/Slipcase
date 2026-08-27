"""Base API client with rate limiting and shared HTTP session."""

import re
import time
from io import BytesIO
from urllib.parse import urlparse

import requests
from PIL import Image

# Maximum image download size (50 MB) to prevent memory exhaustion
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024

# Allowed root domains for image downloads (subdomains are also allowed)
ALLOWED_IMAGE_DOMAINS: set[str] = {
    "screenscraper.fr",
    "thegamesdb.net",
    "thumbnails.libretro.com",
}

# Accepted image formats (reject complex formats with larger attack surface)
_ALLOWED_IMAGE_FORMATS: frozenset[str] = frozenset({
    "PNG", "JPEG", "WEBP", "BMP", "GIF",
})

# Pattern to strip credential values from error messages / URLs
_CREDENTIAL_RE = re.compile(
    r"(devpassword|devid|sspassword|ssid|apikey|api_key|password)=([^&\s]+)",
    re.IGNORECASE,
)


def _sanitize_message(msg: str) -> str:
    """Strip credential values from a string (URLs, error messages)."""
    return _CREDENTIAL_RE.sub(r"\1=***", msg)


def _is_allowed_url(url: str) -> bool:
    """Validate that a URL uses HTTPS and points to an allowed domain."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme != "https":
        return False
    host = parsed.hostname or ""
    # Match exact domain or any subdomain of allowed domains
    for domain in ALLOWED_IMAGE_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return True
    return False


class APIClient:
    """Base HTTP client with rate limiting for cover art APIs."""

    def __init__(self, base_url: str = "", min_request_interval: float = 1.0):
        self.base_url = base_url.rstrip("/")
        self.min_request_interval = min_request_interval
        self._last_request_time = 0.0
        self._session = requests.Session()
        self._session.max_redirects = 5
        self._session.headers.update({
            "User-Agent": "Slipcase/1.0 (Desktop cover art renderer)",
        })

    def _rate_limit(self) -> None:
        """Enforce minimum interval between requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self._last_request_time = time.time()

    def get(self, url: str, params: dict | None = None, **kwargs) -> requests.Response:
        """Make a rate-limited GET request.

        Errors are sanitized to strip credential values before propagating.
        """
        self._rate_limit()
        full_url = f"{self.base_url}/{url.lstrip('/')}" if not url.startswith("http") else url
        try:
            response = self._session.get(
                full_url, params=params, timeout=(10, 30), verify=True, **kwargs
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise requests.RequestException(_sanitize_message(str(e))) from None
        return response

    def get_json(self, url: str, params: dict | None = None) -> dict:
        """GET request returning parsed JSON."""
        return self.get(url, params=params).json()

    def download_image(self, url: str) -> Image.Image | None:
        """Download an image from a URL and return as PIL Image.

        Validates the URL against allowed domains, enforces a size limit via
        streaming (never buffers more than the limit), restricts accepted
        image formats, and calls load() to release the BytesIO reference.
        """
        if not _is_allowed_url(url):
            return None
        try:
            self._rate_limit()
            full_url = url if url.startswith("http") else f"{self.base_url}/{url.lstrip('/')}"
            response = self._session.get(
                full_url, timeout=(10, 30), verify=True, stream=True,
            )
            response.raise_for_status()

            # Fast reject via Content-Length header
            cl = response.headers.get("Content-Length")
            if cl and int(cl) > MAX_DOWNLOAD_BYTES:
                response.close()
                return None

            # Stream with enforced byte limit
            chunks: list[bytes] = []
            downloaded = 0
            for chunk in response.iter_content(chunk_size=65_536):
                downloaded += len(chunk)
                if downloaded > MAX_DOWNLOAD_BYTES:
                    response.close()
                    return None
                chunks.append(chunk)

            img = Image.open(BytesIO(b"".join(chunks)))
            if img.format not in _ALLOWED_IMAGE_FORMATS:
                return None
            img.load()  # Decode pixels, release BytesIO reference
            return img
        except Exception:
            return None

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()
