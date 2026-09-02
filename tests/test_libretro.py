"""The libretro thumbnail lookup.

A libretro thumbnail is named after the full No-Intro ROM name, which carries
a region tag -- "Super Mario World (USA).png". Searching for the title a
person actually types therefore found nothing at all, on every system, until
2026-09-02 (SLIP-0089). The unit tests below lock the candidate order without
touching the network; TestLibretroLive runs the real request and is opt-in,
because a test that needs the internet cannot gate a commit.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.libretro import LibretroThumbnails

SNES = "Nintendo - Super Nintendo Entertainment System"


class TestCandidateUrls(unittest.TestCase):
    """The order is the contract: exact name first, then region tags."""

    def setUp(self):
        self.client = LibretroThumbnails()

    def test_the_exact_name_is_tried_first(self):
        first = self.client.candidate_urls(SNES, "Super Mario World")[0]
        self.assertEqual(first, self.client.get_boxart_url(SNES, "Super Mario World"))

    def test_the_common_region_tags_follow(self):
        urls = self.client.candidate_urls(SNES, "Super Mario World")
        self.assertIn("Super%20Mario%20World%20%28USA%29.png", urls[1])
        self.assertEqual(len(urls), len(self.client.REGION_SUFFIXES))

    def test_a_tagged_candidate_is_still_url_encoded(self):
        # The ampersand is sanitised to _ by libretro's own filename rule, and
        # the space and parentheses still have to survive as percent escapes.
        urls = self.client.candidate_urls("Sony - PlayStation 2", "Ratchet & Clank")
        self.assertIn("Ratchet%20_%20Clank%20%28USA%29.png", urls[1])


class TestDownloadStopsAtTheFirstHit(unittest.TestCase):

    def test_a_later_candidate_is_not_requested_once_one_hits(self):
        client = LibretroThumbnails()
        image = MagicMock()
        with patch.object(client, "download_image", side_effect=[None, image]) as dl:
            self.assertIs(client.download_boxart(SNES, "Super Mario World"), image)
        self.assertEqual(dl.call_count, 2)

    def test_every_candidate_is_tried_before_giving_up(self):
        client = LibretroThumbnails()
        misses = [None] * len(client.REGION_SUFFIXES)
        with patch.object(client, "download_image", side_effect=misses) as dl:
            self.assertIsNone(client.download_boxart(SNES, "Zzz Not A Real Game"))
        self.assertEqual(dl.call_count, len(client.REGION_SUFFIXES))


@unittest.skipUnless(
    os.environ.get("SLIPCASE_LIVE_API"),
    "live API check: set SLIPCASE_LIVE_API=1 to run",
)
class TestLibretroLive(unittest.TestCase):
    """Contacts thumbnails.libretro.com. Opt-in, and never part of the gate.

    This is the check that found the defect: no fixture can tell you the
    server has stopped answering for the names the app builds.
    """

    def test_titles_a_person_would_type_resolve(self):
        client = LibretroThumbnails()
        for system, title in [
            (SNES, "Super Mario World"),
            ("Sega - Mega Drive - Genesis", "Sonic The Hedgehog"),
            ("Sony - PlayStation 2", "Ratchet & Clank"),
        ]:
            with self.subTest(title=title):
                self.assertIsNotNone(client.download_boxart(system, title))

    def test_an_invented_title_still_misses(self):
        client = LibretroThumbnails()
        self.assertIsNone(client.download_boxart(SNES, "Zzz Not A Real Game"))


if __name__ == "__main__":
    unittest.main()
