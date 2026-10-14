"""GUI-independent owner of the verified input pipeline and optional preview."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from vega.audio.preview import PreviewSynth
from vega.input.events import RawEvent
from vega.input.pipeline import VegaInputPipeline
from vega.model import FaceControl
from vega.music.strum import StrumGesture
from vega.settings import Settings, bounded


@dataclass(frozen=True)
class DeviceStatus:
    connected: bool
    name: str = "Qanba Titan"
    detail: str = "Disconnected · waiting for Titan"


class InputSource(Protocol):
    def poll(self, now: float) -> list[RawEvent | DeviceStatus]: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class ViewState:
    device: DeviceStatus
    faces: frozenset[FaceControl]
    lever_x: int
    lever_y: int
    latest_strum: StrumGesture | None
    strum_count: int
    settle_ms: float
    muted: bool
    volume: float
    audio_status: str


class VegaRuntime:
    def __init__(self, source: InputSource, preview: PreviewSynth, settings: Settings) -> None:
        self.source = source
        self.preview = preview
        self.settings = settings
        self.pipeline = VegaInputPipeline(settle_seconds=settings.settle_ms / 1000)
        self.device = DeviceStatus(False)
        self.latest_strum: StrumGesture | None = None
        self.strum_count = 0

    def tick(self, now: float) -> list[StrumGesture]:
        gestures: list[StrumGesture] = []
        try:
            events = self.source.poll(now)
        except Exception as exc:
            events = [DeviceStatus(False, detail=f"Input unavailable: {exc}")]
        for event in events:
            if isinstance(event, DeviceStatus):
                self.device = event
                self.pipeline.reset()
                self.latest_strum = None
                if not event.connected:
                    gestures.clear()  # Never restart audio after a same-batch unplug.
                    self.preview.panic()
            elif self.device.connected:
                gestures.extend(self.pipeline.on_raw(event))
        # Flush during idle as well as after event batches. No GUI settling delay.
        gestures.extend(self.pipeline.flush(now))
        for gesture in gestures:
            self.latest_strum = gesture
            self.strum_count += 1
            self.preview.play(gesture)
        return gestures

    def set_settle_ms(self, value: float) -> None:
        self.settings.settle_ms = bounded(value, 0, 20, 8)
        # The verified recognizer already exposes this parameter. An in-flight
        # stroke uses the new deadline at its next flush; no reset or duplicate.
        self.pipeline.recognizer.settle_seconds = self.settings.settle_ms / 1000

    def set_volume(self, value: float) -> None:
        self.preview.set_volume(value)
        self.settings.preview_volume = self.preview.volume

    def snapshot(self) -> ViewState:
        state = self.pipeline.state
        return ViewState(self.device, state.fingering, state.lever_x, state.lever_y,
                         self.latest_strum, self.strum_count, self.settings.settle_ms,
                         self.preview.muted, self.preview.volume, self.preview.status)

    def close(self) -> None:
        self.preview.close()
        self.source.close()
        self.pipeline.reset()
