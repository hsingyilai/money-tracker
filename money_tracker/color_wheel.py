"""A colour wheel widget: click it to pick a hue and saturation."""
import math

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QConicalGradient, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget

from .models import DEFAULT_CATEGORY_COLOR


def qcolor_or_default(text: str | None) -> QColor:
    """A category's colour text as a QColor, falling back to the default colour
    when it is missing or not a colour (e.g. a hand-edited file)."""
    color = QColor(text or "")
    return color if color.isValid() else QColor(DEFAULT_CATEGORY_COLOR)


class ColorWheel(QWidget):
    """A hue wheel: the angle picks the hue, the distance from the centre picks
    the saturation (white in the middle, full colour at the rim), and
    set_value() dims it towards black."""

    colorChanged = pyqtSignal(QColor)

    MARGIN = 10

    def __init__(self, color: QColor):
        super().__init__()
        self.setMinimumSize(260, 260)
        self.hue = max(color.hsvHueF(), 0.0)  # hsvHueF() is -1 for greys.
        self.saturation = color.hsvSaturationF()
        self.value = color.valueF()

    def color(self) -> QColor:
        return QColor.fromHsvF(self.hue, self.saturation, self.value)

    def set_color(self, color: QColor):
        """Show `color` (marker and brightness) without emitting colorChanged."""
        self.hue = max(color.hsvHueF(), 0.0)  # hsvHueF() is -1 for greys.
        self.saturation = color.hsvSaturationF()
        self.value = color.valueF()
        self.update()

    def set_value(self, value: float):
        self.value = value
        self.update()
        self.colorChanged.emit(self.color())

    def _circle(self) -> tuple[QPointF, float]:
        centre = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - self.MARGIN
        return centre, radius

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        centre, radius = self._circle()

        # Hue goes round the circle (counter-clockwise from 3 o'clock).
        hues = QConicalGradient(centre, 0)
        for step in range(13):
            hues.setColorAt(step / 12, QColor.fromHsvF(min(step / 12, 0.999), 1, 1))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(hues)
        painter.drawEllipse(centre, radius, radius)

        # White fades in towards the centre to lower the saturation.
        fade = QRadialGradient(centre, radius)
        fade.setColorAt(0, QColor(255, 255, 255, 255))
        fade.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(fade)
        painter.drawEllipse(centre, radius, radius)

        # Black over the top for the brightness slider.
        painter.setBrush(QColor(0, 0, 0, round(255 * (1 - self.value))))
        painter.drawEllipse(centre, radius, radius)

        angle = self.hue * 2 * math.pi
        marker = QPointF(
            centre.x() + self.saturation * radius * math.cos(angle),
            centre.y() - self.saturation * radius * math.sin(angle),
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawEllipse(marker, 6, 6)
        painter.setPen(QPen(Qt.GlobalColor.white, 1))
        painter.drawEllipse(marker, 4, 4)

    def mousePressEvent(self, event):
        self._pick(event.position())

    def mouseMoveEvent(self, event):
        self._pick(event.position())

    def _pick(self, point: QPointF):
        centre, radius = self._circle()
        dx, dy = point.x() - centre.x(), centre.y() - point.y()  # y points up
        distance = math.hypot(dx, dy)
        if distance > radius:
            return
        self.hue = (math.atan2(dy, dx) / (2 * math.pi)) % 1.0
        self.saturation = distance / radius
        self.update()
        self.colorChanged.emit(self.color())
