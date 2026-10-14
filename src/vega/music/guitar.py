"""Six-string fretboard and a small deterministic, bounded voicing search."""

from dataclasses import dataclass
from functools import lru_cache

from vega.music.harmony import Harmony

STANDARD_TUNING = (40, 45, 50, 55, 59, 64)  # Strings 6 -> 1.


@dataclass(frozen=True)
class Fretboard:
    tuning: tuple[int, ...] = STANDARD_TUNING

    def __post_init__(self) -> None:
        if len(self.tuning) != 6 or any(not 0 <= n <= 103 for n in self.tuning):
            raise ValueError("six open MIDI pitches must allow frets 0–24")

    def note(self, string: int, fret: int) -> int:
        if not 1 <= string <= 6 or not 0 <= fret <= 24:
            raise ValueError("string must be 1–6 and fret 0–24")
        return self.tuning[6 - string] + fret


@dataclass(frozen=True)
class VirtualString:
    string: int
    note: int | None
    fret: int | None

    @property
    def state(self) -> str:
        return "muted" if self.note is None else "open" if self.fret == 0 else "fretted"


@dataclass(frozen=True)
class GuitarVoicing:
    strings: tuple[VirtualString, ...]  # Physical order: 6,5,4,3,2,1.


@lru_cache(maxsize=256)
def voice(harmony: Harmony, board: Fretboard = Fretboard()) -> GuitarVoicing:
    if harmony.root is None:
        return GuitarVoicing(tuple(VirtualString(s, board.note(s, 0), 0) for s in range(6, 0, -1)))
    pcs = harmony.pitch_classes
    root = harmony.root % 12
    best_key = None
    best = None
    def rank(frets: tuple[int | None, ...]) -> tuple:
        sounding = [(board.tuning[i] + f, f) for i, f in enumerate(frets) if f is not None]
        if not sounding:
            return (10000, ())
        notes = [n for n, _ in sounding]
        if notes != sorted(notes):
            return (20000, ())
        stopped = [f for _, f in sounding if f]
        span = max(stopped) - min(stopped) if stopped else 0
        cost = (1000 * len(pcs - {n % 12 for n in notes}) + 120 * (notes[0] % 12 != root)
                + 12 * (len(frets) - len(notes)) + 2 * span + sum(stopped) * .1 + notes[0] * .02)
        return (cost, tuple(25 if f is None else f for f in frets))

    # Bounded beam search: retain 8 candidates after each string. It is a
    # deterministic heuristic, not a promise of a globally optimal fingering.
    # Fretted notes fit a five-fret window; open strings may ring outside it.
    for start in range(1, 21):
        choices = []
        for string in range(6, 0, -1):
            frets = (0, *range(start, start + 5))
            choices.append(tuple(f for f in frets if board.note(string, f) % 12 in pcs) + (None,))
        candidates = [()]
        for options in choices:
            candidates = sorted((c + (f,) for c in candidates for f in options), key=rank)[:8]
        for frets in candidates:
            key = rank(frets)
            if best_key is None or key < best_key:
                best_key, best = key, frets
    assert best is not None  # Every pitch class occurs on every string within 24 frets.
    return GuitarVoicing(tuple(VirtualString(6 - i, None if f is None else board.tuning[i] + f, f)
                              for i, f in enumerate(best)))
