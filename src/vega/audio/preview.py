"""Preview-only pitches and triangle tones, with a replaceable audio backend."""

from __future__ import annotations

import math
from array import array
from dataclasses import dataclass
from typing import Protocol

from vega.model import StrumCharacter, StrumDirection
from vega.music.strum import StrumGesture
from vega.settings import DEFAULT_PREVIEW_VOLUME, bounded


@dataclass(frozen=True)
class PreviewProfile:
    pitches: tuple[int, ...]
    spacing: float
    duration: float
    attack: float
    octave_mix: float = 0.12


# Fixed E-major audition pitches only. These never interpret held fingerings
# and do not constrain the future guitar engine or its direction conventions.
PREVIEW_PROFILES = {
    StrumCharacter.FULL: PreviewProfile((40, 47, 52, 56, 59, 64), 0.012, 0.80, 0.0025, 0.16),
    StrumCharacter.NORMAL: PreviewProfile((47, 52, 56, 59), 0.009, 0.60, 0.002),
    StrumCharacter.STRICT: PreviewProfile((56, 59, 64), 0.006, 0.35, 0.0015, 0.08),
}

# Each complete strum is one mixer voice, including all delayed note onsets.
# Even three perfectly aligned peaks at volume=1 stay below full scale.
MAX_PREVIEW_VOICES = 3
STRUM_PEAK = 0.30


@dataclass(frozen=True)
class PreviewNote:
    pitch: int
    offset: float


@dataclass(frozen=True)
class PreviewStrum:
    character: StrumCharacter
    direction: StrumDirection
    notes: tuple[PreviewNote, ...]


def preview_strum(character: StrumCharacter, direction: StrumDirection) -> PreviewStrum:
    profile = PREVIEW_PROFILES[character]
    pitches = profile.pitches if direction is StrumDirection.RIGHT else tuple(reversed(profile.pitches))
    return PreviewStrum(character, direction, tuple(
        PreviewNote(pitch, index * profile.spacing) for index, pitch in enumerate(pitches)
    ))


def triangle(phase: float) -> float:
    return 1.0 - 4.0 * abs((phase % 1.0) - 0.5)


def render_strum(strum: PreviewStrum, sample_rate: int = 44100) -> bytes:
    """Pre-render note offsets, then peak-normalize the entire strum once.

    No live note scheduling or limiter callback. A triangle foundation with
    quiet sine harmonics and a slower decay adds attack and body. The bounded
    mixer voice count is part of this gain contract, not an arbitrary setting.
    """
    profile = PREVIEW_PROFILES[strum.character]
    count = round(sample_rate * profile.duration)
    mixed = [0.0] * (count + round(strum.notes[-1].offset * sample_rate))
    for note in strum.notes:
        offset = round(note.offset * sample_rate)
        frequency = 440 * 2 ** ((note.pitch - 69) / 12)
        for index in range(count):
            t = index / sample_rate
            phase = t * frequency
            wave = triangle(phase) + profile.octave_mix * math.sin(4 * math.pi * phase)
            wave += 0.045 * math.sin(6 * math.pi * phase) * math.exp(-t / 0.035)
            envelope = min(1.0, t / profile.attack) * math.exp(-3 * t / profile.duration)
            envelope *= min(1.0, (count - 1 - index) / (sample_rate * 0.025))
            mixed[offset + index] += wave * envelope
    peak = max(abs(sample) for sample in mixed)
    gain = 32767 * STRUM_PEAK / peak if peak else 0
    return array("h", (round(sample * gain) for sample in mixed)).tobytes()


class AudioBackend(Protocol):
    def initialize(self) -> None: ...
    def play(self, strum: PreviewStrum, volume: float) -> None: ...
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
            pass  # Original backend failure is the useful status.

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

    def play(self, gesture: StrumGesture) -> None:
        if self.muted or not self.available:
            return
        try:
            self.backend.play(preview_strum(gesture.character, gesture.direction), self.volume)
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
