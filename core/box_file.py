"""The box file: a box's size, colours and face pictures, for RetroDB.

Format version 1 is the contract both apps bind to (SLIP-0104 § 4.1). For a
stem S, one folder holds S.box.json, S.front.png, S.spine.png and, when the
box has them, S.back.png and S.edge.png, the opening side. read_box_file is Slipcase's reference for
RetroDB's reader.
"""

import json
import math
import os
import re
import tempfile

from PIL import Image

from core.box_model import BoxModel
from core.case_types import CaseType
from core.png_utils import save_optimized_png
from core.version import __version__

FORMAT = "slipcase-box"
VERSION = 1

# Face key in the file -> the BoxModel attribute holding its picture. The
# edge's picture is edge_face: BoxModel.edge is that side's colour.
_FACES = {"front": "front", "spine": "spine", "back": "back", "edge": "edge_face"}
_COLOURS = ("top", "bottom", "edge")
_SIZES = ("width_mm", "height_mm", "depth_mm")
_MAX_SIZE_MM = 1000
_COLOUR_RE = re.compile(r"#[0-9A-Fa-f]{6}")


class BoxFileError(ValueError):
    """A box file that breaks a reading rule, or a stem that cannot be written."""


def _names(stem: str) -> dict[str, str]:
    """The file names for `stem`: the description and each face."""
    names = {"json": f"{stem}.box.json"}
    names.update({face: f"{stem}.{face}.png" for face in _FACES})
    return names


def _check_name(name: object) -> str:
    """`name` if it is a single plain file name, else BoxFileError."""
    if (not isinstance(name, str) or not name or "/" in name or "\\" in name
            or name in (".", "..") or name.startswith(".")):
        raise BoxFileError(f"not a plain file name: {name!r}")
    return name


def box_paths(folder: str, stem: str) -> list[str]:
    """The five paths a box file of `stem` uses: description, front, spine,
    back, edge."""
    return [os.path.join(folder, name) for name in _names(stem).values()]


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def write_box_file(model: BoxModel, folder: str, stem: str,
                   compress_level: int = 6) -> str:
    """Write `model` as the box file `stem` in `folder`; return the .json path.

    A stem whose names fail the name rule is refused before anything is
    written, so no face lands outside `folder`. Any earlier box file of the
    stem is removed first, and the description is written last, so a
    .box.json never names a face that was not written. If a write fails, the
    faces already written are removed and the error is raised.
    """
    names = _names(stem)
    for name in names.values():
        _check_name(name)
    paths = dict(zip(names, box_paths(folder, stem), strict=True))
    for path in paths.values():
        _remove(path)

    ct = model.case_type
    data = {
        "format": FORMAT,
        "version": VERSION,
        "generator": f"Slipcase {__version__}",
        "case": {"name": ct.name, "width_mm": ct.width,
                 "height_mm": ct.height, "depth_mm": ct.depth},
        "colours": {key: "#{:02X}{:02X}{:02X}".format(*getattr(model, key))
                    for key in _COLOURS},
        "faces": {face: names[face] if getattr(model, attr) is not None else None
                  for face, attr in _FACES.items()},
    }

    written: list[str] = []
    try:
        for face, attr in _FACES.items():
            image = getattr(model, attr)
            if image is None:
                continue
            save_optimized_png(image, paths[face], compress_level=compress_level)
            written.append(paths[face])
        fd, tmp_name = tempfile.mkstemp(dir=folder, prefix=".", suffix=".json.tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_name, paths["json"])
        except BaseException:
            _remove(tmp_name)
            raise
    except BaseException:
        for path in written:
            _remove(path)
        raise
    return paths["json"]


def _size(case: dict, key: str) -> float:
    value = case.get(key)
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not 0 < value <= _MAX_SIZE_MM):
        raise BoxFileError(f"case {key} is not a size in mm: {value!r}")
    return value


def _colour(colours: dict, key: str) -> tuple[int, int, int]:
    value = colours.get(key)
    if not isinstance(value, str) or not _COLOUR_RE.fullmatch(value):
        raise BoxFileError(f"colour {key} is not #RRGGBB: {value!r}")
    return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))


def _face(folder: str, name: object) -> Image.Image:
    path = os.path.join(folder, _check_name(name))
    if not os.path.isfile(path):
        raise BoxFileError(f"face picture missing: {name}")
    try:
        with Image.open(path) as img:
            img.load()
            return img.convert("RGB")
    except (OSError, Image.DecompressionBombError) as e:
        raise BoxFileError(f"face picture unreadable: {name}: {e}") from e


def _section(data: dict, key: str) -> dict:
    value = data.get(key)
    if not isinstance(value, dict):
        raise BoxFileError(f"{key} is missing or not an object")
    return value


def read_box_file(path: str) -> BoxModel:
    """Read a box file, applying every reading rule of SLIP-0104 § 4.1."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BoxFileError(f"cannot read {path}: {e}") from e
    if not isinstance(data, dict):
        raise BoxFileError("the box file is not a JSON object")
    if data.get("format") != FORMAT:
        raise BoxFileError(f"format is not {FORMAT}: {data.get('format')!r}")
    version = data.get("version")
    if type(version) is not int or version != VERSION:
        raise BoxFileError(f"unsupported version: {version!r}")

    case = _section(data, "case")
    name = case.get("name")
    if not isinstance(name, str) or not name:
        raise BoxFileError(f"case name is not text: {name!r}")
    width, height, depth = (_size(case, key) for key in _SIZES)
    colours = _section(data, "colours")
    top, bottom, edge = (_colour(colours, key) for key in _COLOURS)

    faces = _section(data, "faces")
    folder = os.path.dirname(path)
    if faces.get("front") is None or faces.get("spine") is None:
        raise BoxFileError("front and spine must name a picture")
    back_name = faces.get("back")
    # Optional, so a file written before SLIP-0106 still reads.
    edge_name = faces.get("edge")
    return BoxModel(
        case_type=CaseType(name=name, width=width, height=height, depth=depth,
                           platforms=()),
        top=top, bottom=bottom, edge=edge,
        front=_face(folder, faces["front"]),
        spine=_face(folder, faces["spine"]),
        back=_face(folder, back_name) if back_name is not None else None,
        edge_face=_face(folder, edge_name) if edge_name is not None else None,
    )
