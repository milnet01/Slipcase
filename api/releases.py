"""The only code that contacts the release host (SLIP-0031 § 4.5).

The updater asks GitHub for the newest release and downloads its files.
Those requests keep the rules every cover-art request keeps (STANDARDS.md
§ 10) -- HTTPS only, certificates verified, every redirect hop re-checked,
size and time limits -- but against their own host list. The cover-art
list, api/base.py's ALLOWED_IMAGE_DOMAINS, does not name GitHub, and this
list names nothing else, so neither path can be sent to the other's hosts.

Both calls raise ReleaseError for a network, HTTP, size, time or stop
failure, so the caller never handles a requests type.
"""

import json
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import urllib3

# _read_body holds the reply to api/base.py's MAX_DOWNLOAD_SECONDS too.
from api.base import MAX_REDIRECTS, READ_TIMEOUT, _read_body

LATEST_RELEASE_URL = "https://api.github.com/repos/milnet01/Slipcase/releases/latest"

# Exact host names, no subdomains. release-assets.githubusercontent.com is
# where a release download redirected on 2026-10-29;
# objects.githubusercontent.com served GitHub's release downloads before
# it, so a move back does not stop every update. The whole of
# githubusercontent.com would also admit content any GitHub user hosts.
ALLOWED_RELEASE_HOSTS: frozenset[str] = frozenset({
    "api.github.com",
    "github.com",
    "release-assets.githubusercontent.com",
    "objects.githubusercontent.com",
})

MAX_RELEASE_REPLY_BYTES = 1024 * 1024
MAX_UPDATE_BYTES = 512 * 1024 * 1024
MAX_SIGNATURE_BYTES = 64
# A whole download's wall-clock budget. The read timeout bounds each gap
# between reads; this bounds a trickle that never trips it.
MAX_UPDATE_SECONDS = 30 * 60

_CHUNK = 65_536
_USER_AGENT = "Slipcase updater"


class ReleaseError(Exception):
    """The release host could not be reached, or its reply was refused."""


def is_allowed_release_url(url: str) -> bool:
    """True for an HTTPS URL on exactly one of ALLOWED_RELEASE_HOSTS."""
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError:
        return False
    return (parsed.scheme == "https" and port in (None, 443)
            and (parsed.hostname or "") in ALLOWED_RELEASE_HOSTS)


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": _USER_AGENT})
    return session


def _open(session: requests.Session, url: str, headers: dict[str, str]) -> requests.Response:
    """GET `url`, following redirects by hand and re-checking every hop."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        if not is_allowed_release_url(current):
            raise ReleaseError("URL not permitted by the release allowlist")
        response = session.get(current, headers=headers, timeout=(10, READ_TIMEOUT),
                               verify=True, stream=True, allow_redirects=False)
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location", "")
            response.close()
            if not location:
                raise ReleaseError("Redirect with no Location")
            current = urljoin(current, location)
            continue
        return response
    raise ReleaseError("Too many redirects")


def fetch_latest_release() -> dict:
    """The newest published release, as GitHub's JSON describes it.

    Read under MAX_RELEASE_REPLY_BYTES and api/base.py's MAX_DOWNLOAD_SECONDS.
    """
    session = _session()
    try:
        response = _open(session, LATEST_RELEASE_URL,
                         {"Accept": "application/vnd.github+json"})
        try:
            response.raise_for_status()
            body = _read_body(response, MAX_RELEASE_REPLY_BYTES)
        finally:
            response.close()
        release = json.loads(body)
    except (requests.RequestException, urllib3.exceptions.HTTPError) as e:
        raise ReleaseError(str(e)) from None
    except ValueError as e:
        raise ReleaseError(f"Unreadable release reply: {e}") from None
    finally:
        session.close()
    if not isinstance(release, dict):
        raise ReleaseError("The release reply is not an object")
    return release


def download(url: str, dest: Path, *, max_bytes: int,
             on_progress: Callable[[int, int], None] | None = None,
             should_stop: Callable[[], bool] | None = None) -> None:
    """Stream `url` into `dest` under `max_bytes` and MAX_UPDATE_SECONDS.

    `on_progress(received, total)` gets the Content-Length as `total`, or 0
    when there is none. `should_stop()` is asked after every read. A body
    shorter than its Content-Length is an error, so a dropped connection is
    not later mistaken for tampering. Any failure deletes `dest`. Raises
    ReleaseError, or OSError for a failure writing `dest`.
    """
    session = _session()
    try:
        # identity: the bytes counted, capped and compared with the
        # Content-Length are the bytes written, with nothing decoded between.
        response = _open(session, url, {"Accept-Encoding": "identity"})
        try:
            response.raise_for_status()
            _stream(response, dest, max_bytes, on_progress, should_stop)
        finally:
            response.close()
    except BaseException as e:
        Path(dest).unlink(missing_ok=True)
        if isinstance(e, (requests.RequestException, urllib3.exceptions.HTTPError)):
            raise ReleaseError(str(e)) from None
        raise
    finally:
        session.close()


def _stream(response: requests.Response, dest: Path, max_bytes: int,
            on_progress: Callable[[int, int], None] | None,
            should_stop: Callable[[], bool] | None) -> None:
    declared = response.headers.get("Content-Length", "")
    total = int(declared) if declared.isascii() and declared.isdigit() else 0
    if total > max_bytes:
        raise ReleaseError("Download larger than the size limit")
    deadline = time.monotonic() + MAX_UPDATE_SECONDS
    received = 0
    with open(dest, "wb") as out:
        while True:
            # read1(), as api/base.py's _read_body explains: it returns as
            # soon as any bytes arrive, so the checks below run on a trickle.
            chunk = response.raw.read1(_CHUNK, decode_content=False)
            if not chunk:
                break
            received += len(chunk)
            if received > max_bytes:
                raise ReleaseError("Download larger than the size limit")
            if time.monotonic() > deadline:
                raise ReleaseError("Download took longer than the time limit")
            if should_stop is not None and should_stop():
                raise ReleaseError("Download stopped")
            out.write(chunk)
            if on_progress is not None:
                on_progress(received, total)
    if received < total:
        raise ReleaseError("The download ended early; the connection may have dropped")
