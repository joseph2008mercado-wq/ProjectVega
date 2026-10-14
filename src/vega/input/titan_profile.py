"""Verified Qanba Titan PC-system / DP-lever pygame mapping."""

from __future__ import annotations

from vega.input.events import RawAxisEvent, RawButtonEvent, RawEvent, RawHatEvent
from vega.model import ControlChange, FaceChange, FaceControl, LeverChange


# These pygame IDs are deliberately confined to the physical profile.
BUTTON_FACES = {
    2: FaceControl.FACE_1,
    3: FaceControl.FACE_2,
    5: FaceControl.FACE_3,
    4: FaceControl.FACE_4,
    0: FaceControl.FACE_5,
    1: FaceControl.FACE_6,
}
AXIS_FACES = {5: FaceControl.FACE_7, 4: FaceControl.FACE_8}
DP_HAT = 0


class TitanPcDpProfile:
    """Turn the observed PC+DP controls into symbolic changes.

    Trigger axes use two thresholds. Startup 0.0 lies between them and is
    treated as unpressed, not as a press. The gap also prevents jitter near
    either released (-1) or pressed (+1) from bouncing the control state.
    """

    def __init__(self, *, press_threshold: float = 0.5, release_threshold: float = -0.5) -> None:
        if not -1.0 < release_threshold < press_threshold < 1.0:
            raise ValueError("expected -1 < release_threshold < press_threshold < 1")
        self.press_threshold = press_threshold
        self.release_threshold = release_threshold
        self._axis_pressed: dict[int, bool] = {axis: False for axis in AXIS_FACES}

    def reset(self) -> None:
        """Forget axis state when the controller disconnects or mode changes."""
        self._axis_pressed = {axis: False for axis in AXIS_FACES}

    def translate(self, event: RawEvent) -> ControlChange | None:
        if isinstance(event, RawButtonEvent):
            face = BUTTON_FACES.get(event.button)
            return FaceChange(face, event.pressed, event.timestamp) if face else None

        if isinstance(event, RawHatEvent):
            return LeverChange(event.x, event.y, event.timestamp) if event.hat == DP_HAT else None

        if isinstance(event, RawAxisEvent):
            face = AXIS_FACES.get(event.axis)
            if face is None:
                return None
            was_pressed = self._axis_pressed[event.axis]
            if event.value >= self.press_threshold:
                is_pressed = True
            elif event.value <= self.release_threshold:
                is_pressed = False
            else:
                return None  # Includes the observed startup 0.0.
            if is_pressed == was_pressed:
                return None
            self._axis_pressed[event.axis] = is_pressed
            return FaceChange(face, is_pressed, event.timestamp)

        return None
