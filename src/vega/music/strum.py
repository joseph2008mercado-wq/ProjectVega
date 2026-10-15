"""Recognize symbolic horizontal strokes without chord or MIDI behavior."""

from __future__ import annotations

from dataclasses import dataclass, replace

from vega.model import FaceControl, StrumCharacter, StrumDirection


def character_for_y(y: int) -> StrumCharacter:
    return {
        -1: StrumCharacter.FULL,
        0: StrumCharacter.NORMAL,
        1: StrumCharacter.STRICT,
    }[y]


@dataclass(frozen=True)
class StrumGesture:
    direction: StrumDirection
    character: StrumCharacter
    timestamp: float
    fingering: frozenset[FaceControl]


class StrumRecognizer:
    """One stroke per x=0 -> x=±1 acquisition; only x=0 rearms.

    A short settle window lets SDL report LEFT then UP+LEFT (or RIGHT then
    DOWN+RIGHT) as one intended diagonal. The gesture keeps the first
    horizontal-acquisition timestamp and fingering. A nonzero y observed on
    the held side during the window refines the character. A later y=0 does
    not erase an already observed FULL/STRICT diagonal. Call flush(now) from
    the future input loop even when there are no new events.
    """

    def __init__(self, *, settle_seconds: float = 0.008) -> None:
        if settle_seconds < 0:
            raise ValueError("settle_seconds must be non-negative")
        self.settle_seconds = settle_seconds
        self._previous_x = 0
        self._pending: StrumGesture | None = None

    def observe(
        self, x: int, y: int, timestamp: float, fingering: frozenset[FaceControl]
    ) -> list[StrumGesture]:
        if x not in (-1, 0, 1) or y not in (-1, 0, 1):
            raise ValueError("lever components must be -1, 0, or 1")
        ready = self.flush(timestamp)
        previous_x = self._previous_x
        self._previous_x = x

        if x == 0:
            # A very quick stroke must still be emitted, even if the settle
            # deadline has not arrived. Vertical position on release does not
            # change the character of that finished horizontal excursion.
            if self._pending is not None:
                ready.append(self._pending)
                self._pending = None
        elif previous_x == 0:
            self._pending = StrumGesture(
                direction=StrumDirection.LEFT if x == -1 else StrumDirection.RIGHT,
                character=character_for_y(y),
                timestamp=timestamp,
                fingering=frozenset(fingering),
            )
            ready.extend(self.flush(timestamp))  # Immediate when window is zero.
        elif (
            self._pending is not None
            and x == (-1 if self._pending.direction is StrumDirection.LEFT else 1)
            and y != 0
        ):
            self._pending = replace(self._pending, character=character_for_y(y))

        return ready

    def flush(self, now: float) -> list[StrumGesture]:
        if self._pending is None or now < self._pending.timestamp + self.settle_seconds:
            return []
        gesture = self._pending
        self._pending = None
        return [gesture]

    @property
    def has_pending(self) -> bool:
        """Runtime can defer bank changes without altering a captured stroke."""
        return self._pending is not None

    def reset(self) -> None:
        """Drop a pending stroke when its controller disconnects."""
        self._previous_x = 0
        self._pending = None

    def cancel_pending(self) -> None:
        """Panic cancels settling without rearming a still-held lever."""
        self._pending = None
