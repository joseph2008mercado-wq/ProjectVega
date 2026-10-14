"""One immutable musical plan shared by preview audio and MIDI."""

import math
from dataclasses import dataclass

from vega.model import StrumCharacter, StrumDirection
from vega.music.guitar import GuitarVoicing
from vega.music.strum import StrumGesture


@dataclass(frozen=True)
class StrumProfile:
    coverage: int
    velocity: int
    duration: float


PROFILES = {
    StrumCharacter.FULL: StrumProfile(6, 110, .80),
    StrumCharacter.NORMAL: StrumProfile(4, 90, .60),
    StrumCharacter.STRICT: StrumProfile(3, 72, .35),
}


@dataclass(frozen=True)
class ScheduledStringEvent:
    note: int
    string: int
    velocity: int
    offset: float
    duration: float

    def __post_init__(self) -> None:
        if any(type(value) is not int for value in (self.note, self.velocity, self.string)):
            raise ValueError("MIDI note, velocity and string must be integers")
        if not 0 <= self.note <= 127 or not 1 <= self.velocity <= 127 or not 1 <= self.string <= 6:
            raise ValueError("invalid MIDI note, velocity or guitar string")
        if not math.isfinite(self.offset) or self.offset < 0 or not math.isfinite(self.duration) or self.duration <= 0:
            raise ValueError("invalid note timing")


@dataclass(frozen=True)
class StrumPlan:
    direction: StrumDirection
    character: StrumCharacter
    notes: tuple[ScheduledStringEvent, ...]


def plan_strum(gesture: StrumGesture, voicing: GuitarVoicing, spread_ms: float = 10) -> StrumPlan:
    if not math.isfinite(spread_ms) or not 1 <= spread_ms <= 30:
        raise ValueError("string spread must be 1–30 ms")
    profile = PROFILES[gesture.character]
    strings = [s for s in voicing.strings if s.note is not None][-profile.coverage:]
    if gesture.direction is StrumDirection.LEFT:
        strings.reverse()
    return StrumPlan(gesture.direction, gesture.character, tuple(
        ScheduledStringEvent(s.note, s.string, profile.velocity, i * spread_ms / 1000, profile.duration)
        for i, s in enumerate(strings)
    ))
