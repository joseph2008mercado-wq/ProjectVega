"""Preview permission, failure containment, and bounded finite audition tones."""

import sys
import unittest
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vega.audio.preview import PREVIEW_PROFILES, PreviewSynth, render_tone, triangle
from vega.model import StrumCharacter, StrumDirection
from vega.music.strum import StrumGesture


class FakeAudio:
    def __init__(self):
        self.requests = []
        self.active = []
        self.stops = 0
        self.closed = False

    def initialize(self):
        pass

    def play(self, character, volume):
        self.requests.append((character, volume))
        self.active.append(character)

    def set_volume(self, volume):
        self.volume = volume

    def stop(self):
        self.active.clear()
        self.stops += 1

    def close(self):
        self.stop()
        self.closed = True


def gesture(character=StrumCharacter.NORMAL):
    return StrumGesture(StrumDirection.LEFT, character, 1.0, frozenset())


class PreviewTests(unittest.TestCase):
    def test_each_launch_starts_muted(self):
        backend = FakeAudio()
        preview = PreviewSynth(backend)
        preview.play(gesture())
        self.assertEqual(backend.requests, [])
        preview.set_muted(False)
        preview.play(gesture())
        self.assertEqual(len(backend.requests), 1)
        preview.close()
        fresh = PreviewSynth(FakeAudio(), preview.volume)
        self.assertTrue(fresh.muted)

    def test_characters_select_preview_profiles(self):
        backend = FakeAudio()
        preview = PreviewSynth(backend)
        preview.set_muted(False)
        for character in StrumCharacter:
            preview.play(gesture(character))
        self.assertEqual([request[0] for request in backend.requests], list(StrumCharacter))
        full, normal, strict = (PREVIEW_PROFILES[c] for c in (
            StrumCharacter.FULL, StrumCharacter.NORMAL, StrumCharacter.STRICT))
        self.assertGreater(full.duration, normal.duration)
        self.assertGreater(normal.duration, strict.duration)
        self.assertLess(full.frequency, normal.frequency)
        self.assertGreater(strict.frequency, normal.frequency)
        self.assertGreater(full.octave_mix, 0)

    def test_panic_and_mute_stop_active_voices(self):
        backend = FakeAudio()
        preview = PreviewSynth(backend)
        preview.set_muted(False)
        preview.play(gesture())
        preview.panic()
        self.assertEqual(backend.active, [])
        preview.play(gesture())
        preview.set_muted(True)
        self.assertEqual(backend.active, [])

    def test_backend_failures_are_contained(self):
        class BrokenAudio(FakeAudio):
            def initialize(self):
                raise RuntimeError("device missing")

        preview = PreviewSynth(BrokenAudio())
        preview.set_muted(False)
        preview.play(gesture())
        self.assertFalse(preview.available)
        self.assertTrue(preview.muted)
        self.assertIn("device missing", preview.status)

        class LostAudio(FakeAudio):
            def play(self, character, volume):
                raise RuntimeError("device lost")

        preview = PreviewSynth(LostAudio())
        preview.set_muted(False)
        preview.play(gesture())
        self.assertFalse(preview.available)
        self.assertIn("device lost", preview.status)

    def test_triangle_tones_have_finite_envelopes_and_headroom(self):
        self.assertEqual([triangle(p) for p in (0, 0.25, 0.5, 0.75, 1)], [-1, 0, 1, 0, -1])
        for profile in PREVIEW_PROFILES.values():
            samples = array("h", render_tone(profile))
            self.assertEqual(len(samples), round(44100 * profile.duration))
            self.assertEqual((samples[0], samples[-1]), (0, 0))
            self.assertGreater(max(samples), 0)
            self.assertLessEqual(max(abs(n) for n in samples) * 8, 32767)
