"""Symbolic input and gesture types shared above the hardware profile."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class FaceControl(Enum):
    FACE_1 = auto()
    FACE_2 = auto()
    FACE_3 = auto()
    FACE_4 = auto()
    FACE_5 = auto()
    FACE_6 = auto()
    FACE_7 = auto()
    FACE_8 = auto()


class ButtonControl(Enum):
    OPTIONS = auto()


class StrumDirection(Enum):
    LEFT = auto()
    RIGHT = auto()


class StrumCharacter(Enum):
    FULL = auto()
    NORMAL = auto()
    STRICT = auto()


@dataclass(frozen=True)
class FaceChange:
    face: FaceControl
    pressed: bool
    timestamp: float


@dataclass(frozen=True)
class ButtonChange:
    control: ButtonControl
    pressed: bool
    timestamp: float


@dataclass(frozen=True)
class LeverChange:
    x: int
    y: int
    timestamp: float

    def __post_init__(self) -> None:
        if self.x not in (-1, 0, 1) or self.y not in (-1, 0, 1):
            raise ValueError("lever components must be -1, 0, or 1")


ControlChange = FaceChange | ButtonChange | LeverChange
