"""Simulated violet glass, independent of the Windows desktop theme."""

STYLE = """
QWidget { color: #e6e0e7; font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow { background: #100e18; }
QWidget#body { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
    stop:0 #413449, stop:0.32 #251d30, stop:0.7 #15121f, stop:1 #211927); }
QFrame#panel { background: transparent; border: none; }
QLabel { background: transparent; border: none; }
QLabel#section { color: #e0d6e5; font-size: 13px; font-weight: 600; }
QLabel#muted { color: #bdb1c4; font-size: 12px; }
QLabel#value { color: #d9ccb9; font-size: 22px; font-weight: 600; }
QLabel#status { color: #cabb9e; }
QPushButton, QDoubleSpinBox { border: 1px solid #76677f; border-bottom-color: #100d18;
    border-radius: 4px; padding: 6px 10px;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 #73677c, stop:0.06 #50435e, stop:0.48 #42364e,
    stop:0.5 #2c2335, stop:0.94 #241b2d, stop:1 #514358); }
QPushButton:hover { border-color: #b09a79; color: #f2e6cf; }
QPushButton:pressed { background: #201927; }
QPushButton:checked { border-color: #8b798f; color: #e6dbe9; }
QPushButton#mute:!checked { border-color: #b6a181; color: #eee0c9;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #807363,
    stop:0.48 #584b43, stop:0.5 #3e3235, stop:1 #514447); }
QPushButton:focus, QDoubleSpinBox:focus { border-color: #cbbca4; }
QPushButton:disabled { color: #817486; border-color: #403746; }
QSlider::groove:horizontal { height: 5px; background: #120f19; border: 1px solid #57455f; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #9b8465; border-radius: 3px; }
QSlider::handle:horizontal { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 #e2d3bc, stop:1 #897563); border: 1px solid #d2b994;
    width: 12px; margin: -5px 0; border-radius: 4px; }
QDoubleSpinBox { padding: 5px 8px; selection-background-color: #6b566c; }
QToolTip { background: #32283d; color: #eee1ca; border: 1px solid #99846d; }
QScrollArea { background: #17121f; }
QScrollBar:vertical { background: #191320; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #62526c; border: 1px solid #82708c;
    border-radius: 4px; min-height: 30px; margin: 2px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QStatusBar { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 #514559, stop:0.08 #302639, stop:1 #211a29);
    border-top: 1px solid #6c5d77; color: #c5b9cd; font-size: 12px; }
QStatusBar::item { border: none; }
"""
