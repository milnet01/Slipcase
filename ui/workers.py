"""Background worker threads for rendering and batch processing."""

import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image
from PyQt6.QtCore import QThread, pyqtSignal

from core.case_types import CaseType
from core.png_utils import save_optimized_png
from core.renderer import BoxRenderer


# ---------------------------------------------------------------------------
# Top-level helper for ProcessPoolExecutor (must be picklable)
# ---------------------------------------------------------------------------

def unique_output_path(output_dir: str, name: str, source_path: str) -> str:
    """Return a non-colliding output path for a batch render.

    Two defects this closes. Covers are generically named, so `A/cover.png`
    and `B/cover.png` both mapped to `<out>/cover.png` and the second silently
    won. And if the user picked the source folder as the output folder, a
    `.png` source was overwritten by its own render.
    """
    src = os.path.abspath(source_path)
    candidate = os.path.join(output_dir, f"{name}.png")
    n = 1
    while os.path.exists(candidate) or os.path.abspath(candidate) == src:
        candidate = os.path.join(output_dir, f"{name} ({n}).png")
        n += 1
    return candidate


def _render_single_image(args: tuple) -> str:
    """Render one image in a worker process.  Returns the output filename stem."""
    fp, output_dir, case_type, renderer_kwargs = args
    # Imports happen inside the child process (spawn context)
    from PIL import Image as _Img
    from core.renderer import BoxRenderer as _BR
    from core.png_utils import save_optimized_png as _save

    name = Path(fp).stem
    renderer = _BR(case_type=case_type, **renderer_kwargs)
    img = _Img.open(fp)
    img.load()
    result = renderer.render(front_image=img, title=name)
    del img
    out_path = unique_output_path(output_dir, name, fp)
    _save(result, out_path)
    del result
    return name


class RenderWorker(QThread):
    """Background thread for rendering the 3D box."""
    rendered = pyqtSignal(object)  # PIL Image
    error = pyqtSignal(str)

    def __init__(self, renderer: BoxRenderer, front, back, title, serial,
                 platform, spine_color, case_color=None, spine_left_offset=0,
                 spine_right_offset=0):
        super().__init__()
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

    def run(self):
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
            )
            self.rendered.emit(result)
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

    def __init__(self, file_paths: list[str], output_dir: str, renderer: BoxRenderer):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir
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

    def run(self):
        """Render every selected file, emitting progress and per-file errors.

        The whole body is guarded: an unhandled exception here would leave
        finished_signal unsent, and the UI's progress bar visible forever.
        """
        count = 0
        try:
            total = len(self.file_paths)
            args_list = [
                (fp, self.output_dir, self._case_type, self._renderer_kwargs)
                for fp in self.file_paths
            ]
            workers = max(1, min((os.cpu_count() or 2) - 1, 4))

            if total >= 4 and workers > 1:
                count = self._run_parallel(args_list, total, workers)
            else:
                count = self._run_sequential(total)
        except Exception as e:
            self.error.emit(f"Batch failed: {e}")
        finally:
            self.finished_signal.emit(count)

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
            count += self._run_sequential(total, skip=done)
        return count

    def _run_sequential(self, total: int, skip: set[int] | None = None) -> int:
        count = 0
        skip = skip or set()
        for i in range(total):
            if i in skip:
                continue
            if self.isInterruptionRequested():
                break
            fp = self.file_paths[i]
            name = Path(fp).stem
            self.progress.emit(i + 1, total, name)
            try:
                img = Image.open(fp)
                img.load()
                renderer = BoxRenderer(
                    case_type=self._case_type, **self._renderer_kwargs,
                )
                result = renderer.render(front_image=img, title=name)
                del img
                out_path = unique_output_path(self.output_dir, name, fp)
                save_optimized_png(result, out_path)
                del result
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

    def run(self):
        try:
            # Generate angle sequence
            angles = []
            for i in range(self.frame_count):
                t = i / max(1, self.frame_count - 1)
                angles.append(self.start_angle + t * (self.end_angle - self.start_angle))
            if self.bounce and self.frame_count > 2:
                angles += angles[-2:0:-1]

            total = len(angles)
            frames: list[Image.Image] = []
            max_w, max_h = 0, 0

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
                )
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
                frames[0].save(
                    self.output_path,
                    save_all=True,
                    append_images=frames[1:],
                    duration=self.frame_delay,
                    loop=0,
                    optimize=True,
                )
            else:
                # APNG supports RGBA
                frames[0].save(
                    self.output_path,
                    save_all=True,
                    append_images=frames[1:],
                    duration=self.frame_delay,
                    loop=0,
                    compress_level=6,
                )

            del frames
            self.finished_signal.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))
