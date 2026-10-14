"""Simulated violet glass, independent of the Windows desktop theme."""

STYLE = """
QWidget { color: #e6ddd5; font-family: 'Segoe UI'; font-size: 12px; }
QMainWindow { background: #100e18; }
QWidget#body { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
    stop:0 #251d31, stop:0.48 #15121f, stop:1 #100e17); }
QFrame#panel { border: 1px solid #4d4058; border-radius: 10px;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 #382d42, stop:0.035 #302639, stop:0.14 #241d2e, stop:1 #1b1724); }
QLabel { background: transparent; border: none; }
QLabel#section { color: #bfb0c6; font-size: 10px; font-weight: 600; letter-spacing: 2px; }
QLabel#muted { color: #b8aabb; font-size: 11px; }
QLabel#value { color: #e0cba8; font-size: 20px; font-weight: 600; }
QLabel#status { color: #d7c39f; }
QPushButton, QDoubleSpinBox { border: 1px solid #64536b; border-radius: 5px;
    padding: 6px 12px; background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 #493a52, stop:0.45 #302738, stop:0.5 #292131, stop:1 #211b29); }
QPushButton:hover { border-color: #b09a79; color: #f2e6cf; }
QPushButton:pressed { background: #201927; }
QPushButton:checked { border-color: #b5a084; background: #51444d; color: #f4e2bf; }
QPushButton:disabled { color: #817486; border-color: #403746; }
QSlider::groove:horizontal { height: 5px; background: #120f19; border: 1px solid #57455f; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #9b8465; border-radius: 3px; }
QSlider::handle:horizontal { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 #e2d3bc, stop:1 #897563); border: 1px solid #d2b994;
    width: 12px; margin: -5px 0; border-radius: 4px; }
QDoubleSpinBox { padding: 5px 8px; selection-background-color: #6b566c; }
QToolTip { background: #32283d; color: #eee1ca; border: 1px solid #99846d; }
"""
