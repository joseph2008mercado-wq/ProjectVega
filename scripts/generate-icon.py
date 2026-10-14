"""Rebuild the multi-resolution Windows ICO from the editable SVG using Qt."""

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

SIZES = (16, 24, 32, 48, 64, 128, 256)
RESOURCES = Path(__file__).resolve().parents[1] / "src" / "vega" / "app" / "resources"


def main() -> None:
    renderer = QSvgRenderer(str(RESOURCES / "vega.svg"))
    if not renderer.isValid():
        raise RuntimeError("Invalid Vega icon SVG")
    images = []
    for size in SIZES:
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "PNG"):
            raise RuntimeError(f"Failed to render {size}px icon")
        images.append(bytes(buffer.data()))
    offset = 6 + 16 * len(SIZES)
    directory = bytearray(struct.pack("<HHH", 0, 1, len(SIZES)))
    for size, data in zip(SIZES, images):
        directory.extend(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    (RESOURCES / "vega.ico").write_bytes(directory + b"".join(images))
    print(f"Generated {RESOURCES / 'vega.ico'} ({', '.join(map(str, SIZES))} px)")


if __name__ == "__main__":
    main()
