"""Production profile/recognizer integration with deterministic input and audio."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vega.audio.preview import PreviewSynth
from vega.input.events import RawButtonEvent, RawHatEvent
from vega.model import FaceControl, StrumCharacter
from vega.runtime import DeviceStatus, VegaRuntime
from vega.settings import Settings
from test_preview import FakeAudio
from test_midi import FakeMidi
from vega.midi.output import MidiOutput
from vega.music.harmony import BankAction


class FakeSource:
    def __init__(self):
        self.events = []
        self.closed = False

    def poll(self, now):
        events, self.events = self.events, []
        return events

    def close(self):
        self.closed = True


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.source = FakeSource()
        self.audio = FakeAudio()
        self.preview = PreviewSynth(self.audio)
        self.runtime = VegaRuntime(self.source, self.preview, Settings())

    def test_bank_and_fret_changes_are_silent(self):
        self.connect()
        self.preview.set_muted(False)
        self.runtime.bank_action(BankAction.BANK_NEXT)
        self.assertEqual(self.runtime.bank, 2)
        self.source.events = [RawButtonEvent(2, True, 1, 1)]
        self.runtime.tick(1)
        self.assertEqual(self.runtime.snapshot().selection.frets, (9,))
        self.assertFalse(self.audio.requests)
        self.assertIsNone(self.runtime.latest_plan)

    def test_options_press_release_and_duplicate_press_advance_once(self):
        self.connect()
        self.source.events = [RawButtonEvent(7, True, 1, 1)]
        self.assertEqual(self.runtime.tick(1), [])
        self.assertEqual(self.runtime.bank, 2)
        self.source.events = [RawButtonEvent(7, True, 1.1, 1), RawButtonEvent(7, False, 1.2, 1)]
        self.assertEqual(self.runtime.tick(1.2), [])
        self.assertEqual(self.runtime.bank, 2)
        self.assertFalse(self.runtime.pipeline.state.fingering)

    def test_repeated_options_presses_cycle_banks_without_any_output(self):
        self.connect()
        self.preview.set_muted(False)
        midi = FakeMidi()
        self.runtime.midi = MidiOutput(midi)
        self.runtime.midi.connect("Vega Guitar")
        for timestamp, expected in ((1, 2), (2, 3), (3, 1)):
            self.source.events = [RawButtonEvent(7, True, timestamp, 1),
                                  RawButtonEvent(7, False, timestamp + .1, 1)]
            self.assertEqual(self.runtime.tick(timestamp + .1), [])
            self.assertEqual(self.runtime.bank, expected)
        self.assertFalse(self.audio.requests)
        self.assertFalse(midi.messages)
        self.assertFalse(self.runtime.midi.active)
        self.assertEqual(self.runtime.strum_count, 0)
        self.assertIsNone(self.runtime.latest_plan)
        self.assertFalse(self.runtime.pipeline.recognizer.has_pending)

    def test_options_queues_while_fingering_is_held(self):
        self.connect()
        self.source.events = [RawButtonEvent(2, True, 1, 1), RawButtonEvent(7, True, 1.1, 1)]
        self.assertEqual(self.runtime.tick(1.1), [])
        self.assertEqual(self.runtime.bank, 1)
        self.assertEqual(self.runtime.pending_bank, 2)
        self.assertEqual(self.runtime.snapshot().selection.frets, (1,))
        self.source.events = [RawButtonEvent(7, False, 1.2, 1), RawButtonEvent(2, False, 1.3, 1)]
        self.assertEqual(self.runtime.tick(1.3), [])
        self.assertEqual(self.runtime.bank, 2)
        self.assertIsNone(self.runtime.pending_bank)

    def test_options_queues_until_captured_stroke_finishes(self):
        self.connect()
        self.preview.set_muted(False)
        self.source.events = [RawButtonEvent(2, True, 1, 1), RawHatEvent(0, 1, -1, 1, 1),
                              RawButtonEvent(2, False, 1.001, 1), RawButtonEvent(7, True, 1.002, 1),
                              RawButtonEvent(7, False, 1.003, 1)]
        self.assertEqual(self.runtime.tick(1.003), [])
        self.assertEqual(self.runtime.bank, 1)
        self.assertEqual(self.runtime.pending_bank, 2)
        self.assertFalse(self.audio.requests)
        self.assertEqual(len(self.runtime.tick(1.009)), 1)
        self.assertEqual(self.runtime.latest_selection.frets, (1,))
        self.assertEqual(self.runtime.latest_selection.bank, 1)
        self.assertEqual(self.runtime.bank, 2)
        self.assertIsNone(self.runtime.pending_bank)
        self.assertEqual(len(self.audio.requests), 1)  # Only the earlier lever stroke sounds.

    def test_options_at_settle_deadline_keeps_previous_stroke_bank(self):
        self.connect()
        self.source.events = [RawButtonEvent(2, True, 1, 1), RawHatEvent(0, 1, 0, 1, 1),
                              RawButtonEvent(2, False, 1.001, 1)]
        self.runtime.tick(1.001)
        self.source.events = [RawButtonEvent(7, True, 1.009, 1)]
        self.assertEqual(len(self.runtime.tick(1.009)), 1)
        self.assertEqual(self.runtime.latest_selection.bank, 1)
        self.assertEqual(self.runtime.latest_selection.frets, (1,))
        self.assertEqual(self.runtime.bank, 2)

    def test_disconnect_rearms_options_press(self):
        self.connect()
        self.source.events = [RawButtonEvent(7, True, 1, 1), DeviceStatus(False),
                              DeviceStatus(True), RawButtonEvent(7, True, 2, 1)]
        self.assertEqual(self.runtime.tick(2), [])
        self.assertEqual(self.runtime.bank, 3)

    def test_bank_queue_protects_held_and_pending_stroke(self):
        self.connect()
        self.preview.set_muted(False)
        self.source.events = [RawButtonEvent(2, True, 1, 1), RawHatEvent(0, 1, -1, 1, 1)]
        self.runtime.tick(1)
        self.runtime.bank_action(BankAction.BANK_NEXT)
        self.assertEqual(self.runtime.bank, 1)
        self.assertEqual(self.runtime.pending_bank, 2)
        self.source.events = [RawButtonEvent(2, False, 1.002, 1)]
        self.runtime.tick(1.002)
        self.assertEqual(self.runtime.bank, 1)  # No faces, but old stroke still settling.
        self.runtime.tick(1.009)
        self.assertEqual(self.runtime.latest_selection.frets, (1,))
        self.assertEqual(self.runtime.bank, 2)
        self.assertIsNone(self.runtime.pending_bank)
        self.assertEqual(len(self.audio.requests), 1)

    def test_queued_bank_wrap_and_reset_on_disconnect(self):
        self.connect()
        self.source.events = [RawButtonEvent(2, True, 1, 1)]
        self.runtime.tick(1)
        for _ in range(3): self.runtime.bank_action(BankAction.BANK_NEXT)
        self.assertEqual(self.runtime.pending_bank, 1)
        self.source.events = [DeviceStatus(False)]
        self.runtime.tick(2)
        self.assertIsNone(self.runtime.pending_bank)
        self.assertEqual(VegaRuntime(FakeSource(), PreviewSynth(FakeAudio()), Settings()).bank, 1)

    def test_preview_and_midi_receive_identical_plan(self):
        backend = FakeMidi()
        self.runtime.midi = MidiOutput(backend)
        self.runtime.midi.connect("Vega Guitar")
        self.connect()
        self.preview.set_muted(False)
        self.runtime.set_settle_ms(0)
        self.source.events = [RawButtonEvent(2, True, 1, 1), RawButtonEvent(0, True, 1, 1),
                              RawHatEvent(0, 1, -1, 1, 1)]
        self.runtime.tick(1)
        plan = self.runtime.latest_plan
        self.assertIs(self.audio.requests[0][0], plan)
        self.runtime.tick(1.06)
        ons = [m for m in backend.messages if m.kind == "note_on"]
        self.assertEqual([m.note for m in ons], [n.note for n in plan.notes])
        self.assertEqual([m.velocity for m in ons], [n.velocity for n in plan.notes])
        self.runtime.panic()
        self.assertFalse(self.runtime.midi.active)
        self.assertFalse(self.audio.active)

    def test_output_epoch_is_after_planning_not_raw_acquisition(self):
        self.runtime.clock = lambda: 5.0
        backend = FakeMidi()
        self.runtime.midi = MidiOutput(backend)
        self.runtime.midi.connect("Vega Guitar")
        self.connect()
        self.source.events = [RawHatEvent(0, 1, -1, 1, 1)]
        self.runtime.tick(1.009)
        self.assertEqual(len([m for m in backend.messages if m.kind == "note_on"]), 1)
        self.assertAlmostEqual(min(item[0] for item in self.runtime.midi._queue), 5.01)

    def test_pending_bank_before_settle_with_two_strokes_in_one_batch(self):
        self.connect()
        self.source.events = [RawButtonEvent(2, True, 1, 1), RawHatEvent(0, 1, 0, 1, 1)]
        self.runtime.tick(1)
        self.runtime.bank_action(BankAction.BANK_NEXT)
        self.preview.set_muted(False)
        self.source.events = [RawButtonEvent(2, False, 1.001, 1), RawHatEvent(0, 0, 0, 1.002, 1),
                              RawButtonEvent(2, True, 1.003, 1), RawHatEvent(0, -1, 0, 1.004, 1)]
        result = self.runtime.tick(1.02)
        self.assertEqual(len(result), 2)
        self.assertEqual(self.runtime.latest_selection.frets, (9,))
        pitches = [{n.note % 12 for n in p.notes} for p, _ in self.audio.requests]
        self.assertEqual(pitches, [{5}, {1}])

    def connect(self):
        self.source.events = [DeviceStatus(True, "Titan", "Connected")]
        self.runtime.tick(0)

    def test_waiting_connect_disconnect_reconnect(self):
        self.assertFalse(self.runtime.snapshot().device.connected)
        self.connect()
        self.source.events = [RawButtonEvent(2, True, 1, 1), RawHatEvent(0, -1, -1, 1, 1)]
        self.runtime.tick(1)
        state = self.runtime.snapshot()
        self.assertEqual(state.faces, frozenset({FaceControl.FACE_1}))
        self.assertEqual((state.lever_x, state.lever_y), (-1, -1))
        self.source.events = [DeviceStatus(False)]
        self.runtime.tick(1.002)
        state = self.runtime.snapshot()
        self.assertFalse(state.device.connected)
        self.assertFalse(state.faces)
        self.assertEqual((state.lever_x, state.lever_y), (0, 0))
        self.assertEqual(self.runtime.tick(2), [])
        self.connect()
        self.assertTrue(self.runtime.snapshot().device.connected)

    def test_finalized_gesture_reaches_view_and_preview_once(self):
        self.connect()
        self.preview.set_muted(False)
        self.source.events = [RawButtonEvent(2, True, 1, 1), RawButtonEvent(3, True, 1, 1),
                              RawHatEvent(0, 1, -1, 1, 1)]
        self.assertEqual(self.runtime.tick(1), [])
        self.source.events = [RawButtonEvent(2, False, 1.002, 1)]
        self.assertEqual(self.runtime.tick(1.003), [])
        result = self.runtime.tick(1.009)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].character, StrumCharacter.FULL)
        self.assertEqual(result[0].fingering, frozenset({FaceControl.FACE_1, FaceControl.FACE_2}))
        self.assertEqual(self.runtime.snapshot().latest_strum, result[0])
        self.assertEqual(self.runtime.tick(2), [])
        self.assertEqual(self.runtime.snapshot().strum_count, 1)
        self.assertEqual(len(self.audio.requests), 1)

    def test_live_settle_changes_production_deadline(self):
        self.connect()
        self.source.events = [RawHatEvent(0, -1, 0, 1, 1)]
        self.runtime.tick(1)
        self.runtime.set_settle_ms(12)
        self.assertEqual(self.runtime.tick(1.009), [])
        self.runtime.set_settle_ms(4)
        self.assertEqual(self.runtime.pipeline.recognizer.settle_seconds, 0.004)
        self.assertEqual(len(self.runtime.tick(1.010)), 1)
        self.assertEqual(self.runtime.snapshot().settle_ms, 4)
        self.source.events = [RawHatEvent(0, 0, 0, 2, 1), RawHatEvent(0, 1, 0, 3, 1)]
        self.runtime.tick(3)
        self.assertEqual(self.runtime.tick(3.003), [])
        self.assertEqual(len(self.runtime.tick(3.005)), 1)

    def test_unplug_discards_ready_audio_in_same_batch(self):
        self.connect()
        self.preview.set_muted(False)
        self.runtime.set_settle_ms(0)
        self.source.events = [RawHatEvent(0, -1, 0, 1, 1), DeviceStatus(False)]
        self.assertEqual(self.runtime.tick(1), [])
        self.assertEqual(self.audio.requests, [])

    def test_audio_failure_does_not_stop_visual_input(self):
        self.connect()
        self.preview._failed(RuntimeError("no audio"))
        self.source.events = [RawHatEvent(0, -1, 0, 1, 1)]
        self.runtime.tick(1)
        self.assertEqual(len(self.runtime.tick(1.01)), 1)
        self.assertIsNotNone(self.runtime.snapshot().latest_strum)
        self.assertIn("no audio", self.runtime.snapshot().audio_status)

    def test_volume_and_shutdown(self):
        self.runtime.set_volume(8)
        self.assertEqual(self.runtime.snapshot().volume, 1)
        self.assertEqual(self.runtime.settings.preview_volume, 1)
        self.runtime.close()
        self.assertTrue(self.source.closed)
        self.assertTrue(self.audio.closed)
