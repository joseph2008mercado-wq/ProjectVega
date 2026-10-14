"""Paint-only instruments. All state supplied as symbolic values by the view."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from vega.model import FaceControl


class VegaMark(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(140, 74)
        self.setAccessibleName("Vega: abstract talons crossing six strings and a star")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for index in range(6):
            painter.setPen(QPen(QColor(178, 153, 114, 80 + index * 18), 1))
            y = 24 + index * 6
            painter.drawLine(QPointF(5, y), QPointF(128, y - 12))
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(3):
            x = 38 + index * 22
            blade = QPainterPath(QPointF(x, 65))
            blade.cubicTo(x + 7, 45, x + 8, 20, x + 26, 6)
            blade.cubicTo(x + 17, 33, x + 18, 45, x, 65)
            gradient = QLinearGradient(x, 8, x + 20, 65)
            gradient.setColorAt(0, QColor("#ddd0b7"))
            gradient.setColorAt(0.5, QColor("#957e86"))
            gradient.setColorAt(1, QColor("#47344f"))
            painter.fillPath(blade, gradient)
        painter.setPen(QPen(QColor("#f0dfbc"), 1.5))
        painter.drawLine(86, 23, 86, 39)
        painter.drawLine(78, 31, 94, 31)
        painter.setBrush(QColor("#f0dfbc"))
        painter.drawEllipse(QPointF(86, 31), 2, 2)
        painter.end()


class FaceBank(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.faces = frozenset()
        self.setMinimumSize(320, 164)
        self.setAccessibleName("Held face controls: none")

    def set_faces(self, faces: frozenset[FaceControl]) -> None:
        if faces != self.faces:
            self.faces = faces
            self.setAccessibleName("Held face controls: " + (", ".join(f.name for f in sorted(faces, key=lambda f: f.value)) or "none"))
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
            gradient.setColorAt(0, QColor("#e4d3b1" if active else "#574761"))
            gradient.setColorAt(0.45, QColor("#a48b69" if active else "#302738"))
            gradient.setColorAt(1, QColor("#746049" if active else "#1b1724"))
            if active:
                painter.setPen(QPen(QColor(216, 187, 140, 40), 7))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(center, radius + 2, radius + 2)
            painter.setPen(QPen(QColor("#e0c99d" if active else "#6b5876"), 1))
            painter.setBrush(gradient)
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QColor("#241b1e" if active else "#c3b3ca"))
            painter.drawText(QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2), Qt.AlignmentFlag.AlignCenter, str(index + 1))
            painter.setPen(QColor("#e0c99d" if active else "#a899b2"))
            painter.drawText(QRectF(center.x() - 38, center.y() + radius + 2, 76, 18), Qt.AlignmentFlag.AlignCenter, face.name)
        painter.end()


class LeverView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.position = (0, 0)
        self.setMinimumSize(310, 212)
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
            painter.setBrush(QColor("#ad9370" if active else "#302638"))
            painter.setPen(QPen(QColor("#e4d0aa" if active else "#5c4966"), 2 if active else 1))
            painter.drawEllipse(center, 16, 16)
            painter.setPen(QColor("#211b22" if active else "#c2b0c9"))
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
