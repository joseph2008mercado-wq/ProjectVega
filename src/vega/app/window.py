"""Compact control panel; widgets observe runtime state and send settings."""

from __future__ import annotations

import time

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QLayout, QMainWindow,
    QPushButton, QScrollArea, QSlider, QVBoxLayout, QWidget,
)

from vega.app.style import STYLE
from vega.app.widgets import FaceBank, GlassPanel, LeverView, VegaMark
from vega.runtime import VegaRuntime
from vega.settings import SettingsStore


def label(text: str, role: str = "") -> QLabel:
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setObjectName(role)
    return widget


def panel(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = GlassPanel()
    frame.setObjectName("panel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 14, 18, 14)
    layout.setSpacing(9)
    layout.addWidget(label(title, "section"))
    return frame, layout


class VegaWindow(QMainWindow):
    def __init__(self, runtime: VegaRuntime, store: SettingsStore) -> None:
        super().__init__()
        self.runtime = runtime
        self.store = store
        self.previous = None
        self.setWindowTitle("Project Vega · Guitar control panel")
        self.resize(860, 860)
        self.setMinimumSize(780, 580)
        self.setStyleSheet(STYLE)
        body = QWidget()
        body.setObjectName("body")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(body)
        self.setCentralWidget(scroll)
        outer = QVBoxLayout(body)
        outer.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        outer.setContentsMargins(22, 12, 22, 18)
        outer.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(VegaMark())
        brand = QVBoxLayout()
        title = label("Vega")
        title.setStyleSheet("font-size: 28px; font-weight: 400; color: #e3d9cc;")
        brand.addWidget(title)
        brand.addWidget(label("Guitar controller", "muted"))
        header.addLayout(brand)
        header.addStretch()
        outer.addLayout(header)

        device_panel, device_layout = panel("Device")
        row = QHBoxLayout()
        self.device_name = label("Qanba Titan")
        self.device_status = label("Waiting for Titan", "status")
        self.device_status.setWordWrap(True)
        row.addWidget(self.device_name)
        row.addStretch()
        row.addWidget(self.device_status)
        device_layout.addLayout(row)
        device_layout.addWidget(label("Qanba Titan PC+DP profile · Set physical switches to PC + DP", "muted"))
        outer.addWidget(device_panel)

        controls = QHBoxLayout()
        controls.setSpacing(12)
        faces_panel, faces_layout = panel("Face controls")
        self.faces = FaceBank()
        faces_layout.addWidget(self.faces)
        faces_layout.addWidget(label("Hold any combination. Each strum captures it.", "muted"))
        faces_layout.addStretch()
        controls.addWidget(faces_panel, 1)
        lever_panel, lever_layout = panel("Lever")
        lever_panel.setMinimumHeight(286)
        self.lever = LeverView()
        lever_layout.addWidget(self.lever)
        lever_layout.addWidget(label("Left / right: stroke · Vertical center: normal", "muted"))
        controls.addWidget(lever_panel, 1)
        outer.addLayout(controls)

        last_panel, last_layout = panel("Last strum")
        self.strum = label("—  Awaiting a stroke", "value")
        self.fingering = label("Fingering snapshot: —", "muted")
        self.strum_meta = label("Horizontal center rearms the next stroke.", "muted")
        last_layout.addWidget(self.strum)
        last_layout.addWidget(self.fingering)
        last_layout.addWidget(self.strum_meta)
        outer.addWidget(last_panel)

        lower = QHBoxLayout()
        lower.setSpacing(12)
        timing_panel, timing_layout = panel("Gesture settings")
        timing_row = QHBoxLayout()
        timing_row.addWidget(label("Diagonal settle window"))
        self.settle = QDoubleSpinBox()
        self.settle.setRange(0, 20)
        self.settle.setDecimals(1)
        self.settle.setSingleStep(1)
        self.settle.setSuffix(" ms")
        self.settle.setValue(runtime.settings.settle_ms)
        self.settle.setAccessibleName("Production recognizer settle window in milliseconds")
        timing_row.addWidget(self.settle)
        timing_layout.addLayout(timing_row)
        presets = QHBoxLayout()
        for value in (4, 6, 8, 10, 12):
            button = QPushButton(str(value))
            button.setToolTip(f"Set the production settle window to {value} ms")
            button.clicked.connect(lambda checked=False, ms=value: self.settle.setValue(ms))
            presets.addWidget(button)
        timing_layout.addLayout(presets)
        timing_layout.addWidget(label("Verified default: 8 ms · Adjustable", "muted"))
        lower.addWidget(timing_panel, 1)

        audio_panel, audio_layout = panel("Preview audio")
        audio_row = QHBoxLayout()
        self.mute = QPushButton("Muted · Unmute")
        self.mute.setObjectName("mute")
        self.mute.setCheckable(True)
        self.mute.setChecked(True)
        self.panic = QPushButton("Panic / Stop")
        self.panic.setToolTip("Stop all preview voices immediately. Future gestures may sound if unmuted.")
        audio_row.addWidget(self.mute)
        audio_row.addWidget(self.panic)
        audio_layout.addLayout(audio_row)
        volume_row = QHBoxLayout()
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(round(runtime.preview.volume * 100))
        self.volume.setAccessibleName("Preview volume")
        self.volume_value = label(f"{self.volume.value()}%", "muted")
        volume_row.addWidget(label("Volume", "muted"))
        volume_row.addWidget(self.volume)
        volume_row.addWidget(self.volume_value)
        audio_layout.addLayout(volume_row)
        self.audio_status = label(runtime.preview.status, "muted")
        self.audio_status.setWordWrap(True)
        audio_layout.addWidget(self.audio_status)
        lower.addWidget(audio_panel, 1)
        outer.addLayout(lower)

        footer = QHBoxLayout()
        footer.addWidget(label("MIDI  ·  Not implemented yet", "muted"))
        footer.addStretch()
        footer.addWidget(label("Preview strums · Fixed audition pitches", "muted"))
        outer.addLayout(footer)
        self.settings_status = label(store.error, "muted")
        self.settings_status.setWordWrap(True)
        self.settings_status.setVisible(bool(store.error))
        outer.addWidget(self.settings_status)

        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(400)
        self.save_timer.timeout.connect(self.save_settings)
        self.flash_timer = QTimer(self)
        self.flash_timer.setSingleShot(True)
        self.flash_timer.setInterval(140)
        self.flash_timer.timeout.connect(lambda: self.strum.setStyleSheet(""))
        self.settle.valueChanged.connect(self.change_settle)
        self.volume.valueChanged.connect(self.change_volume)
        self.mute.toggled.connect(self.change_mute)
        self.panic.clicked.connect(runtime.preview.panic)
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(2)
        self.timer.timeout.connect(self.poll)
        self.refresh()
        self.timer.start()

    def poll(self) -> None:
        gestures = self.runtime.tick(time.perf_counter())
        if gestures:
            self.strum.setStyleSheet("color: #f3e3c3;")
            self.flash_timer.start()
        self.refresh()

    def refresh(self) -> None:
        state = self.runtime.snapshot()
        if state == self.previous:
            return
        self.previous = state
        self.device_name.setText(state.device.name)
        self.device_status.setText(("● " if state.device.connected else "○ ") + state.device.detail)
        self.faces.set_faces(state.faces)
        self.lever.set_position(state.lever_x, state.lever_y)
        gesture = state.latest_strum
        if gesture is None:
            self.strum.setText("—  Awaiting a stroke")
            self.fingering.setText("Fingering snapshot: —")
            self.strum_meta.setText("Horizontal center rearms the next stroke.")
        else:
            self.strum.setText(f"{gesture.direction.name}  /  {gesture.character.name}")
            names = ", ".join(face.name for face in sorted(gesture.fingering, key=lambda face: face.value))
            self.fingering.setText("Fingering snapshot: " + (names or "(none)"))
            self.strum_meta.setText(f"Stroke {state.strum_count:04d}  ·  perf {gesture.timestamp:.6f} s")
        self.audio_status.setText(state.audio_status)
        self.mute.blockSignals(True)
        self.mute.setChecked(state.muted)
        self.mute.setText("Muted · Unmute" if state.muted else "Sound on · Mute")
        self.mute.blockSignals(False)
        self.mute.setEnabled(self.runtime.preview.available)

    def change_settle(self, value: float) -> None:
        self.runtime.set_settle_ms(value)
        self.save_timer.start()
        self.refresh()

    def change_volume(self, value: int) -> None:
        self.runtime.set_volume(value / 100)
        self.volume_value.setText(f"{value}%")
        self.save_timer.start()
        self.refresh()

    def change_mute(self, muted: bool) -> None:
        self.runtime.preview.set_muted(muted)
        self.refresh()

    def save_settings(self) -> None:
        self.store.save(self.runtime.settings)
        self.settings_status.setText(self.store.error)
        self.settings_status.setVisible(bool(self.store.error))

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.save_timer.stop()
        self.flash_timer.stop()
        self.runtime.close()
        self.save_settings()
        event.accept()
