"""Small, pygame-independent path from Titan events to strum gestures."""

from __future__ import annotations

from vega.input.events import RawEvent
from vega.input.state import PhysicalState
from vega.input.titan_profile import TitanPcDpProfile
from vega.model import ControlChange, LeverChange
from vega.music.strum import StrumGesture, StrumRecognizer


class VegaInputPipeline:
    def __init__(self, *, settle_seconds: float = 0.008) -> None:
        self.profile = TitanPcDpProfile()
        self.state = PhysicalState()
        self.recognizer = StrumRecognizer(settle_seconds=settle_seconds)
        self.last_change: ControlChange | None = None

    def on_raw(self, event: RawEvent) -> list[StrumGesture]:
        self.last_change = None
        ready = self.recognizer.flush(event.timestamp)
        change = self.profile.translate(event)
        if change is not None and self.state.apply(change):
            self.last_change = change  # Applied symbolic edge; never an unchanged duplicate.
            if isinstance(change, LeverChange):
                ready.extend(
                    self.recognizer.observe(
                        self.state.lever_x, self.state.lever_y, change.timestamp, self.state.fingering
                    )
                )
        return ready

    def flush(self, now: float) -> list[StrumGesture]:
        return self.recognizer.flush(now)

    def reset(self) -> None:
        self.last_change = None
        self.profile.reset()
        self.state.reset()
        self.recognizer.reset()
