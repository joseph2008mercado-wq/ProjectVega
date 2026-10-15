"""Editable mappings, persistence and pending-stroke safety without hardware."""

import json
import tempfile
import unittest
from pathlib import Path

from vega.music.fret_sets import FACTORY_FRET_SETS, FretSet, read_sets, validate_sets
from vega.music.harmony import FretSelection, interpret
from vega.music.guitar import STANDARD_TUNING, voice
from vega.model import FaceControl
from vega.settings import Settings, SettingsStore
from vega.runtime import DeviceStatus, VegaRuntime
from vega.audio.preview import PreviewSynth
from vega.midi.output import MidiOutput
from vega.input.events import RawButtonEvent, RawHatEvent
from test_runtime import FakeSource
from test_preview import FakeAudio
from test_midi import FakeMidi


class FretSetTests(unittest.TestCase):
    def test_exact_defaults(self):
        self.assertEqual([(s.name, s.frets) for s in FACTORY_FRET_SETS], [
            ("Chromatic", (1, 2, 3, 4, 5, 6, 7, 8)),
            ("Major / Dominant", (2, 4, 5, 7, 9, 10, 11, 12)),
            ("Minor / Blues", (2, 3, 5, 6, 7, 8, 10, 12))])

    def test_validation_and_immutability(self):
        for frets in ((1,) * 7, (1,) * 9, (0,) * 8, (25,) * 8, (1.5,) * 8, (True,) * 8, [1] * 8):
            with self.assertRaises(ValueError): FretSet("Test", frets)
        for name in ("", "  ", "x" * 41, None):
            with self.assertRaises(ValueError): FretSet(name, (1,) * 8)
        mapping = FretSet("  Custom  ", (24,) * 8)
        self.assertEqual(mapping.name, "Custom")
        with self.assertRaises(AttributeError): mapping.name = "Oops"
        for invalid in ((), FACTORY_FRET_SETS[:2], (*FACTORY_FRET_SETS, mapping), (mapping, mapping, None)):
            with self.assertRaises(ValueError): validate_sets(invalid)

    def test_all_faces_resolve_and_duplicates_deduplicate(self):
        mapping = FretSet("Chromatic", (5, 5, 24, 1, 13, 7, 9, 2))
        for face in FaceControl:
            self.assertEqual(FretSelection.from_faces(frozenset({face}), 2, mapping).frets,
                             (mapping.frets[face.value - 1],))
        faces = frozenset((FaceControl.FACE_1, FaceControl.FACE_2))
        selection = FretSelection.from_faces(faces, 2, mapping)
        self.assertEqual(selection.frets, (5,))
        self.assertEqual(interpret(selection).pitches, (45,))
        renamed = FretSet("Not a musical mode", mapping.frets)
        self.assertEqual(interpret(selection), interpret(FretSelection.from_faces(faces, 2, renamed)))

    def test_open_guitar_independent_of_set(self):
        for index, mapping in enumerate(FACTORY_FRET_SETS, 1):
            selection = FretSelection.from_faces(frozenset(), index, mapping)
            self.assertEqual(tuple(s.note for s in voice(interpret(selection)).strings), STANDARD_TUNING)

    def test_settings_round_trip_migration_and_unknown_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"settle_ms": 6, "preview_volume": .3, "spread_ms": 12,
                                        "future_preference": {"keep": True}, "muted": False}))
            store = SettingsStore(path)
            settings = store.load()
            self.assertEqual(settings.fret_sets, FACTORY_FRET_SETS)
            settings.fret_sets = (FretSet("Custom", (24,) * 8), *FACTORY_FRET_SETS[1:])
            settings.active_set = 3
            settings.midi_port, settings.midi_channel = "Missing cable", 16
            settings.window_geometry = "geometry"
            store.save(settings)
            self.assertEqual(store.load(), settings)
            data = json.loads(path.read_text())
            self.assertEqual(data["future_preference"], {"keep": True})
            self.assertNotIn("muted", data)
            data["fret_sets"][0]["frets"][0] = 0
            path.write_text(json.dumps(data))
            restored = store.load()
            self.assertEqual(restored.fret_sets, FACTORY_FRET_SETS)
            self.assertEqual((restored.settle_ms, restored.preview_volume, restored.spread_ms), (6, .3, 12))
            self.assertEqual((restored.midi_port, restored.midi_channel), ("Missing cable", 16))

    def test_malformed_persisted_values_default_safely(self):
        for value in (None, {}, [], [None] * 3, [1] * 3, [{"name": "x", "frets": "bad"}] * 3):
            self.assertEqual(read_sets(value), FACTORY_FRET_SETS)
        settings = Settings(active_set=True, midi_port=[], midi_channel=20, window_geometry=None)
        self.assertEqual((settings.active_set, settings.midi_port, settings.midi_channel, settings.window_geometry),
                         (1, "", 1, ""))


class FretSetRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.source, self.audio, self.backend = FakeSource(), FakeAudio(), FakeMidi()
        self.runtime = VegaRuntime(self.source, PreviewSynth(self.audio), Settings(), MidiOutput(self.backend))
        self.runtime.midi.connect("Vega Guitar")
        self.runtime.preview.set_muted(False)
        self.source.events = [DeviceStatus(True)]
        self.runtime.tick(0)

    def test_edit_pending_stroke_keeps_mapping_next_stroke_uses_edit(self):
        self.source.events = [RawButtonEvent(2, True, 1, 1), RawHatEvent(0, 1, 0, 1, 1)]
        self.runtime.tick(1)
        custom = (FretSet("New mapping", (24,) * 8), *FACTORY_FRET_SETS[1:])
        self.runtime.set_fret_sets(custom)
        self.assertEqual(self.runtime.snapshot().selection.frets, (24,))
        self.assertFalse(self.audio.requests)
        self.assertFalse(self.backend.messages)
        self.runtime.tick(1.009)
        self.assertEqual(self.runtime.latest_selection.frets, (1,))
        self.source.events = [RawHatEvent(0, 0, 0, 2, 1), RawHatEvent(0, -1, 0, 2.001, 1)]
        self.runtime.tick(2.01)
        self.assertEqual(self.runtime.latest_selection.frets, (24,))

    def test_edit_reset_and_duplicate_faces_are_silent(self):
        custom = (FretSet("Dup", (5,) * 8), *FACTORY_FRET_SETS[1:])
        self.runtime.set_fret_sets(custom)
        self.source.events = [RawButtonEvent(2, True, 1, 1), RawButtonEvent(3, True, 1, 1)]
        self.runtime.tick(1)
        self.assertEqual(len(self.runtime.snapshot().faces), 2)
        self.assertEqual(self.runtime.snapshot().selection.frets, (5,))
        self.runtime.set_fret_sets(FACTORY_FRET_SETS)
        with self.assertRaises(ValueError): self.runtime.set_fret_sets(custom[:2])
        self.assertEqual(self.runtime.settings.fret_sets, FACTORY_FRET_SETS)
        self.assertFalse(self.audio.requests)
        self.assertFalse(self.backend.messages)
        self.assertEqual(self.runtime.strum_count, 0)

    def test_panic_drops_pending_without_rearming_held_lever(self):
        self.source.events = [RawHatEvent(0, 1, 0, 1, 1)]
        self.runtime.tick(1)
        self.runtime.panic()
        self.runtime.panic()
        self.source.events = [RawHatEvent(0, 1, -1, 1.002, 1)]
        self.assertEqual(self.runtime.tick(2), [])
        self.assertFalse(self.audio.requests)
        self.assertFalse([m for m in self.backend.messages if m.kind == "note_on"])
        self.source.events = [RawHatEvent(0, 0, 0, 3, 1), RawHatEvent(0, 1, 0, 3.001, 1)]
        self.assertEqual(len(self.runtime.tick(3.02)), 1)

    def test_saved_active_set_and_channel_restore(self):
        settings = Settings(active_set=3, midi_channel=16)
        runtime = VegaRuntime(FakeSource(), PreviewSynth(FakeAudio()), settings, MidiOutput(FakeMidi()))
        self.assertEqual(runtime.bank, 3)
        self.assertEqual(runtime.snapshot().fret_set, FACTORY_FRET_SETS[2])
        self.assertEqual(runtime.midi.channel, 16)
        runtime.set_midi_channel(1)
        runtime.connect_midi("Other")
        self.assertEqual((settings.midi_channel, settings.midi_port), (1, "Other"))
