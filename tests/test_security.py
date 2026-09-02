"""Regression tests for the security invariants CLAUDE.md declares mandatory.

Every test here locks a rule that a refactor could silently remove: the URL
allowlist, credential scrubbing, the download size cap and the
decompression-bomb limit. These are pure functions with no network in them.

Covers ROADMAP SLIP-0021.
"""

import os
import sys
import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from PIL import Image

from api import base
from api.base import (
    ALLOWED_IMAGE_DOMAINS,
    MAX_DOWNLOAD_BYTES,
    APIClient,
    _ALLOWED_IMAGE_FORMATS,
    _is_allowed_url,
    _sanitize_message,
)


class TestUrlAllowlist(unittest.TestCase):
    """CLAUDE.md: image downloads are restricted to known domains."""

    def test_allowed_hosts_accepted(self):
        for host in ALLOWED_IMAGE_DOMAINS:
            self.assertTrue(_is_allowed_url(f"https://{host}/art.png"), host)

    def test_subdomains_accepted(self):
        self.assertTrue(_is_allowed_url("https://cdn.thegamesdb.net/a.jpg"))

    def test_userinfo_cannot_spoof_host(self):
        # The host is what follows the LAST '@'; a naive split would read
        # these as an allowed domain.
        for url in (
            "https://screenscraper.fr@evil.com/x.png",
            "https://screenscraper.fr:@evil.com/x.png",
            "https://screenscraper.fr%40evil.com@evil.com/x.png",
        ):
            self.assertFalse(_is_allowed_url(url), url)

    def test_suffix_and_prefix_cannot_spoof_host(self):
        for url in (
            "https://evil-screenscraper.fr/x.png",
            "https://screenscraper.fr.evil.com/x.png",
            "https://notthegamesdb.net/x.png",
        ):
            self.assertFalse(_is_allowed_url(url), url)

    def test_non_https_rejected(self):
        for url in (
            "http://screenscraper.fr/x.png",
            "file:///etc/passwd",
            "ftp://screenscraper.fr/x.png",
        ):
            self.assertFalse(_is_allowed_url(url), url)


class TestRedirectValidation(unittest.TestCase):
    """A redirect must not escape the allowlist or downgrade TLS.

    The allowlist is worthless if it is checked on the URL requested rather
    than the URL actually fetched.
    """

    def _client(self):
        return APIClient(base_url="https://screenscraper.fr")

    def test_redirects_are_not_followed_automatically(self):
        client = self._client()
        response = MagicMock(is_redirect=False, is_permanent_redirect=False)
        with patch.object(client._session, "get", return_value=response) as get:
            client._get_validated("https://screenscraper.fr/a.png")
        self.assertIs(get.call_args.kwargs["allow_redirects"], False)

    def test_redirect_to_disallowed_host_is_refused(self):
        client = self._client()
        redirect = MagicMock(
            is_redirect=True,
            is_permanent_redirect=False,
            headers={"Location": "https://evil.example/payload.png"},
        )
        with patch.object(client._session, "get", return_value=redirect):
            with self.assertRaises(requests.RequestException):
                client._get_validated("https://screenscraper.fr/a.png")

    def test_redirect_to_localhost_is_refused(self):
        client = self._client()
        redirect = MagicMock(
            is_redirect=True,
            is_permanent_redirect=False,
            headers={"Location": "http://127.0.0.1:8080/"},
        )
        with patch.object(client._session, "get", return_value=redirect):
            with self.assertRaises(requests.RequestException):
                client._get_validated("https://screenscraper.fr/a.png")

    def test_tls_downgrade_redirect_is_refused(self):
        client = self._client()
        redirect = MagicMock(
            is_redirect=True,
            is_permanent_redirect=False,
            headers={"Location": "http://screenscraper.fr/a.png"},
        )
        with patch.object(client._session, "get", return_value=redirect):
            with self.assertRaises(requests.RequestException):
                client._get_validated("https://screenscraper.fr/a.png")

    def test_redirect_chain_is_bounded(self):
        client = self._client()
        redirect = MagicMock(
            is_redirect=True,
            is_permanent_redirect=False,
            headers={"Location": "https://screenscraper.fr/loop.png"},
        )
        with patch.object(client._session, "get", return_value=redirect):
            with self.assertRaises(requests.RequestException):
                client._get_validated("https://screenscraper.fr/a.png")


class TestCredentialScrubbing(unittest.TestCase):
    """CLAUDE.md: API errors strip passwords/keys before display."""

    def test_every_credential_key_is_scrubbed(self):
        for key in (
            "devpassword", "devid", "sspassword", "ssid", "apikey",
            "api_key", "password",
        ):
            msg = f"failed for https://api.test/x?{key}=hunter2&other=1"
            scrubbed = _sanitize_message(msg)
            self.assertNotIn("hunter2", scrubbed, key)
            self.assertIn(f"{key}=***", scrubbed, key)

    def test_scrubbing_is_case_insensitive(self):
        self.assertNotIn("hunter2", _sanitize_message("?PassWord=hunter2"))

    def test_longer_key_is_not_shadowed_by_a_shorter_one(self):
        # 'devpassword' must not be matched as 'password' with a 'dev' prefix
        # left behind carrying the value.
        scrubbed = _sanitize_message("?devpassword=hunter2")
        self.assertNotIn("hunter2", scrubbed)

    def test_non_credential_values_survive(self):
        self.assertIn("recherche=Halo", _sanitize_message("?recherche=Halo"))


class TestDownloadLimits(unittest.TestCase):
    """CLAUDE.md: 50MB max per download, and a decompression-bomb ceiling."""

    def test_limit_is_fifty_megabytes(self):
        self.assertEqual(MAX_DOWNLOAD_BYTES, 50 * 1024 * 1024)

    def test_disallowed_url_never_reaches_the_network(self):
        client = APIClient(base_url="https://screenscraper.fr")
        with patch.object(client._session, "get") as get:
            self.assertIsNone(client.download_image("https://evil.example/x.png"))
        get.assert_not_called()

    def test_oversized_content_length_is_rejected(self):
        client = APIClient(base_url="https://screenscraper.fr")
        response = MagicMock(
            is_redirect=False,
            is_permanent_redirect=False,
            headers={"Content-Length": str(MAX_DOWNLOAD_BYTES + 1)},
        )
        response.raise_for_status.return_value = None
        with patch.object(client._session, "get", return_value=response):
            self.assertIsNone(
                client.download_image("https://screenscraper.fr/big.png")
            )

    def test_streaming_stops_past_the_limit_without_content_length(self):
        client = APIClient(base_url="https://screenscraper.fr")
        chunk = b"\x00" * 65_536
        chunks = [chunk] * ((MAX_DOWNLOAD_BYTES // len(chunk)) + 2)
        response = MagicMock(
            is_redirect=False, is_permanent_redirect=False, headers={},
        )
        response.raise_for_status.return_value = None
        response.iter_content.return_value = iter(chunks)
        with patch.object(client._session, "get", return_value=response):
            self.assertIsNone(
                client.download_image("https://screenscraper.fr/big.png")
            )

    def test_bomb_limit_is_below_pillow_hard_error(self):
        # Pillow only WARNS at MAX_IMAGE_PIXELS and raises above 2x it, so a
        # value at or above its own default is a relaxation, not a control.
        default = int(1024 * 1024 * 1024 // 4 // 3)
        self.assertLess(Image.MAX_IMAGE_PIXELS, default)

    def test_oversized_pixel_count_is_rejected_before_decode(self):
        client = APIClient(base_url="https://screenscraper.fr")
        response = MagicMock(
            is_redirect=False, is_permanent_redirect=False, headers={},
        )
        response.raise_for_status.return_value = None
        response.iter_content.return_value = iter([b"fake-png-bytes"])
        bomb = MagicMock(format="PNG", size=(60_000, 60_000))
        with patch.object(client._session, "get", return_value=response), \
                patch("api.base.Image.open", return_value=bomb):
            self.assertIsNone(
                client.download_image("https://screenscraper.fr/bomb.png")
            )
        bomb.load.assert_not_called()

    def test_disallowed_image_format_is_rejected(self):
        client = APIClient(base_url="https://screenscraper.fr")
        response = MagicMock(
            is_redirect=False, is_permanent_redirect=False, headers={},
        )
        response.raise_for_status.return_value = None
        response.iter_content.return_value = iter([b"bytes"])
        svg = MagicMock(format="SVG", size=(10, 10))
        with patch.object(client._session, "get", return_value=response), \
                patch("api.base.Image.open", return_value=svg):
            self.assertIsNone(
                client.download_image("https://screenscraper.fr/x.svg")
            )


class TestAcceptedImageFormats(unittest.TestCase):
    """The set of decoders a remote response can reach is a deliberate choice.

    SLIP-0066 dropped BMP and GIF: cover art from all three services is PNG,
    JPEG or WEBP, and nothing recorded a use for the other two. This test
    fails if a format is added back, which is the intent -- widening the set
    widens the attack surface and should be an explicit decision.
    """

    def test_only_the_three_cover_art_formats_are_accepted(self):
        self.assertEqual(_ALLOWED_IMAGE_FORMATS, frozenset({"PNG", "JPEG", "WEBP"}))

    def test_bmp_and_gif_are_rejected_by_the_download_path(self):
        client = APIClient(base_url="https://screenscraper.fr")
        for fmt in ("BMP", "GIF"):
            with self.subTest(image_format=fmt):
                response = MagicMock(
                    is_redirect=False, is_permanent_redirect=False, headers={},
                )
                response.raise_for_status.return_value = None
                response.iter_content.return_value = iter([b"bytes"])
                img = MagicMock(format=fmt, size=(10, 10))
                with patch.object(client._session, "get", return_value=response), \
                        patch("api.base.Image.open", return_value=img):
                    self.assertIsNone(
                        client.download_image("https://screenscraper.fr/x.img")
                    )


class TestTlsEnforced(unittest.TestCase):
    """CLAUDE.md: all API requests use HTTPS with verify=True."""

    def test_verify_is_always_true(self):
        client = APIClient(base_url="https://screenscraper.fr")
        response = MagicMock(is_redirect=False, is_permanent_redirect=False)
        response.raise_for_status.return_value = None
        with patch.object(client._session, "get", return_value=response) as get:
            client.get("x.php")
        self.assertIs(get.call_args.kwargs["verify"], True)


if __name__ == "__main__":
    unittest.main()


class TestJsonRequestsAreValidated(unittest.TestCase):
    """The allowlist covers the JSON path, not only image downloads.

    get() tested only startswith("http"), so "TLS only" on that path rested
    entirely on the hardcoded API_URL constants being right -- true, and
    enforced by nothing (SLIP-0064).

    Each refusal test hands the session a response it would happily return,
    so the request CAN succeed if the guard is missing. Without that, these
    passed on a DNS failure and proved nothing.
    """

    @staticmethod
    def _willing_session(client):
        response = MagicMock()
        response.raise_for_status.return_value = None
        return patch.object(client._session, "get", return_value=response)

    def test_the_three_real_api_hosts_are_permitted(self):
        for url in (
            "https://api.screenscraper.fr/api2/jeuInfos.php",
            "https://api.thegamesdb.net/v1/Games/ByGameName",
            "https://thumbnails.libretro.com/x/Named_Boxarts/y.png",
        ):
            with self.subTest(url=url):
                self.assertTrue(_is_allowed_url(url))

    def test_a_permitted_host_still_gets_through(self):
        client = APIClient(base_url="https://api.thegamesdb.net/v1", min_request_interval=0)
        with self._willing_session(client) as session_get:
            client.get("Games/ByGameName")
        session_get.assert_called_once()

    def test_a_plain_http_api_url_is_refused_without_being_requested(self):
        client = APIClient(base_url="http://api.screenscraper.fr/api2", min_request_interval=0)
        with self._willing_session(client) as session_get:
            with self.assertRaises(requests.RequestException) as caught:
                client.get("jeuInfos.php")
        self.assertIn("not permitted", str(caught.exception))
        session_get.assert_not_called()

    def test_a_base_url_off_the_allowlist_is_refused_without_being_requested(self):
        client = APIClient(base_url="https://evil.example.com/api", min_request_interval=0)
        with self._willing_session(client) as session_get:
            with self.assertRaises(requests.RequestException):
                client.get("jeuInfos.php")
        session_get.assert_not_called()

    def test_an_absolute_url_off_the_allowlist_is_refused(self):
        client = APIClient(base_url="https://api.thegamesdb.net/v1", min_request_interval=0)
        with self._willing_session(client) as session_get:
            with self.assertRaises(requests.RequestException):
                client.get("https://evil.example.com/steal")
        session_get.assert_not_called()


def _png_bytes(size=(8, 8)):
    """A real PNG, so a download that is NOT cut short succeeds."""
    buf = BytesIO()
    Image.new("RGB", size, (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


class TestDownloadDeadline(unittest.TestCase):
    """A trickling server trips neither the size cap nor the read timeout.

    timeout=(10, 30) bounds the gap between reads, not the total, so one byte
    every 29 seconds held a worker thread and a connection open indefinitely
    (SLIP-0065).

    The payload is a real PNG and well under MAX_DOWNLOAD_BYTES, so the only
    thing that can return None is the deadline. download_image() swallows
    every exception, so a test using junk bytes would pass whether the
    deadline fired or the decode simply failed.
    """

    def _response(self):
        response = MagicMock(
            is_redirect=False, is_permanent_redirect=False, headers={},
        )
        response.raise_for_status.return_value = None
        payload = _png_bytes()
        response.iter_content.return_value = iter(
            [payload[i:i + 4] for i in range(0, len(payload), 4)]
        )
        return response

    def test_a_slow_trickle_is_abandoned(self):
        client = APIClient(base_url="https://screenscraper.fr", min_request_interval=0)
        # A deadline already in the past, rather than a faked clock: the rate
        # limiter reads the same monotonic clock, and patching it globally
        # made that compute a multi-day sleep.
        with patch.object(client._session, "get", return_value=self._response()), \
                patch.object(base, "MAX_DOWNLOAD_SECONDS", -1.0):
            self.assertIsNone(
                client.download_image("https://screenscraper.fr/slow.png")
            )

    def test_the_same_download_succeeds_within_the_deadline(self):
        client = APIClient(base_url="https://screenscraper.fr", min_request_interval=0)
        with patch.object(client._session, "get", return_value=self._response()):
            image = client.download_image("https://screenscraper.fr/ok.png")
        self.assertIsNotNone(image, "the payload itself must be downloadable")
        self.assertEqual(image.size, (8, 8))
