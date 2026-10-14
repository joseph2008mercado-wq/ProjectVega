"""Small pygame-independent representations of raw joystick events."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawButtonEvent:
    button: int
    pressed: bool
    timestamp: float
    instance_id: int | None = None


@dataclass(frozen=True)
class RawAxisEvent:
    axis: int
    value: float
    timestamp: float
    instance_id: int | None = None


@dataclass(frozen=True)
class RawHatEvent:
    hat: int
    x: int
    y: int
    timestamp: float
    instance_id: int | None = None


RawEvent = RawButtonEvent | RawAxisEvent | RawHatEvent
