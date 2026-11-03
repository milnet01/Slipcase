"""A turnable, zoomable 3D view of a BoxModel, drawn with QPainter.

The box is the patches core.box_shape gives: six faces, or a shaped case's
surface (SLIP-0125 § 4.4). Each patch's corners are projected with a
perspective camera that orbits the box, and a picture is mapped onto them
with QTransform.quadToQuad, which draws it perspective-correctly. Only
patches turned towards the camera are drawn. A six-faced box needs no
sorting, as its faces never overlap (SLIP-0104 § 4.5). A shaped one is not
convex: at most one of its two sheets faces the camera, and what lies behind
that sheet's plane is drawn before it, what stands in front after it, each
from the farthest centre to the nearest.

Box coordinates are millimetres with the box centred on the origin: x runs
across the front, y up, z out of the front. The spine is the x = -width/2
face, on the front's left as seen from the front.
"""

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image
from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor, QImage, QKeyEvent, QMouseEvent, QPainter, QPainterPath, QPaintEvent,
    QPen, QPolygonF, QTransform, QWheelEvent,
)
from PyQt6.QtWidgets import QWidget

from core.box_model import BoxModel
from core.box_shape import Patch, box_patches, face_corners, patch_normal

Vec = tuple[float, float, float]

_RESET_PITCH = 10.0
_PITCH_LIMIT = 89.0
# Field of view across the widget's shorter side. Narrow, so the fitted
# camera is far enough off that 10 degrees of pitch already shows the top,
# as the still render does; at 30 degrees it sat below the top's plane.
_FOV = math.radians(20)
# At the fitted zoom the box's bounding sphere spans this share of the
# shorter side, so a box turned any way stays inside the widget.
_FIT_SHARE = 0.9
# Closest and farthest camera, as multiples of the bounding sphere's radius
# and of the fitted distance. Above 1, the camera never enters the box.
_MIN_DISTANCE_RADII = 1.2
_MAX_DISTANCE_FITS = 4.0
_DRAG_DEGREES_PER_PX = 0.5
_KEY_DEGREES = 5.0
_ZOOM_STEP = 1.1  # one key press or wheel notch
_SPIN_DEGREES_PER_S = 30.0
_SPIN_INTERVAL_MS = 33
# Brightness = _AMBIENT + _DIFFUSE * max(0, normal . light). The light sits
# above, right of and in front of the camera, and turns with it, so whichever
# side faces the user is lit and the spine on the left falls darker, as in
# the still render.
_AMBIENT = 0.45
_DIFFUSE = 0.55
_LIGHT_IN_VIEW = (0.3, 0.35, 0.89)  # (right, up, towards the camera)
# A rounded strip whose region of its picture spans fewer pixels than this
# is filled with that region's average colour instead of the picture.
_PICTURE_MIN_PX = 8


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _unit(a: Vec) -> Vec:
    n = math.sqrt(_dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


@dataclass
class _Piece:
    """A patch as the viewer draws it, worked out once per model.

    `mode` is "plane" for a face, or a sheet, drawn by its face's picture
    mapped onto `plane` and clipped to the patch; "strip" for a patch drawn
    by the region `rect` of its picture, whose corners are `source`; and
    "fill" for a patch filled with `colour` alone. `parts`, when set, holds
    the patches a "plane" piece joins; it is drawn as their union.
    """
    corners: list[Vec]
    normal: Vec
    centre: Vec
    colour: tuple[int, int, int]
    face: str | None
    mode: str
    sheet: bool                     # the cover's flat sheet, front or back
    plane: list[Vec] | None = None
    source: QPolygonF | None = None
    rect: QRectF | None = None
    parts: list[list[Vec]] | None = None


def _piece(patch: Patch, pictures: dict[str, np.ndarray],
           plain: dict[str, tuple[int, int, int]],
           faces: dict[str, list[Vec]], shaped: bool) -> _Piece | None:
    """How to draw `patch`, or None for a patch with no area."""
    normal = patch_normal(patch.corners)
    if normal == (0.0, 0.0, 0.0):
        return None
    n = len(patch.corners)
    centre = tuple(sum(c[i] for c in patch.corners) / n for i in range(3))
    piece = _Piece(patch.corners, normal, centre, plain[patch.colour], None,
                   "fill", shaped and n > 4)
    picture = pictures.get(patch.face) if patch.face is not None else None
    if picture is None:
        return piece

    height, width = picture.shape[:2]
    us = [u * width for u, _ in patch.source]
    vs = [v * height for _, v in patch.source]
    x0 = min(max(0, math.floor(min(us))), width - 1)
    y0 = min(max(0, math.floor(min(vs))), height - 1)
    x1 = max(x0 + 1, min(width, math.ceil(max(us))))
    y1 = max(y0 + 1, min(height, math.ceil(max(vs))))
    region = picture[y0:y1, x0:x1].reshape(-1, picture.shape[2])[:, :3]
    piece.colour = tuple(int(round(c)) for c in region.mean(axis=0))

    outer = faces[patch.face]
    face_normal = patch_normal(outer)
    if not shaped or (n > 4 and _dot(normal, face_normal) > 1 - 1e-9):
        # A face, or a sheet parallel to its face: the face's picture, on
        # the patch's own plane.
        offset = _dot(face_normal, _sub(patch.corners[0], outer[0]))
        piece.plane = [tuple(c + offset * f for c, f in zip(corner, face_normal, strict=True))
                       for corner in outer]
        piece.mode, piece.face = "plane", patch.face
    elif (n == 4 and len({round(u, 6) for u in us}) <= 2
            and len({round(v, 6) for v in vs}) <= 2
            and max(x1 - x0, y1 - y0) >= _PICTURE_MIN_PX):
        # A straight strip: its region of the picture is a rectangle.
        low_u, low_v = min(us), min(vs)
        piece.source = QPolygonF([
            QPointF(x0 if u - low_u < 1e-6 else x1, y0 if v - low_v < 1e-6 else y1)
            for u, v in zip(us, vs, strict=True)])
        piece.rect = QRectF(x0, y0, x1 - x0, y1 - y0)
        piece.mode, piece.face = "strip", patch.face
    return piece


def _join_flat(pieces: list[_Piece], faces: dict[str, list[Vec]]) -> list[_Piece]:
    """`pieces` with the strips lying flat on one face's plane joined into
    one piece that draws that face's picture once. Drawn apart, each strip's
    outline shows as a line across the picture."""
    groups: dict[tuple[str, float], list[_Piece]] = {}
    kept = []
    for piece in pieces:
        if piece.mode == "strip":
            outer = faces[piece.face]
            normal = patch_normal(outer)
            if _dot(piece.normal, normal) > 1 - 1e-9:
                offset = round(_dot(normal, _sub(piece.corners[0], outer[0])), 6)
                groups.setdefault((piece.face, offset), []).append(piece)
                continue
        kept.append(piece)
    for (face, offset), group in groups.items():
        if len(group) == 1:
            kept.extend(group)
            continue
        corners = [c for piece in group for c in piece.corners]
        normal = patch_normal(faces[face])
        kept.append(_Piece(
            corners, group[0].normal,
            tuple(sum(c[i] for c in corners) / len(corners) for i in range(3)),
            tuple(round(sum(p.colour[i] for p in group) / len(group)) for i in range(3)),
            face, "plane", False,
            plane=[tuple(c + offset * f for c, f in zip(corner, normal, strict=True))
                   for corner in faces[face]],
            parts=[piece.corners for piece in group]))
    return kept


def _to_qimage(image: Image.Image) -> QImage:
    """A face picture as a QImage in the format QPainter draws fastest."""
    rgb = image.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    qimg = QImage(data, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888)
    # convertToFormat copies, so the result does not borrow `data`.
    return qimg.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)


class BoxViewer(QWidget):
    """Shows a BoxModel the user can turn, move and zoom.

    Left-drag turns, right- or middle-drag moves, the wheel zooms. Arrow keys
    turn, + and - zoom, Home or a double-click resets the view. It paints
    only the box, so whatever is behind the widget shows through.
    """
    auto_spin_changed = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAccessibleName(self.tr("3D box view"))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(200, 200)
        self._model: BoxModel | None = None
        self._images: dict[str, QImage] = {}
        self._corners: dict[str, list[Vec]] = {}
        self._normals: dict[str, Vec] = {}
        self._pieces: list[_Piece] = []
        self._shaped = False
        self._radius = 1.0
        self._angle = 30.0
        self.yaw = 0.0
        self.pitch = _RESET_PITCH
        self.distance = 1.0
        self._pan = QPointF(0, 0)
        self._drag_pos: QPointF | None = None
        self._drag_button = Qt.MouseButton.NoButton
        self._spin = QTimer(self)
        self._spin.setInterval(_SPIN_INTERVAL_MS)
        self._spin.timeout.connect(
            lambda: self.turn(_SPIN_DEGREES_PER_S * _SPIN_INTERVAL_MS / 1000, 0))

    # --- Model and view state ---

    def set_model(self, model: BoxModel | None, angle: float = 30.0) -> None:
        """Show `model` from the render's `angle`, or nothing for None.

        The faces are converted here, once per model, never while painting.
        """
        self._model = model
        self._images = {}
        if model is None:
            self.set_auto_spin(False)
            self.update()
            return
        pictures = {"front": model.front, "spine": model.spine,
                    "back": model.back, "edge": model.edge_face,
                    "top": model.top_face, "bottom": model.bottom_face}
        self._images = {face: _to_qimage(picture)
                        for face, picture in pictures.items() if picture is not None}
        ct = model.case_type
        self._corners = face_corners(ct)
        self._normals = {face: patch_normal(c) for face, c in self._corners.items()}
        self._shaped = ct.shape is not None
        arrays = {face: np.asarray(picture.convert("RGB"))
                  for face, picture in pictures.items() if picture is not None}
        plain = {"top": model.top, "bottom": model.bottom, "edge": model.edge}
        pieces = (_piece(patch, arrays, plain, self._corners, self._shaped)
                  for patch in box_patches(ct))
        self._pieces = [piece for piece in pieces if piece is not None]
        if self._shaped:
            self._pieces = _join_flat(self._pieces, self._corners)
        del arrays
        self._radius = math.sqrt(ct.width ** 2 + ct.height ** 2 + ct.depth ** 2) / 2
        self._angle = angle
        self.reset_view()

    @property
    def fitted_distance(self) -> float:
        """The camera distance at which the bounding sphere spans _FIT_SHARE."""
        return self._radius / math.sin(math.atan(math.tan(_FOV / 2) * _FIT_SHARE))

    @property
    def min_distance(self) -> float:
        return self._radius * _MIN_DISTANCE_RADII

    @property
    def max_distance(self) -> float:
        return self.fitted_distance * _MAX_DISTANCE_FITS

    def set_view(self, yaw: float, pitch: float) -> None:
        self.yaw = yaw % 360
        self.pitch = max(-_PITCH_LIMIT, min(_PITCH_LIMIT, pitch))
        self.update()

    def turn(self, d_yaw: float, d_pitch: float) -> None:
        self.set_view(self.yaw + d_yaw, self.pitch + d_pitch)

    def zoom_by(self, factor: float) -> None:
        """Zoom in by `factor` (below 1 zooms out), within the limits."""
        self.distance = max(self.min_distance,
                            min(self.max_distance, self.distance / factor))
        self.update()

    def reset_view(self) -> None:
        self.distance = self.fitted_distance
        self._pan = QPointF(0, 0)
        self.set_view(self._angle, _RESET_PITCH)

    def set_auto_spin(self, on: bool) -> None:
        """Start or stop turning the yaw at _SPIN_DEGREES_PER_S.

        auto_spin_changed reports every change, and reports False when there
        is no box to turn, so a toggle button bound to it never shows a spin
        that is not happening.
        """
        if on and self._model is None:
            self.auto_spin_changed.emit(False)
            return
        if on == self._spin.isActive():
            return
        if on:
            self._spin.start()
        else:
            self._spin.stop()
        self.auto_spin_changed.emit(on)

    # --- Projection ---

    def _camera(self) -> tuple[Vec, Vec, Vec, Vec]:
        """The camera's position and its right, up and forward directions."""
        yaw, pitch = math.radians(self.yaw), math.radians(self.pitch)
        position = (-math.sin(yaw) * math.cos(pitch) * self.distance,
                    math.sin(pitch) * self.distance,
                    math.cos(yaw) * math.cos(pitch) * self.distance)
        forward = _unit((-position[0], -position[1], -position[2]))
        right = _unit(_cross(forward, (0.0, 1.0, 0.0)))
        return position, right, _cross(right, forward), forward

    def visible_faces(self) -> set[str]:
        """The faces whose outer rectangle is turned towards the camera."""
        position = self._camera()[0]
        return {face for face, corners in self._corners.items()
                if _dot(self._normals[face], _sub(position, corners[0])) > 0}

    def paintEvent(self, event: QPaintEvent | None) -> None:
        if self._model is None:
            return
        position, right, up, forward = self._camera()
        focal = min(self.width(), self.height()) / 2 / math.tan(_FOV / 2)
        cx = self.width() / 2 + self._pan.x()
        cy = self.height() / 2 + self._pan.y()
        lx, ly, lz = _LIGHT_IN_VIEW
        light = _unit(tuple(lx * r + ly * u - lz * f
                            for r, u, f in zip(right, up, forward, strict=True)))

        def project(corners: list[Vec]) -> QPolygonF:
            points = []
            for corner in corners:
                rel = _sub(corner, position)
                depth = _dot(rel, forward)
                points.append(QPointF(cx + focal * _dot(rel, right) / depth,
                                      cy - focal * _dot(rel, up) / depth))
            return QPolygonF(points)

        visible = [piece for piece in self._pieces
                   if _dot(piece.normal, _sub(position, piece.centre)) > 0]
        # Behind the visible sheet's plane, the sheet, then in front of it;
        # each farthest to nearest (SLIP-0125 § 4.4).
        sheet = next((piece for piece in visible if piece.sheet), None)

        def order(piece: _Piece) -> tuple[int, float]:
            group = 0
            if piece is sheet:
                group = 1
            elif sheet is not None and _dot(sheet.normal, _sub(piece.centre, sheet.corners[0])) > 0:
                group = 2
            return group, -_dot(_sub(piece.centre, position), forward)

        visible.sort(key=order)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setPen(Qt.PenStyle.NoPen)
        for piece in visible:
            path = QPainterPath()
            for part in piece.parts or [piece.corners]:
                path.addPolygon(project(part))
                path.closeSubpath()
            if piece.parts:
                path = path.simplified()  # their union, outlined only outside
            brightness = _AMBIENT + _DIFFUSE * max(0.0, _dot(piece.normal, light))
            if self._shaped or piece.mode == "fill":
                colour = QColor(*(round(c * brightness) for c in piece.colour))
                if self._shaped:
                    # Outlined in its own colour, so no gap shows between patches.
                    painter.setPen(QPen(colour, 1))
                painter.setBrush(colour)
                painter.drawPath(path)
            if piece.mode == "fill":
                continue
            image = self._images[piece.face]
            shade = QColor(0, 0, 0, round(255 * (1 - brightness)))
            transform = QTransform()
            if piece.mode == "plane":
                rect = QRectF(0, 0, image.width(), image.height())
                source = QPolygonF([rect.topLeft(), rect.topRight(),
                                    rect.bottomRight(), rect.bottomLeft()])
                if not QTransform.quadToQuad(source, project(piece.plane), transform):
                    continue
                if self._shaped:
                    painter.setClipPath(path)
                painter.setTransform(transform)
                painter.drawImage(0, 0, image)
            else:
                if not QTransform.quadToQuad(piece.source, project(piece.corners), transform):
                    continue
                rect = piece.rect
                painter.setTransform(transform)
                painter.drawImage(rect.topLeft(), image, rect)
            painter.fillRect(rect, shade)
            painter.resetTransform()
            painter.setClipping(False)
        painter.end()

    # --- Controls ---

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event is None:
            return
        self._drag_pos = event.position()
        self._drag_button = event.button()

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        if event is None or self._drag_pos is None:
            return
        delta = event.position() - self._drag_pos
        self._drag_pos = event.position()
        self.set_auto_spin(False)
        if self._drag_button == Qt.MouseButton.LeftButton:
            self.turn(delta.x() * _DRAG_DEGREES_PER_PX, delta.y() * _DRAG_DEGREES_PER_PX)
        else:
            self._pan += delta
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event: QMouseEvent | None) -> None:
        self.reset_view()

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        if event is None or self._model is None:
            return
        self.zoom_by(_ZOOM_STEP ** (event.angleDelta().y() / 120))

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if event is None:
            return
        key = event.key()
        if key == Qt.Key.Key_Left:
            self.turn(-_KEY_DEGREES, 0)
        elif key == Qt.Key.Key_Right:
            self.turn(_KEY_DEGREES, 0)
        elif key == Qt.Key.Key_Up:
            self.turn(0, _KEY_DEGREES)
        elif key == Qt.Key.Key_Down:
            self.turn(0, -_KEY_DEGREES)
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal) and self._model is not None:
            self.zoom_by(_ZOOM_STEP)
        elif key == Qt.Key.Key_Minus and self._model is not None:
            self.zoom_by(1 / _ZOOM_STEP)
        elif key == Qt.Key.Key_Home:
            self.reset_view()
        else:
            super().keyPressEvent(event)
