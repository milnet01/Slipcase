"""3D boxart preview widget using QLabel with pixmap rendering."""

from PIL import Image
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QColor, QConicalGradient, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLabel, QSizePolicy, QWidget

from ui.themes import get_active_theme, themed_preview_style


def pil_to_qpixmap(pil_image: Image.Image) -> QPixmap:
    """Convert a PIL RGBA Image to a QPixmap."""
    img = pil_image.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, img.width * 4, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


class BusyOverlay(QWidget):
    """Semi-transparent overlay with a spinning arc indicator."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(25)  # ~40 fps
        self._timer.timeout.connect(self._tick)

    def show_busy(self) -> None:
        self.raise_()
        self.show()
        self._angle = 0
        self._timer.start()

    def hide_busy(self) -> None:
        self._timer.stop()
        self.hide()

    def _tick(self) -> None:
        self._angle = (self._angle + 8) % 360
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dim background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))

        # Spinning arc
        size = min(self.width(), self.height(), 200)
        arc_size = int(size * 0.3)
        cx = self.width() / 2
        cy = self.height() / 2
        rect = QRectF(cx - arc_size / 2, cy - arc_size / 2, arc_size, arc_size)

        # Gradient pen for the arc (fades from accent to transparent)
        accent = QColor(get_active_theme().accent)
        accent_bright = QColor(accent)
        accent_bright.setAlpha(240)
        accent_clear = QColor(accent)
        accent_clear.setAlpha(0)
        gradient = QConicalGradient(cx, cy, -self._angle)
        gradient.setColorAt(0.0, accent_bright)
        gradient.setColorAt(0.35, accent_bright)
        gradient.setColorAt(0.85, accent_clear)
        gradient.setColorAt(1.0, accent_clear)

        pen = QPen(gradient, max(3, arc_size // 10))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        # Draw a 270-degree arc
        start = int(self._angle * 16)
        span = 270 * 16
        painter.drawArc(rect, start, span)

        painter.end()


class PreviewWidget(QLabel):
    """Widget that displays a 3D boxart preview, scaled to fit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 200)
        self.setStyleSheet(themed_preview_style())
        self._source_pixmap: QPixmap | None = None
        self._rendered_image: Image.Image | None = None
        self.setText("No preview")

    def set_image(self, image: Image.Image) -> None:
        """Set the preview image from a PIL Image."""
        self._rendered_image = image
        self._source_pixmap = pil_to_qpixmap(image)
        self._update_display()

    def clear_image(self) -> None:
        """Clear the preview."""
        self._source_pixmap = None
        self._rendered_image = None
        self.setPixmap(QPixmap())
        self.setText("No preview")

    def get_rendered_image(self) -> Image.Image | None:
        """Get the current rendered PIL Image."""
        return self._rendered_image

    def resizeEvent(self, event) -> None:
        """Re-scale the pixmap on resize."""
        super().resizeEvent(event)
        self._update_display()

    def _update_display(self) -> None:
        """Scale and display the current pixmap."""
        if self._source_pixmap is None:
            return
        self.setText("")
        scaled = self._source_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
