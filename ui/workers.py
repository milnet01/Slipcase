"""Background worker threads for rendering and batch processing."""

import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image
from PyQt6.QtCore import QThread, pyqtSignal

from core.box_file import box_paths, write_box_file
from core.box_model import build_box_model
from core.case_types import CaseType
from core.renderer import BoxRenderer, visible_width_mm

# Most memory an animation's frames may take. Every frame is held until the
# encoder runs, so 120 frames at 2048px wide came to several gigabytes with
# nothing to stop it (SLIP-0036). The estimate is taken from the first frame.
MAX_ANIMATION_BYTES = 1024 ** 3


# ---------------------------------------------------------------------------
# Top-level helper for ProcessPoolExecutor (must be picklable)
# ---------------------------------------------------------------------------

def _stem_taken(output_dir: str, stem: str, source: str, given: set[str]) -> bool:
    png = os.path.join(output_dir, f"{stem}.png")
    return (stem.casefold() in given or os.path.abspath(png) == source
            or any(os.path.exists(p) for p in [png, *box_paths(output_dir, stem)]))


def pick_output_stems(file_paths: list[str], output_dir: str) -> list[str]:
    """Pick each batch file's output stem, before any render starts.

    A stem is taken only when neither its PNG nor any of its box-file paths
    exists, and no earlier file in the batch was given it. Covers are
    generically named, so `A/cover.png` and `B/cover.png` both mapped to
    `<out>/cover.png` and the second silently won. And if the user picked the
    source folder as the output folder, a `.png` source was overwritten by
    its own render. Stems are compared case-blind, as Windows names are.
    """
    given: set[str] = set()
    stems = []
    for fp in file_paths:
        name = Path(fp).stem
        source = os.path.abspath(fp)
        stem, n = name, 1
        while _stem_taken(output_dir, stem, source, given):
            stem = f"{name} ({n})"
            n += 1
        given.add(stem.casefold())
        stems.append(stem)
    return stems


def _render_single_image(args: tuple) -> str:
    """Render one batch file to `<stem>.png`, and its box file when asked.

    Runs in a worker process, or in the batch thread when rendering
    sequentially. Returns the output stem.
    """
    fp, output_dir, stem, case_type, renderer_kwargs, compress_level, box_file = args
    # Imports happen inside the child process (spawn context)
    from PIL import Image as _Img
    from core.renderer import BoxRenderer as _BR
    from core.png_utils import save_optimized_png as _save

    name = Path(fp).stem
    renderer = _BR(case_type=case_type, **renderer_kwargs)
    img = _Img.open(fp)
    img.load()
    result = renderer.render(front_image=img, title=name)
    _save(result, os.path.join(output_dir, f"{stem}.png"), compress_level=compress_level)
    del result
    if box_file:
        try:
            model = build_box_model(
                img, None, case_type, title=name, serial="", platform="",
                spine_color=None, case_color=None, spine_left_offset=0,
                spine_right_offset=0, full_cover=None,
                show_texture=renderer.show_texture,
            )
            write_box_file(model, output_dir, stem, compress_level)
        except Exception as e:
            raise RuntimeError(f"PNG saved, but the box file was not: {e}") from e
        del model
    del img
    return stem


class RenderWorker(QThread):
    """Background thread for rendering the 3D box and building its model."""
    rendered = pyqtSignal(object)  # PIL Image
    model_ready = pyqtSignal(object)  # BoxModel of the same render
    error = pyqtSignal(str)

    def __init__(self, renderer: BoxRenderer, front: Image.Image,
                 back: Image.Image | None, title: str, serial: str,
                 platform: str, spine_color: tuple[int, int, int] | None,
                 case_color: tuple[int, int, int] | None = None,
                 spine_left_offset: int = 0, spine_right_offset: int = 0,
                 full_cover: bool | None = None, view: str = "front") -> None:
        super().__init__()
        self.view = view
        self.renderer = renderer
        self.front = front
        self.back = back
        self.title = title
        self.serial = serial
        self.platform = platform
        self.spine_color = spine_color
        self.case_color = case_color
        self.spine_left_offset = spine_left_offset
        self.spine_right_offset = spine_right_offset
        self.full_cover = full_cover

    def run(self) -> None:
        """Render once and emit the image, then the box model, or the error."""
        try:
            result = self.renderer.render(
                front_image=self.front,
                back_image=self.back,
                title=self.title,
                serial=self.serial,
                platform=self.platform,
                spine_color=self.spine_color,
                case_color=self.case_color,
                spine_left_offset=self.spine_left_offset,
                spine_right_offset=self.spine_right_offset,
                full_cover=self.full_cover,
                view=self.view,
            )
            self.rendered.emit(result)
            self.model_ready.emit(build_box_model(
                self.front, self.back, self.renderer.case_type,
                title=self.title,
                serial=self.serial,
                platform=self.platform,
                spine_color=self.spine_color,
                case_color=self.case_color,
                spine_left_offset=self.spine_left_offset,
                spine_right_offset=self.spine_right_offset,
                full_cover=self.full_cover,
                show_texture=self.renderer.show_texture,
            ))
        except Exception as e:
            self.error.emit(str(e))


class BatchWorker(QThread):
    """Background thread for batch processing multiple images.

    Uses ProcessPoolExecutor to render across CPU cores with a
    sequential fallback if multiprocessing is unavailable.
    """
    progress = pyqtSignal(int, int, str)  # current, total, filename
    finished_signal = pyqtSignal(int)  # number processed
    error = pyqtSignal(str)

    def __init__(self, file_paths: list[str], output_dir: str, renderer: BoxRenderer,
                 compress_level: int = 6, box_file: bool = False):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir
        # export.box_file: write each render's box file beside its PNG.
        self.box_file = box_file
        # rendering.compress_level, which single exports already honoured;
        # batch saved at the default (SLIP-0091).
        self.compress_level = compress_level
        # Extract config for pickling to worker processes
        self._case_type = renderer.case_type
        self._renderer_kwargs = {
            "angle": renderer.angle,
            "output_width": renderer.output_width,
            "show_reflection": renderer.show_reflection,
            "show_shadow": renderer.show_shadow,
            "show_texture": renderer.show_texture,
            "supersample": renderer.supersample,
            "background": renderer.background,
        }

    def run(self) -> None:
        """Render every selected file, emitting progress and per-file errors.

        The whole body is guarded: an unhandled exception here would leave
        finished_signal unsent, and the UI's progress bar visible forever.
        """
        count = 0
        try:
            total = len(self.file_paths)
            stems = pick_output_stems(self.file_paths, self.output_dir)
            args_list = [self._args_for(fp, stem)
                         for fp, stem in zip(self.file_paths, stems, strict=True)]
            workers = max(1, min((os.cpu_count() or 2) - 1, 4))

            if total >= 4 and workers > 1:
                count = self._run_parallel(args_list, total, workers)
            else:
                count = self._run_sequential(args_list)
        except Exception as e:
            self.error.emit(f"Batch failed: {e}")
        finally:
            self.finished_signal.emit(count)

    def _args_for(self, fp: str, stem: str) -> tuple:
        """The picklable arguments _render_single_image takes for one file."""
        return (fp, self.output_dir, stem, self._case_type, self._renderer_kwargs,
                self.compress_level, self.box_file)

    def _run_parallel(self, args_list: list, total: int, workers: int) -> int:
        count = 0
        completed = 0
        done: set[int] = set()
        try:
            mp_ctx = multiprocessing.get_context("spawn")
            with ProcessPoolExecutor(max_workers=workers,
                                     mp_context=mp_ctx) as pool:
                future_to_idx = {
                    pool.submit(_render_single_image, a): i
                    for i, a in enumerate(args_list)
                }
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    completed += 1
                    done.add(idx)
                    try:
                        name = future.result()
                        count += 1
                    except Exception as e:
                        name = Path(self.file_paths[idx]).stem
                        self.error.emit(f"{name}: {e}")
                    self.progress.emit(completed, total, name)
                    if self.isInterruptionRequested():
                        pool.shutdown(cancel_futures=True)
                        break
        except Exception as e:
            # Fall back to sequential if the pool itself failed. Skip the
            # indices that actually finished -- `completed` counts finished
            # FUTURES, which in completion order says nothing about position.
            self.error.emit(f"Parallel rendering unavailable: {e}")
            count += self._run_sequential(args_list, skip=done)
        return count

    def _run_sequential(self, args_list: list, skip: set[int] | None = None) -> int:
        count = 0
        skip = skip or set()
        total = len(args_list)
        for i, args in enumerate(args_list):
            if i in skip:
                continue
            if self.isInterruptionRequested():
                break
            name = Path(args[0]).stem
            self.progress.emit(i + 1, total, name)
            try:
                _render_single_image(args)
                count += 1
            except Exception as e:
                self.error.emit(f"{name}: {e}")
        return count


class AnimationWorker(QThread):
    """Background thread for rendering a rotation animation."""
    progress = pyqtSignal(int, int)  # current_frame, total_frames
    finished_signal = pyqtSignal(str)  # output path
    error = pyqtSignal(str)

    def __init__(
        self,
        case_type: CaseType,
        front_image: Image.Image,
        back_image: Image.Image | None,
        title: str,
        serial: str,
        platform: str,
        spine_color: tuple[int, int, int] | None,
        case_color: tuple[int, int, int] | None,
        spine_left_offset: int,
        spine_right_offset: int,
        output_path: str,
        output_width: int,
        start_angle: int,
        end_angle: int,
        frame_count: int,
        frame_delay: int,
        bounce: bool,
        fmt: str,
        show_reflection: bool,
        show_shadow: bool,
        background: str,
        show_texture: bool = True,
        supersample: int = 2,
        full_cover: bool | None = None,
    ):
        super().__init__()
        self.case_type = case_type
        self.front_image = front_image
        self.back_image = back_image
        self.title = title
        self.serial = serial
        self.platform = platform
        self.spine_color = spine_color
        self.case_color = case_color
        self.spine_left_offset = spine_left_offset
        self.spine_right_offset = spine_right_offset
        self.output_path = output_path
        self.output_width = output_width
        self.start_angle = start_angle
        self.end_angle = end_angle
        self.frame_count = frame_count
        self.frame_delay = frame_delay
        self.bounce = bounce
        self.fmt = fmt
        self.show_reflection = show_reflection
        self.show_shadow = show_shadow
        self.background = background
        self.show_texture = show_texture
        self.supersample = supersample
        self.full_cover = full_cover

    def run(self) -> None:
        """Render each angle of the sweep and write the animated file."""
        try:
            # One render per angle of the sweep. Bounce replays the sweep
            # backwards, so it reuses those frames rather than rendering and
            # storing each one a second time.
            angles = []
            for i in range(self.frame_count):
                t = i / max(1, self.frame_count - 1)
                angles.append(self.start_angle + t * (self.end_angle - self.start_angle))
            order = list(range(len(angles)))
            if self.bounce and self.frame_count > 2:
                order += order[-2:0:-1]

            total = len(angles)
            frames: list[Image.Image] = []
            max_w, max_h = 0, 0
            # Every frame is sized as the widest one is, so the box keeps one
            # size as it turns (SLIP-0105).
            fit_angle = max(
                angles, key=lambda a: visible_width_mm(self.case_type, a)
            )

            for i, angle in enumerate(angles):
                if self.isInterruptionRequested():
                    self.error.emit("Animation export cancelled")
                    return
                self.progress.emit(i + 1, total)
                renderer = BoxRenderer(
                    case_type=self.case_type,
                    angle=angle,
                    output_width=self.output_width,
                    show_reflection=self.show_reflection,
                    show_shadow=self.show_shadow,
                    show_texture=self.show_texture,
                    supersample=self.supersample,
                    background=self.background,
                    fit_angle=fit_angle,
                )
                frame = renderer.render(
                    front_image=self.front_image,
                    back_image=self.back_image,
                    title=self.title,
                    serial=self.serial,
                    platform=self.platform,
                    spine_color=self.spine_color,
                    case_color=self.case_color,
                    spine_left_offset=self.spine_left_offset,
                    spine_right_offset=self.spine_right_offset,
                    full_cover=self.full_cover,
                )
                if i == 0:
                    frame_w = max(frame.size[0], self.output_width)
                    need = frame_w * frame.size[1] * 4 * total
                    if need > MAX_ANIMATION_BYTES:
                        self.error.emit(
                            f"This animation would need about "
                            f"{need / 1024 ** 3:.1f} GB of memory "
                            f"({total} frames at {frame_w}x{frame.size[1]}), "
                            f"more than the {MAX_ANIMATION_BYTES / 1024 ** 3:.0f} GB "
                            "limit. Lower the width or the number of frames."
                        )
                        return
                frames.append(frame)
                max_w = max(max_w, frame.size[0])
                max_h = max(max_h, frame.size[1])

            # Normalize all frames in-place to the same size (frees originals)
            for i, frame in enumerate(frames):
                canvas = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
                ox = (max_w - frame.size[0]) // 2
                oy = max_h - frame.size[1]  # bottom-align
                canvas.paste(frame, (ox, oy))
                frames[i] = canvas  # Replace original, freeing its memory

            if self.fmt.upper() == "GIF":
                # Convert to RGB in-place (frees RGBA versions)
                bg = (0, 0, 0) if self.background == "black" else (255, 255, 255)
                for i, f in enumerate(frames):
                    bg_img = Image.new("RGBA", f.size, (*bg, 255))
                    comp = Image.alpha_composite(bg_img, f)
                    frames[i] = comp.convert("RGB")
                encoder_options = {"optimize": True}
            else:
                # APNG supports RGBA
                encoder_options = {"compress_level": 6}

            sequence = [frames[k] for k in order]
            sequence[0].save(
                self.output_path,
                save_all=True,
                append_images=sequence[1:],
                duration=self.frame_delay,
                loop=0,
                **encoder_options,
            )

            del frames, sequence
            self.finished_signal.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))
