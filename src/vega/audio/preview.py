"""Preview-only pitches and triangle tones, with a replaceable audio backend."""

from __future__ import annotations

import math
from array import array
from dataclasses import dataclass
from typing import Protocol

from vega.model import StrumCharacter
from vega.music.strum import StrumGesture
from vega.settings import bounded


@dataclass(frozen=True)
class PreviewProfile:
    frequency: float
    duration: float
    attack: float
    octave_mix: float = 0.0


# Audition tones only: no fingering vocabulary, chord meaning, or strings.
PREVIEW_PROFILES = {
    StrumCharacter.FULL: PreviewProfile(146.83, 0.48, 0.005, 0.16),
    StrumCharacter.NORMAL: PreviewProfile(196.0, 0.30, 0.004),
    StrumCharacter.STRICT: PreviewProfile(293.66, 0.16, 0.002),
}


def triangle(phase: float) -> float:
    return 1.0 - 4.0 * abs((phase % 1.0) - 0.5)


def render_tone(profile: PreviewProfile, sample_rate: int = 44100) -> bytes:
    """Bounded mono signed-16 PCM; short attack and zero-ending release."""
    samples = array("h")
    count = round(sample_rate * profile.duration)
    for index in range(count):
        t = index / sample_rate
        phase = t * profile.frequency
        wave = (triangle(phase) + profile.octave_mix * triangle(phase * 2)) / (1 + profile.octave_mix)
        envelope = min(1.0, t / profile.attack) * math.exp(-5 * t / profile.duration)
        envelope *= min(1.0, (count - 1 - index) / (sample_rate * 0.015))
        # Headroom for eight simultaneous voices, including FULL's harmonic.
        samples.append(round(32767 * 0.10 * envelope * wave))
    return samples.tobytes()


class AudioBackend(Protocol):
    def initialize(self) -> None: ...
    def play(self, character: StrumCharacter, volume: float) -> None: ...
    def set_volume(self, volume: float) -> None: ...
    def stop(self) -> None: ...
    def close(self) -> None: ...


class PreviewSynth:
    """Only an explicit unmute permits playback; failures never escape to input."""

    def __init__(self, backend: AudioBackend, volume: float = 0.35) -> None:
        self.backend = backend
        self.volume = bounded(volume, 0, 1, 0.35)
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
        return "Muted · preview ready" if self.muted else "Preview active · triangle"

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
        self.volume = bounded(volume, 0, 1, 0.35)
        if self.available:
            try:
                self.backend.set_volume(self.volume)
            except Exception as exc:
                self._failed(exc)

    def play(self, gesture: StrumGesture) -> None:
        if self.muted or not self.available:
            return
        try:
            self.backend.play(gesture.character, self.volume)
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
