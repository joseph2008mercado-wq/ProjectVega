"""Small, deliberately plain Win2000-era setup bitmaps from Vega's real icon."""

from pathlib import Path
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    app = QApplication.instance() or QApplication([])
    destination = ROOT / "build" / "installer-art"
    destination.mkdir(parents=True, exist_ok=True)
    renderer = QSvgRenderer(str(ROOT / "src/vega/app/resources/vega.svg"))
    if not renderer.isValid():
        raise RuntimeError("Vega SVG icon is missing or invalid")
    for name, width, height in (("welcome", 164, 314), ("header", 55, 55)):
        bitmap = QImage(width, height, QImage.Format.Format_RGB32)
        bitmap.fill(QColor("#3c3246"))
        painter = QPainter(bitmap)
        painter.setPen(QColor("#786b80"))
        painter.drawRect(0, 0, width - 1, height - 1)
        if name == "welcome":
            renderer.render(painter, QRectF(44, 36, 76, 76))
            painter.setPen(QColor("#d9ccb9"))
            painter.setFont(QFont("Tahoma", 17, QFont.Weight.Bold))
            painter.drawText(QRectF(12, 126, 140, 28), Qt.AlignmentFlag.AlignCenter, "Vega")
            painter.setPen(QColor("#786b80"))
            painter.drawLine(20, 166, 143, 166)
        else:
            renderer.render(painter, QRectF(7, 7, 41, 41))
        painter.end()
        if not bitmap.save(str(destination / f"{name}.bmp")):
            raise RuntimeError("Could not save installer artwork")
    print(f"Generated classic installer artwork: {destination}")


if __name__ == "__main__":
    main()
