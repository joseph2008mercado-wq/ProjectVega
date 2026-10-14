"""Current symbolic state; no raw pygame IDs or pygame objects."""

from __future__ import annotations

from dataclasses import dataclass, field

from vega.model import ButtonChange, ButtonControl, ControlChange, FaceChange, FaceControl, LeverChange


@dataclass
class PhysicalState:
    held_faces: set[FaceControl] = field(default_factory=set)
    lever_x: int = 0
    lever_y: int = 0
    held_buttons: set[ButtonControl] = field(default_factory=set)

    @property
    def fingering(self) -> frozenset[FaceControl]:
        return frozenset(self.held_faces)

    def apply(self, change: ControlChange) -> bool:
        """Apply one change, returning whether physical state actually changed."""
        if isinstance(change, FaceChange):
            was_pressed = change.face in self.held_faces
            if change.pressed == was_pressed:
                return False
            if change.pressed:
                self.held_faces.add(change.face)
            else:
                self.held_faces.remove(change.face)
            return True

        if isinstance(change, ButtonChange):
            was_pressed = change.control in self.held_buttons
            if change.pressed == was_pressed:
                return False
            if change.pressed:
                self.held_buttons.add(change.control)
            else:
                self.held_buttons.remove(change.control)
            return True

        if isinstance(change, LeverChange):
            if (change.x, change.y) == (self.lever_x, self.lever_y):
                return False
            self.lever_x, self.lever_y = change.x, change.y
            return True

        raise TypeError(f"unsupported control change: {type(change)!r}")

    def reset(self) -> None:
        self.held_faces.clear()
        self.held_buttons.clear()
        self.lever_x = 0
        self.lever_y = 0
