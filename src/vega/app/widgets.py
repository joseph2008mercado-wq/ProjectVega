"""Paint-only instruments. All state supplied as symbolic values by the view."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QWidget

from vega.model import FaceControl
from vega.app.identity import icon_path


class GlassPanel(QFrame):
    """A clipped reflection and double rim give glass depth without OS blur."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -2)
        shape = QPainterPath()
        shape.addRoundedRect(rect, 4, 4)
        painter.setPen(QPen(QColor(0, 0, 0, 120), 2))
        painter.drawRoundedRect(rect.translated(0, 1), 4, 4)
        surface = QLinearGradient(0, 0, self.width() * 0.35, self.height())
        surface.setColorAt(0, QColor(87, 73, 98, 225))
        surface.setColorAt(0.22, QColor(49, 38, 62, 235))
        surface.setColorAt(0.65, QColor(26, 21, 35, 245))
        surface.setColorAt(1, QColor(39, 29, 47, 235))
        painter.fillPath(shape, surface)
        painter.save()
        painter.setClipPath(shape)
        sheen = QLinearGradient(0, 0, 0, 38)
        sheen.setColorAt(0, QColor(237, 224, 247, 45))
        sheen.setColorAt(0.48, QColor(237, 224, 247, 20))
        sheen.setColorAt(0.51, QColor(16, 10, 23, 55))
        sheen.setColorAt(1, QColor(16, 10, 23, 25))
        painter.fillRect(QRectF(0, 0, self.width(), 38), sheen)
        painter.setPen(QColor(0, 0, 0, 100))
        painter.drawLine(2, 38, self.width() - 3, 38)
        painter.setPen(QColor(202, 181, 218, 28))
        painter.drawLine(2, 39, self.width() - 3, 39)
        painter.restore()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(179, 159, 192, 105), 1))
        painter.drawPath(shape)
        painter.setPen(QPen(QColor(235, 222, 240, 32), 1))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 3, 3)
        painter.end()


class VegaMark(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(56, 56)
        self.setAccessibleName("Vega: three abstract slashes crossing six strings")
        self.icon = QIcon(str(icon_path()))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        self.icon.paint(painter, 4, 4, 48, 48)
        painter.end()


class FaceBank(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.faces = frozenset()
        self.bank = 1
        self.setMinimumSize(260, 150)
        self.setToolTip("Left to right: FACE_1–FACE_4, then FACE_5–FACE_8")
        self.setAccessibleName("Held face controls: none")

    @property
    def fret_labels(self) -> tuple[int, ...]:
        return tuple((self.bank - 1) * 8 + i for i in range(1, 9))

    def set_faces(self, faces: frozenset[FaceControl], bank: int = 1) -> None:
        if faces != self.faces or bank != self.bank:
            self.faces = faces
            self.bank = bank
            self.setAccessibleName("Held frets: " + (", ".join(str((bank - 1) * 8 + f.value) for f in sorted(faces, key=lambda f: f.value)) or "open"))
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cell = self.width() / 4
        radius = min(cell * 0.32, 27)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        for index, face in enumerate(FaceControl):
            center = QPointF(cell * (index % 4 + 0.5), 37 + (index // 4) * 74)
            active = face in self.faces
            gradient = QLinearGradient(center.x(), center.y() - radius, center.x(), center.y() + radius)
            gradient.setColorAt(0, QColor("#baa88a" if active else "#88758f"))
            gradient.setColorAt(0.12, QColor("#8c7a62" if active else "#584762"))
            gradient.setColorAt(0.48, QColor("#675645" if active else "#403249"))
            gradient.setColorAt(0.51, QColor("#3d3032" if active else "#241b2e"))
            gradient.setColorAt(1, QColor("#6f5d4f" if active else "#43334e"))
            if active:
                painter.setPen(QPen(QColor(216, 187, 140, 40), 7))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(center, radius + 2, radius + 2)
            painter.setPen(QPen(QColor("#e0c99d" if active else "#6b5876"), 1))
            painter.setBrush(gradient)
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QColor("#f2e4c8" if active else "#d6c9de"))
            painter.drawText(QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2), Qt.AlignmentFlag.AlignCenter, str(self.fret_labels[index]))
        painter.end()


class LeverView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.position = (0, 0)
        self.setMinimumSize(280, 212)
        self.setAccessibleName("Lever centered")

    def set_position(self, x: int, y: int) -> None:
        if self.position != (x, y):
            self.position = (x, y)
            self.setAccessibleName(f"Lever x={x}, y={y}")
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        painter.setPen(QPen(QColor("#55445f"), 1))
        painter.setBrush(QColor("#1a1522"))
        painter.drawEllipse(QPointF(cx, cy), 74, 74)
        painter.setFont(QFont("Segoe UI", 9))
        labels = {(0, 1): "↑", (0, -1): "↓", (-1, 0): "←", (1, 0): "→",
                  (-1, 1): "↖", (1, 1): "↗", (-1, -1): "↙", (1, -1): "↘", (0, 0): "•"}
        for (x, y), label in labels.items():
            active = self.position == (x, y)
            center = QPointF(cx + x * 46, cy - y * 46)
            glass = QLinearGradient(0, center.y() - 16, 0, center.y() + 16)
            glass.setColorAt(0, QColor("#b5a185" if active else "#6a5876"))
            glass.setColorAt(0.48, QColor("#77654f" if active else "#42334f"))
            glass.setColorAt(0.52, QColor("#493c35" if active else "#251c30"))
            glass.setColorAt(1, QColor("#685545" if active else "#3a2b45"))
            painter.setBrush(glass)
            painter.setPen(QPen(QColor("#e4d0aa" if active else "#5c4966"), 2 if active else 1))
            painter.drawEllipse(center, 16, 16)
            painter.setPen(QColor("#f2e4c8" if active else "#c2b0c9"))
            painter.setFont(QFont("Segoe UI", 14))
            painter.drawText(QRectF(center.x() - 16, center.y() - 16, 32, 32), Qt.AlignmentFlag.AlignCenter, label)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        painter.setPen(QColor("#cbb691"))
        for text, rect in [("STRICT", QRectF(cx - 55, cy - 102, 110, 20)),
                           ("FULL", QRectF(cx - 55, cy + 82, 110, 20)),
                           ("LEFT", QRectF(0, cy - 10, cx - 82, 20)),
                           ("RIGHT", QRectF(cx + 82, cy - 10, cx - 82, 20))]:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
