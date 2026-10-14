"""Triangle audition of the shared musical plan, with a replaceable backend."""

from __future__ import annotations

import math
from array import array
from functools import lru_cache
from typing import Protocol

from vega.music.plan import StrumPlan
from vega.settings import DEFAULT_PREVIEW_VOLUME, bounded

# Six individual string channels per strum, three overlapping strum groups.
MAX_PREVIEW_VOICES = 3
STRUM_PEAK = 0.30


def triangle(phase: float) -> float:
    return 1.0 - 4.0 * abs((phase % 1.0) - 0.5)


@lru_cache(maxsize=8)
def _envelope(duration: float, sample_rate: int) -> tuple[float, ...]:
    count = round(sample_rate * duration)
    return tuple(min(1, i / (sample_rate * .0025)) * math.exp(-3 * i / count)
                 * min(1, (count - 1 - i) / (sample_rate * .025)) for i in range(count))


def render_note(note: int, duration: float, sample_rate: int = 44100) -> bytes:
    """PCM at a bounded per-string gain. Built before live polling begins."""
    frequency = 440 * 2 ** ((note - 69) / 12)
    gain = 32767 * STRUM_PEAK / 6
    return array("h", (round(triangle(i * frequency / sample_rate) * env * gain)
                       for i, env in enumerate(_envelope(duration, sample_rate)))).tobytes()


def render_strum(strum: StrumPlan, sample_rate: int = 44100) -> bytes:
    """Offline reference renderer for deterministic tests, not the live loop."""
    count = max((round(n.offset * sample_rate) + round(n.duration * sample_rate) for n in strum.notes), default=0)
    mixed = [0.0] * count
    for note in strum.notes:
        offset = round(note.offset * sample_rate)
        samples = array("h", render_note(note.note, note.duration, sample_rate))
        for i, sample in enumerate(samples):
            mixed[offset + i] += sample * note.velocity / 127
    return array("h", (round(sample) for sample in mixed)).tobytes()


class AudioBackend(Protocol):
    def initialize(self) -> None: ...
    def play(self, strum: StrumPlan, volume: float, now: float) -> None: ...
    def set_volume(self, volume: float) -> None: ...
    def stop(self) -> None: ...
    def close(self) -> None: ...


class PreviewSynth:
    """Only an explicit unmute permits playback; failures never escape to input."""

    def __init__(self, backend: AudioBackend, volume: float = DEFAULT_PREVIEW_VOLUME) -> None:
        self.backend = backend
        self.volume = bounded(volume, 0, 1, DEFAULT_PREVIEW_VOLUME)
        self.muted = True
        self.available = False
        self.error = ""
        try:
            backend.initialize()
            self.available = True
        except Exception as exc:
            self._failed(exc)

    @property
    def status(self) -> str:
        if not self.available:
            return f"Audio unavailable: {self.error}"
        return "Muted · strum preview ready" if self.muted else "Preview on · triangle strums"

    def _failed(self, exc: Exception) -> None:
        self.error = str(exc)
        self.available = False
        self.muted = True
        try:
            self.backend.close()
        except Exception:
            pass

    def set_muted(self, muted: bool) -> None:
        self.muted = bool(muted) or not self.available
        if self.muted:
            self.panic()

    def set_volume(self, volume: float) -> None:
        self.volume = bounded(volume, 0, 1, DEFAULT_PREVIEW_VOLUME)
        if self.available:
            try:
                self.backend.set_volume(self.volume)
            except Exception as exc:
                self._failed(exc)

    def play(self, plan: StrumPlan, now: float) -> None:
        if self.muted or not self.available:
            return
        try:
            self.backend.play(plan, self.volume, now)
        except Exception as exc:
            self._failed(exc)

    def tick(self, now: float) -> None:
        if self.available and hasattr(self.backend, "tick"):
            try:
                self.backend.tick(now)
            except Exception as exc:
                self._failed(exc)

    def panic(self) -> None:
        if self.available:
            try:
                self.backend.stop()
            except Exception as exc:
                self._failed(exc)

    def close(self) -> None:
        self.muted = True
        try:
            self.backend.close()
        except Exception as exc:
            self.error = str(exc)
        self.available = False
