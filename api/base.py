"""Base API client with rate limiting and shared HTTP session."""

import re
import threading
import time
from io import BytesIO
from urllib.parse import urljoin, urlparse

import requests
from PIL import Image

# Maximum image download size (50 MB) to prevent memory exhaustion
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024

# Decompression-bomb ceiling, in pixels. Well above any real cover scan
# (~4000 x 10000) and far below a decode that would exhaust memory.
#
# This is the ONE definition; main.py imports it rather than repeating the
# number. It is applied at import here so the download path -- the only one
# that ingests untrusted bytes -- is protected even when main.py was never
# executed, as in a test, a spawned batch child, or library use.
#
# NOTE: Pillow only *warns* at this value and raises above 2x it, so
# download_image() also checks the pixel count explicitly before decoding.
MAX_IMAGE_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

# Maximum redirect hops to follow. Each hop is re-validated against the
# allowlist, so this bounds the work rather than the trust.
MAX_REDIRECTS = 5

# Allowed root domains for image downloads (subdomains are also allowed)
ALLOWED_IMAGE_DOMAINS: set[str] = {
    "screenscraper.fr",
    "thegamesdb.net",
    "thumbnails.libretro.com",
}

# Wall-clock budget for one download, in seconds. timeout=(10, 30) bounds the
# gap between reads, not the total: a server sending one byte every 29 seconds
# holds a worker thread and a connection open indefinitely while never
# reaching MAX_DOWNLOAD_BYTES, so neither the size cap nor the timeout ever
# fires (SLIP-0065).
MAX_DOWNLOAD_SECONDS = 60.0

# Accepted image formats. The list exists to keep the decoder attack surface
# small: every format here is one more Pillow decoder reachable from a
# remote response. BMP and GIF were dropped on 2026-09-02 (SLIP-0066)
# because cover art from all three services is PNG, JPEG or WEBP, and
# nothing recorded a use for the other two. Adding a format back is a
# deliberate decision, not a convenience.
_ALLOWED_IMAGE_FORMATS: frozenset[str] = frozenset({
    "PNG", "JPEG", "WEBP",
})

# Last request time per API host, shared across client INSTANCES.
#
# Each worker constructs its own client, so per-instance state reset the
# interval to zero every time and the limit only ever held within one worker.
# Sharing the state here keeps rate limiting correct while leaving each client
# free to close its own session, as STANDARDS.md § 12 requires.
_last_request_lock = threading.Lock()
_last_request_by_host: dict[str, float] = {}

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
        self._session = requests.Session()
        self._session.max_redirects = MAX_REDIRECTS
        self._session.headers.update({
            "User-Agent": "Slipcase/1.0 (Desktop cover art renderer)",
        })

    def _rate_limit(self) -> None:
        """Enforce minimum interval between requests.

        Uses a monotonic clock: a wall-clock step (NTP correction, DST) could
        otherwise make `elapsed` negative and park the caller for the skew.
        """
        key = self.base_url or self.__class__.__name__
        with _last_request_lock:
            last = _last_request_by_host.get(key, float("-inf"))
            now = time.monotonic()
            wait = self.min_request_interval - (now - last)
            # Claim the slot before releasing the lock, so two threads cannot
            # both decide they may go now.
            _last_request_by_host[key] = now + max(0.0, wait)
        if wait > 0:
            time.sleep(wait)

    def get(
        self,
        url: str,
        params: dict | list[tuple[str, str]] | None = None,
        **kwargs,
    ) -> requests.Response:
        """Make a rate-limited GET request.

        Errors are sanitized to strip credential values before propagating.
        """
        full_url = f"{self.base_url}/{url.lstrip('/')}" if not url.startswith("http") else url
        # The same check download_image() runs. startswith("http") was the only
        # test here, so "TLS only" on the JSON path rested entirely on the
        # hardcoded API_URL constants being right -- true today, and enforced
        # by nothing (SLIP-0064). All three API hosts are subdomains of, or
        # exactly, an entry in ALLOWED_IMAGE_DOMAINS, so no second list is
        # needed.
        if not _is_allowed_url(full_url):
            raise requests.RequestException("URL not permitted by allowlist")
        self._rate_limit()
        try:
            response = self._session.get(
                full_url, params=params, timeout=(10, 30), verify=True, **kwargs
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise requests.RequestException(_sanitize_message(str(e))) from None
        return response

    def get_json(
        self, url: str, params: dict | list[tuple[str, str]] | None = None
    ) -> dict:
        """GET request returning parsed JSON."""
        return self.get(url, params=params).json()

    def _get_validated(self, url: str) -> requests.Response:
        """Stream a GET, re-validating the allowlist on every redirect hop.

        `requests` follows redirects itself, which would let a 302 from an
        allowed host fetch the body from an arbitrary one -- and an
        https -> http hop would silently drop TLS. Both are checked here, so
        the URL that is actually fetched is always an allowed HTTPS URL.
        """
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            if not _is_allowed_url(current):
                raise requests.RequestException("URL not permitted by allowlist")
            self._rate_limit()
            response = self._session.get(
                current, timeout=(10, 30), verify=True, stream=True,
                allow_redirects=False,
            )
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location", "")
                response.close()
                if not location:
                    raise requests.RequestException("Redirect with no Location")
                current = urljoin(current, location)
                continue
            return response
        raise requests.RequestException("Too many redirects")

    def download_image(self, url: str) -> Image.Image | None:
        """Download an image from a URL and return as PIL Image.

        Validates the URL against allowed domains on every redirect hop,
        enforces a size limit via streaming (never buffers more than the
        limit), rejects an oversized pixel count before decoding, restricts
        accepted image formats, and calls load() to release the BytesIO
        reference.
        """
        if not _is_allowed_url(url):
            return None
        try:
            response = self._get_validated(url)
            response.raise_for_status()

            # Fast reject via Content-Length header
            cl = response.headers.get("Content-Length")
            if cl and int(cl) > MAX_DOWNLOAD_BYTES:
                response.close()
                return None

            # Stream with enforced byte limit
            chunks: list[bytes] = []
            downloaded = 0
            deadline = time.monotonic() + MAX_DOWNLOAD_SECONDS
            for chunk in response.iter_content(chunk_size=65_536):
                downloaded += len(chunk)
                if downloaded > MAX_DOWNLOAD_BYTES:
                    response.close()
                    return None
                if time.monotonic() > deadline:
                    # A trickle never trips the size cap or the read timeout.
                    response.close()
                    return None
                chunks.append(chunk)

            img = Image.open(BytesIO(b"".join(chunks)))
            if img.format not in _ALLOWED_IMAGE_FORMATS:
                return None
            # Reject a decompression bomb BEFORE decoding. Pillow only warns
            # at MAX_IMAGE_PIXELS and raises above 2x it, so a header
            # declaring a huge canvas would otherwise allocate on load().
            if img.size[0] * img.size[1] > MAX_IMAGE_PIXELS:
                return None
            img.load()  # Decode pixels, release BytesIO reference
            return img
        except Exception:
            return None

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()
