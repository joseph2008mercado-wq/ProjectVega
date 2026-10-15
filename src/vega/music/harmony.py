"""Mapped fret selection and lossless, root-relative harmony interpretation."""

from dataclasses import dataclass
from enum import Enum, auto

from vega.model import FaceControl
from vega.music.fret_sets import FACTORY_FRET_SETS, FretSet

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def note_name(note: int) -> str:
    return f"{NOTE_NAMES[note % 12]}{note // 12 - 1}"


class BankAction(Enum):
    BANK_NEXT = auto()
    BANK_PREVIOUS = auto()


def next_bank(bank: int, action: BankAction) -> int:
    if bank not in (1, 2, 3):
        raise ValueError("bank must be 1, 2 or 3")
    step = 1 if action is BankAction.BANK_NEXT else -1
    return (bank - 1 + step) % 3 + 1


@dataclass(frozen=True)
class FretSelection:
    bank: int
    frets: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.bank not in (1, 2, 3) or any(not 1 <= f <= 24 for f in self.frets):
            raise ValueError("expected bank 1–3 and selected frets 1–24")

    @classmethod
    def from_faces(cls, faces: frozenset[FaceControl], bank: int,
                   fret_set: FretSet | None = None) -> "FretSelection":
        if bank not in (1, 2, 3):
            raise ValueError("Fret Set index must be 1–3")
        mapping = fret_set or FACTORY_FRET_SETS[bank - 1]
        return cls(bank, tuple(sorted({mapping.frets[face.value - 1] for face in faces})))


@dataclass(frozen=True)
class Harmony:
    pitches: tuple[int, ...]
    root: int | None
    pitch_classes: frozenset[int]
    intervals: tuple[int, ...]
    identity: str

    @property
    def label(self) -> str:
        return "Open strings" if self.root is None else f"{NOTE_NAMES[self.root % 12]} · {self.identity}"


CHORD_NAMES = {
    (0,): "Root / unison", (0, 7): "Fifth", (0, 4, 7): "Major",
    (0, 3, 7): "Minor", (0, 4, 7, 10): "Dominant 7",
    (0, 4, 7, 11): "Major 7", (0, 3, 7, 10): "Minor 7",
}


def interpret(selection: FretSelection) -> Harmony:
    pitches = tuple(sorted({40 + fret for fret in selection.frets}))
    if not pitches:
        return Harmony((), None, frozenset(), (), "Open")
    root = pitches[0]
    intervals = tuple(sorted({(pitch - root) % 12 for pitch in pitches}))
    return Harmony(pitches, root, frozenset(p % 12 for p in pitches), intervals,
                   CHORD_NAMES.get(intervals, "Custom"))
