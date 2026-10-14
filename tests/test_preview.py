"""Preview permission, failure containment, and bounded finite audition tones."""

import sys
import unittest
from array import array
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vega.audio.preview import (
    MAX_PREVIEW_VOICES, STRUM_PEAK, PREVIEW_PROFILES, PreviewSynth,
    preview_strum, render_strum, triangle,
)
from vega.audio.pygame_backend import PygameAudioBackend
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

    def play(self, strum, volume):
        self.requests.append((strum, volume))
        self.active.append(strum)

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
        self.assertEqual(len(backend.requests[0][0].notes), 4)
        preview.close()
        fresh = PreviewSynth(FakeAudio(), preview.volume)
        self.assertTrue(fresh.muted)

    def test_characters_select_preview_profiles(self):
        backend = FakeAudio()
        preview = PreviewSynth(backend)
        preview.set_muted(False)
        for character in StrumCharacter:
            preview.play(gesture(character))
        self.assertEqual([request[0].character for request in backend.requests], list(StrumCharacter))
        full, normal, strict = (PREVIEW_PROFILES[c] for c in (
            StrumCharacter.FULL, StrumCharacter.NORMAL, StrumCharacter.STRICT))
        self.assertGreater(full.duration, normal.duration)
        self.assertGreater(normal.duration, strict.duration)
        self.assertEqual([len(p.pitches) for p in (full, normal, strict)], [6, 4, 3])
        self.assertLess(full.pitches[0], normal.pitches[0])
        self.assertGreater(strict.pitches[0], normal.pitches[0])
        self.assertGreater(full.spacing, normal.spacing)
        self.assertGreater(normal.spacing, strict.spacing)
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

    def test_left_and_right_reverse_notes_with_spaced_onsets(self):
        for character in StrumCharacter:
            left = preview_strum(character, StrumDirection.LEFT)
            right = preview_strum(character, StrumDirection.RIGHT)
            self.assertEqual([n.pitch for n in left.notes], list(reversed([n.pitch for n in right.notes])))
            self.assertEqual([n.offset for n in left.notes], [n.offset for n in right.notes])
            self.assertEqual(right.notes[0].offset, 0)
            self.assertTrue(all(a.offset < b.offset for a, b in zip(right.notes, right.notes[1:])))
            self.assertNotEqual(render_strum(left, 8000), render_strum(right, 8000))

    def test_triangle_strums_have_finite_envelopes_and_overlap_headroom(self):
        self.assertEqual([triangle(p) for p in (0, 0.25, 0.5, 0.75, 1)], [-1, 0, 1, 0, -1])
        for character, profile in PREVIEW_PROFILES.items():
            for direction in StrumDirection:
                strum = preview_strum(character, direction)
                samples = array("h", render_strum(strum))
                self.assertEqual(len(samples), round(44100 * profile.duration) + round(44100 * strum.notes[-1].offset))
                self.assertEqual((samples[0], samples[-1]), (0, 0))
                peak = max(abs(n) for n in samples)
                self.assertAlmostEqual(peak / 32767, STRUM_PEAK, places=4)
                self.assertGreater(peak / 32767, 0.10)  # Louder than the old maximum at the same volume.
                self.assertLess(peak * MAX_PREVIEW_VOICES, 32767)

    def test_backend_uses_directional_cache_bounded_voices_and_panic(self):
        class Mixer:
            def __init__(self):
                self.active = []
                self.volume = 0
                self.ready = False

            def init(self, **kwargs): self.ready = True
            def get_init(self): return self.ready
            def set_num_channels(self, count): self.count = count
            def Sound(self, *, buffer): return buffer
            def find_channel(self, *, force): return self
            def set_volume(self, value): self.volume = value
            def play(self, sound): self.active.append(sound)
            def stop(self): self.active.clear()
            def quit(self): self.ready = False

        mixer = Mixer()
        with patch.dict(sys.modules, {"pygame": SimpleNamespace(mixer=mixer)}), \
             patch("vega.audio.pygame_backend.render_strum", side_effect=lambda s: (s.character, s.direction)):
            backend = PygameAudioBackend()
            backend.initialize()
        self.assertEqual(mixer.count, MAX_PREVIEW_VOICES)
        self.assertEqual(len(backend.sounds), 6)
        for direction in StrumDirection:
            backend.play(preview_strum(StrumCharacter.FULL, direction), 1)
        self.assertEqual(mixer.active, [(StrumCharacter.FULL, d) for d in StrumDirection])
        backend.stop()
        self.assertEqual(mixer.active, [])
        backend.close()
        self.assertFalse(mixer.ready)
