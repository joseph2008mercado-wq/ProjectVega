"""GUI-independent owner of input, musical state, preview and MIDI output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from vega.audio.preview import PreviewSynth
from vega.input.events import RawEvent
from vega.input.pipeline import VegaInputPipeline
from vega.model import ButtonChange, ButtonControl, FaceControl
from vega.midi.output import MidiOutput
from vega.music.harmony import BankAction, FretSelection, Harmony, interpret, next_bank
from vega.music.guitar import GuitarVoicing, voice
from vega.music.plan import StrumPlan, plan_strum
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
    selection: FretSelection
    pending_bank: int | None
    harmony: Harmony
    voicing: GuitarVoicing
    latest_selection: FretSelection | None
    spread_ms: float
    midi_ports: tuple[str, ...]
    midi_port: str
    midi_status: str
    midi_channel: int


class VegaRuntime:
    def __init__(self, source: InputSource, preview: PreviewSynth, settings: Settings,
                 midi: MidiOutput | None = None, *, clock: Callable[[], float] | None = None) -> None:
        self.source = source
        self.preview = preview
        self.settings = settings
        self.pipeline = VegaInputPipeline(settle_seconds=settings.settle_ms / 1000)
        self.device = DeviceStatus(False)
        self.latest_strum: StrumGesture | None = None
        self.strum_count = 0
        self.bank = 1
        self.pending_bank: int | None = None
        self.latest_selection: FretSelection | None = None
        self.latest_plan: StrumPlan | None = None
        self.midi = midi or MidiOutput()
        self.clock = clock

    def bank_action(self, action: BankAction) -> None:
        self.pending_bank = next_bank(self.pending_bank or self.bank, action)
        self._apply_bank()

    def _apply_bank(self) -> None:
        if (self.pending_bank is not None and not self.pipeline.state.fingering
                and not self.pipeline.recognizer.has_pending):
            self.bank, self.pending_bank = self.pending_bank, None

    def tick(self, now: float) -> list[StrumGesture]:
        gestures: list[StrumGesture] = []
        captured: list[tuple[StrumGesture, int]] = []
        try:
            events = self.source.poll(now)
        except Exception as exc:
            events = [DeviceStatus(False, detail=f"Input unavailable: {exc}")]
        for event in events:
            if isinstance(event, DeviceStatus):
                self.device = event
                self.pipeline.reset()
                self.latest_strum = None
                self.latest_selection = None
                self.latest_plan = None
                self.pending_bank = None
                if not event.connected:
                    gestures.clear()  # Never restart audio after a same-batch unplug.
                    captured.clear()
                    self.panic()
            elif self.device.connected:
                ready = self.pipeline.on_raw(event)
                captured.extend((g, self.bank) for g in ready)
                change = self.pipeline.last_change
                if isinstance(change, ButtonChange) and change.control is ButtonControl.OPTIONS and change.pressed:
                    self.bank_action(BankAction.BANK_NEXT)
                self._apply_bank()
        # Flush during idle as well as after event batches. No GUI settling delay.
        captured.extend((g, self.bank) for g in self.pipeline.flush(now))
        self._apply_bank()
        for gesture, bank in captured:
            gestures.append(gesture)
            self.latest_strum = gesture
            self.strum_count += 1
            self.latest_selection = FretSelection.from_faces(gesture.fingering, bank)
            voicing = voice(interpret(self.latest_selection))
            self.latest_plan = plan_strum(gesture, voicing, self.settings.spread_ms)
            # Start musical time after planning, not at the old hardware
            # timestamp. Both outputs share exactly this epoch and plan.
            start = self.clock() if self.clock else now
            self.midi.submit(self.latest_plan, start)
            self.preview.play(self.latest_plan, start)
        output_now = self.clock() if self.clock else now
        self.midi.tick(output_now)
        self.preview.tick(output_now)
        return gestures

    def panic(self) -> None:
        self.preview.panic()
        self.midi.panic()

    def set_spread_ms(self, value: float) -> None:
        self.settings.spread_ms = bounded(value, 1, 30, 10)

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
        selection = FretSelection.from_faces(state.fingering, self.bank)
        harmony = interpret(selection)
        return ViewState(self.device, state.fingering, state.lever_x, state.lever_y,
                         self.latest_strum, self.strum_count, self.settings.settle_ms,
                         self.preview.muted, self.preview.volume, self.preview.status,
                         selection, self.pending_bank, harmony, voice(harmony), self.latest_selection,
                         self.settings.spread_ms, self.midi.port_names, self.midi.port_name,
                         self.midi.status, self.midi.channel)

    def close(self) -> None:
        self.midi.close()
        self.preview.close()
        self.source.close()
        self.pipeline.reset()
