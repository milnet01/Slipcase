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


class TestSelectedCoverIsNotDownloadedTwice(unittest.TestCase):
    """The preview already fetched the full-size front; selecting the result
    fetched it again (SLIP-0035)."""

    def test_a_given_front_is_used_instead_of_downloading_it(self):
        cached = object()
        ss = MagicMock()
        ss.download_back.return_value = "back"
        seen = {}
        worker = sd.DownloadWorker("ScreenScraper", "result", MagicMock(), front=cached)
        worker.image_ready.connect(lambda f, b: seen.update(front=f, back=b))
        with patch.object(sd, "_create_ss_client", lambda _c: ss):
            worker.run()
        ss.download_front.assert_not_called()
        self.assertIs(seen["front"], cached)
        self.assertEqual(seen["back"], "back")

    def test_without_a_given_front_it_is_downloaded(self):
        ss = MagicMock()
        ss.download_front.return_value = "front"
        seen = {}
        worker = sd.DownloadWorker("ScreenScraper", "result", MagicMock())
        worker.image_ready.connect(lambda f, b: seen.update(front=f))
        with patch.object(sd, "_create_ss_client", lambda _c: ss):
            worker.run()
        self.assertEqual(seen["front"], "front")

    def test_the_dialog_hands_the_cached_preview_to_the_download(self):
        dialog = MagicMock()
        dialog.results_list.currentRow.return_value = 0
        dialog._results = [("ScreenScraper", "Halo", "Xbox", "result")]
        preview = object()
        dialog._preview_cache = {0: preview}
        with patch.object(sd, "DownloadWorker") as worker_cls:
            sd.SearchDialog._download_selected(dialog)
        self.assertIs(worker_cls.call_args.kwargs.get("front"), preview)


def _animation_worker(**overrides):
    from core.case_types import CASE_TYPES
    from ui.workers import AnimationWorker
    args = dict(
        case_type=CASE_TYPES["DVD Case"], front_image=None, back_image=None,
        title="", serial="", platform="", spine_color=None, case_color=None,
        spine_left_offset=0, spine_right_offset=0, output_path="",
        output_width=64, start_angle=10, end_angle=50, frame_count=5,
        frame_delay=50, bounce=False, fmt="APNG", show_reflection=False,
        show_shadow=False, background="transparent",
    )
    args.update(overrides)
    return AnimationWorker(**args)


class TestAnimationMemory(unittest.TestCase):
    """Every frame is held in memory until the encoder runs, and nothing
    bounded that; bounce also rendered and stored each frame twice
    (SLIP-0036)."""

    def _run(self, worker, frame_size=(64, 90)):
        from PIL import Image
        import ui.workers as workers
        renders = []

        class FakeRenderer:
            def __init__(self, **kw):
                self.angle = kw["angle"]

            def render(self, **kw):
                renders.append(self.angle)
                # Distinct per angle: the APNG writer merges identical frames.
                return Image.new("RGBA", frame_size, (int(self.angle * 4), 0, 0, 255))

        seen = {"errors": []}
        worker.error.connect(seen["errors"].append)
        worker.finished_signal.connect(lambda p: seen.update(done=p))
        with patch.object(workers, "BoxRenderer", FakeRenderer):
            worker.run()
        return renders, seen

    def test_bounce_renders_each_angle_once_and_writes_the_full_loop(self):
        import tempfile
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "spin.png")
            worker = _animation_worker(bounce=True, output_path=out)
            renders, seen = self._run(worker)
            self.assertEqual(seen["errors"], [])
            self.assertEqual(len(renders), 5)
            self.assertEqual(len(set(renders)), 5)
            with Image.open(out) as img:
                self.assertEqual(img.n_frames, 8)  # 5 out, 3 back

    def test_an_animation_over_the_memory_budget_is_refused_early(self):
        import ui.workers as workers
        worker = _animation_worker(frame_count=100)
        with patch.object(workers, "MAX_ANIMATION_BYTES", 1_000_000):
            renders, seen = self._run(worker, frame_size=(64, 90))
        self.assertEqual(len(renders), 1, "it kept rendering past the estimate")
        self.assertEqual(len(seen["errors"]), 1)
        self.assertIn("memory", seen["errors"][0])
        self.assertNotIn("done", seen)


if __name__ == "__main__":
    unittest.main()
