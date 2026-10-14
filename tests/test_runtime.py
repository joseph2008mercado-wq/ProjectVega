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
