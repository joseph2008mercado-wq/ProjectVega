"""Editable input mappings, not musical modes or hardware profiles."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FretSet:
    name: str
    frets: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 40:
            raise ValueError("Fret Set name must contain 1–40 characters")
        if not isinstance(self.frets, tuple) or len(self.frets) != 8:
            raise ValueError("A Fret Set needs exactly eight slots")
        if any(type(f) is not int or not 1 <= f <= 24 for f in self.frets):
            raise ValueError("Each fret must be an integer from 1 to 24")
        object.__setattr__(self, "name", self.name.strip())


FACTORY_FRET_SETS = (
    FretSet("Chromatic", (1, 2, 3, 4, 5, 6, 7, 8)),
    FretSet("Major / Dominant", (2, 4, 5, 7, 9, 10, 11, 12)),
    FretSet("Minor / Blues", (2, 3, 5, 6, 7, 8, 10, 12)),
)


def validate_sets(sets: tuple[FretSet, ...]) -> tuple[FretSet, ...]:
    if not isinstance(sets, tuple) or len(sets) != 3 or not all(isinstance(s, FretSet) for s in sets):
        raise ValueError("Exactly three Fret Sets are required")
    return sets


def read_sets(value: object) -> tuple[FretSet, ...]:
    """Treat malformed persisted configuration atomically; never partially load."""
    try:
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError("Expected three saved sets")
        return validate_sets(tuple(FretSet(item["name"].strip() or f"Set {i + 1}",
                                           tuple(item["frets"])) for i, item in enumerate(value)))
    except (TypeError, ValueError, KeyError, AttributeError):
        return FACTORY_FRET_SETS
