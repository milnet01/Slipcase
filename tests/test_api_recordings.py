"""The search clients parse real, recorded ScreenScraper and TheGamesDB replies.

Every other API test builds its reply by hand, so it proves the parser
matches what its author believed the services send. These replies were
recorded from the live services on 2026-09-29 (SLIP-0088), which is the
evidence that belief was right on that date.

The recordings are trimmed and scrubbed: three ScreenScraper games with only
the media types the parser reads (plus one it ignores), the account block
dropped, and every credential in every URL replaced with REDACTED. The last
class here keeps a future re-recording from committing a real one.
"""

import json
import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from api.screenscraper import ScreenScraperAPI
from api.thegamesdb import TheGamesDBAPI

FIXTURES = Path(__file__).parent / "fixtures"
SS_RECORDING = FIXTURES / "screenscraper_search_crash_bandicoot.json"
TGDB_RECORDING = FIXTURES / "thegamesdb_search_crash_bandicoot.json"


def _replay(path):
    response = requests.Response()
    response.status_code = 200
    response._content = path.read_bytes()
    response.encoding = "utf-8"
    return response


class TestScreenScraperRecording(unittest.TestCase):

    def setUp(self):
        client = ScreenScraperAPI("dev", "devpw", "user", "pw")
        client.min_request_interval = 0
        with patch.object(client._session, "get", return_value=_replay(SS_RECORDING)):
            self.results = client.search_game("Crash Bandicoot")
        client.close()
        self.by_id = {r.game_id: r for r in self.results}

    def test_every_recorded_game_is_parsed(self):
        self.assertEqual(sorted(self.by_id), [3882, 3946, 542207])

    def test_the_us_name_wins_over_the_ss_name_listed_first(self):
        self.assertEqual(self.by_id[3882].name, "Crash Bandicoot : The Huge Adventure")
        self.assertEqual(self.by_id[3882].platform, "Game Boy Advance")

    def test_the_us_cover_wins_over_the_eu_cover_listed_first(self):
        game = self.by_id[3882]
        self.assertTrue(game.front_url.endswith("media=box-2D(us)"))
        self.assertTrue(game.back_url.endswith("media=box-2D-back(us)"))
        self.assertTrue(game.box3d_url.endswith("media=box-3D(us)"))
        self.assertTrue(game.wheel_url.endswith("media=wheel(us)"))

    def test_a_game_with_no_media_has_no_urls(self):
        game = self.by_id[542207]
        self.assertEqual(game.name, "Crash Bandicoot")
        self.assertIsNone(game.front_url)
        self.assertIsNone(game.box3d_url)


class TestTheGamesDBRecording(unittest.TestCase):

    def setUp(self):
        client = TheGamesDBAPI("key")
        client.min_request_interval = 0
        with patch.object(client._session, "get", return_value=_replay(TGDB_RECORDING)):
            self.results = client.search_game("Crash Bandicoot")
        client.close()
        self.by_id = {r.game_id: r for r in self.results}

    def test_every_recorded_game_is_parsed(self):
        self.assertEqual(len(self.results), 20)

    def test_cover_urls_are_built_from_the_reply_base_url(self):
        game = self.by_id[1006]
        self.assertEqual(game.release_date, "1996-09-09")
        self.assertEqual(
            game.front_url,
            "https://cdn.thegamesdb.net/images/original/boxart/front/1006-1.jpg",
        )
        self.assertEqual(
            game.back_url,
            "https://cdn.thegamesdb.net/images/original/boxart/back/1006-1.jpg",
        )

    def test_a_game_with_no_boxart_has_no_urls(self):
        self.assertIsNone(self.by_id[138013].front_url)
        self.assertIsNone(self.by_id[138013].back_url)


class TestRecordingsCarryNoCredentials(unittest.TestCase):
    """The repository is public. A re-recording must be scrubbed first."""

    CREDENTIAL = re.compile(
        r"(devid|devpassword|ssid|sspassword|apikey|api_key)=(?!REDACTED\b)",
        re.IGNORECASE,
    )

    def test_every_credential_parameter_is_redacted(self):
        for path in FIXTURES.glob("*.json"):
            with self.subTest(recording=path.name):
                self.assertIsNone(self.CREDENTIAL.search(path.read_text("utf-8")))

    def test_the_screenscraper_account_block_is_dropped(self):
        reply = json.loads(SS_RECORDING.read_text("utf-8"))
        self.assertNotIn("ssuser", reply["response"])


if __name__ == "__main__":
    unittest.main()
