"""SearchWorker always finishes, and says when nothing was asked.

Two defects from the 2026-09-01 review. The client construction and the two
emits sat outside every try, so an exception there left finished_signal
unsent: the progress bar stayed visible and Search stayed disabled until the
dialog was closed (SLIP-0052). And with no credentials and a platform
libretro does not carry, no source ran at all and the user was told the query
found nothing, which blames the search term for a missing configuration
(SLIP-0038).

Nothing here touches the network or needs a running QApplication -- run() is
called directly and the clients are replaced.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ui.search_dialog as sd
from ui.animation_dialog import frames_in_file


def _drive(platform, ss=None, tgdb=None, libretro=None, ss_factory=None):
    """Run one search with every client replaced, and collect what it emitted."""
    seen = {"errors": []}
    worker = sd.SearchWorker("Halo", platform, MagicMock())
    worker.results_ready.connect(
        lambda results, count: seen.update(results=results, sources=count)
    )
    worker.finished_signal.connect(lambda: seen.update(finished=True))
    worker.error.connect(seen["errors"].append)

    ss = ss or MagicMock(is_configured=False)
    tgdb = tgdb or MagicMock(is_configured=False)
    libretro = libretro or MagicMock(download_boxart=MagicMock(return_value=None))

    with patch.object(sd, "_create_ss_client", ss_factory or (lambda _c: ss)), \
            patch.object(sd, "_create_tgdb_client", lambda _c: tgdb), \
            patch.object(sd, "LibretroThumbnails", lambda: libretro):
        worker.run()
    return seen


class TestSearchAlwaysFinishes(unittest.TestCase):

    def test_a_client_failing_mid_search_still_finishes(self):
        ss = MagicMock(is_configured=True)
        ss.search_game.side_effect = RuntimeError("boom")
        seen = _drive("PS2", ss=ss)
        self.assertTrue(seen.get("finished"), "finished_signal was never emitted")
        self.assertIn("ScreenScraper: boom", seen["errors"])

    def test_a_client_failing_to_construct_still_finishes(self):
        # The regression: this raised before any try block existed.
        def explode(_config):
            raise RuntimeError("no client for you")

        seen = _drive("PS2", ss_factory=explode)
        self.assertTrue(seen.get("finished"), "finished_signal was never emitted")
        self.assertEqual(seen["results"], [])
        self.assertTrue(any("no client for you" in e for e in seen["errors"]))


class TestNoSourcesQueried(unittest.TestCase):

    def test_nothing_configured_and_no_libretro_platform_queries_nothing(self):
        # PS5 is in ALL_PLATFORMS and not in LIBRETRO_SYSTEMS.
        self.assertNotIn("PS5", sd.LIBRETRO_SYSTEMS)
        seen = _drive("PS5")
        self.assertEqual(seen["sources"], 0)
        self.assertEqual(seen["results"], [])

    def test_a_libretro_platform_is_queried_even_with_no_credentials(self):
        seen = _drive("PS2")
        self.assertEqual(seen["sources"], 1)

    def test_a_configured_client_counts_as_queried(self):
        seen = _drive("PS5", ss=MagicMock(is_configured=True, **{"search_game.return_value": []}))
        self.assertEqual(seen["sources"], 1)


if __name__ == "__main__":
    unittest.main()


class TestFrameTotal(unittest.TestCase):
    """Bounce nearly doubles the frames written (SLIP-0072).

    The dialog's label and the export's progress maximum now come from this
    one function, so they cannot disagree.
    """

    def test_without_bounce_the_count_is_what_was_asked_for(self):
        self.assertEqual(frames_in_file(24, False), 24)

    def test_bounce_replays_without_repeating_either_endpoint(self):
        self.assertEqual(frames_in_file(24, True), 46)
        self.assertEqual(frames_in_file(120, True), 238)

    def test_a_sweep_too_short_to_bounce_is_left_alone(self):
        self.assertEqual(frames_in_file(2, True), 2)
