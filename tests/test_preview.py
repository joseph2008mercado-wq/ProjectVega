"""Shared-plan audition, muted startup, envelopes and bounded SDL scheduling."""

import sys
import unittest
from array import array
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vega.audio.preview import MAX_PREVIEW_VOICES, STRUM_PEAK, PreviewSynth, render_strum, triangle
from vega.audio.pygame_backend import PygameAudioBackend
from vega.model import StrumCharacter, StrumDirection
from vega.music.strum import StrumGesture
from vega.music.harmony import FretSelection, interpret
from vega.music.guitar import voice
from vega.music.plan import PROFILES, plan_strum


class FakeAudio:
    def __init__(self):
        self.requests = []
        self.active = []
        self.stops = 0
        self.closed = False

    def initialize(self): pass

    def play(self, strum, volume, now):
        self.requests.append((strum, volume))
        self.active.append(strum)

    def set_volume(self, volume): self.volume = volume

    def stop(self):
        self.active.clear()
        self.stops += 1

    def close(self):
        self.stop()
        self.closed = True


def sample_plan(character=StrumCharacter.NORMAL, direction=StrumDirection.LEFT, frets=()):
    gesture = StrumGesture(direction, character, 1, frozenset())
    return plan_strum(gesture, voice(interpret(FretSelection(1, frets))))


class PreviewTests(unittest.TestCase):
    def test_each_launch_starts_muted(self):
        backend = FakeAudio()
        preview = PreviewSynth(backend)
        plan = sample_plan()
        preview.play(plan, 0)
        self.assertEqual(backend.requests, [])
        preview.set_muted(False)
        preview.play(plan, 0)
        self.assertIs(backend.requests[0][0], plan)
        self.assertEqual(len(plan.notes), 4)
        preview.close()
        self.assertTrue(PreviewSynth(FakeAudio(), preview.volume).muted)

    def test_actual_harmony_not_a_fixed_chord(self):
        backend = FakeAudio()
        preview = PreviewSynth(backend)
        preview.set_muted(False)
        for frets in ((), (1, 5, 8), (3, 7, 10)):
            plan = sample_plan(StrumCharacter.FULL, frets=frets)
            preview.play(plan, 1)
            self.assertIs(backend.requests[-1][0], plan)
        pitches = [tuple(n.note for n in p.notes) for p, _ in backend.requests]
        self.assertEqual(len(set(pitches)), 3)

    def test_panic_and_mute_stop_active_voices(self):
        backend = FakeAudio()
        preview = PreviewSynth(backend)
        preview.set_muted(False)
        preview.play(sample_plan(), 0)
        preview.panic()
        self.assertEqual(backend.active, [])
        preview.play(sample_plan(), 0)
        preview.set_muted(True)
        self.assertEqual(backend.active, [])

    def test_backend_failures_are_contained(self):
        class BrokenAudio(FakeAudio):
            def initialize(self): raise RuntimeError("device missing")
        preview = PreviewSynth(BrokenAudio())
        preview.set_muted(False)
        preview.play(sample_plan(), 0)
        self.assertFalse(preview.available)
        self.assertTrue(preview.muted)
        self.assertIn("device missing", preview.status)

        class LostAudio(FakeAudio):
            def play(self, *args): raise RuntimeError("device lost")
        preview = PreviewSynth(LostAudio())
        preview.set_muted(False)
        preview.play(sample_plan(), 0)
        self.assertFalse(preview.available)
        self.assertIn("device lost", preview.status)

    def test_left_and_right_reverse_notes_with_spaced_onsets(self):
        for character in StrumCharacter:
            left = sample_plan(character, StrumDirection.LEFT)
            right = sample_plan(character, StrumDirection.RIGHT)
            self.assertEqual([n.note for n in left.notes], list(reversed([n.note for n in right.notes])))
            self.assertEqual([n.offset for n in left.notes], [n.offset for n in right.notes])
            self.assertNotEqual(render_strum(left, 8000), render_strum(right, 8000))

    def test_triangle_strums_have_finite_envelopes_and_overlap_headroom(self):
        self.assertEqual([triangle(p) for p in (0, .25, .5, .75, 1)], [-1, 0, 1, 0, -1])
        for character, profile in PROFILES.items():
            for direction in StrumDirection:
                plan = sample_plan(character, direction)
                samples = array("h", render_strum(plan, 8000))
                self.assertEqual(len(samples), round(8000 * profile.duration) + round(8000 * plan.notes[-1].offset))
                self.assertEqual((samples[0], samples[-1]), (0, 0))
                peak = max(abs(n) for n in samples)
                self.assertGreater(peak, 50)
                self.assertLessEqual(peak / 32767, STRUM_PEAK)
                self.assertLess(peak * MAX_PREVIEW_VOICES, 32767)

    def test_backend_uses_note_cache_bounded_groups_and_panic(self):
        class Channel:
            def __init__(self): self.played = []
            def play(self, sound): self.played.append(sound)
            def stop(self): self.played.clear()
            def set_volume(self, value): self.volume = value
        class Mixer:
            def init(self, **kwargs): self.ready = True
            def get_init(self): return self.ready
            def set_num_channels(self, count): self.channels = [Channel() for _ in range(count)]
            def Sound(self, *, buffer): return buffer
            def Channel(self, index): return self.channels[index]
            def stop(self):
                for c in self.channels: c.stop()
            def quit(self): self.ready = False
        mixer = Mixer()
        with patch.dict(sys.modules, {"pygame": SimpleNamespace(mixer=mixer)}), \
             patch("vega.audio.pygame_backend.render_note", side_effect=lambda n, d: (n, d)):
            backend = PygameAudioBackend()
            backend.initialize()
        self.assertEqual(len(mixer.channels), 18)
        self.assertEqual(len(backend.sounds), 384)
        plan = sample_plan(StrumCharacter.FULL, StrumDirection.RIGHT)
        backend.play(plan, 1, 10)
        backend.tick(10)
        self.assertEqual(mixer.channels[0].played, [(40, .8)])
        self.assertFalse(mixer.channels[1].played)
        backend.tick(10.051)
        self.assertEqual([c.played[0][0] for c in mixer.channels[:6]], [n.note for n in plan.notes])
        for i in range(4): backend.play(plan, 1, 11 + i * .001)
        self.assertLessEqual(len(backend.queue), 18)
        backend.stop()
        backend.tick(100)
        self.assertFalse(backend.queue)
        self.assertTrue(all(not c.played for c in mixer.channels))
        backend.close()
        self.assertFalse(mixer.ready)
        self.assertFalse(backend.sounds)
        backend.close()
