"""Preferences require no GUI and never restore permission to make sound."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vega.settings import Settings, SettingsStore


class SettingsTests(unittest.TestCase):
    def test_defaults_and_clamps(self):
        self.assertEqual(Settings().settle_ms, 8)
        self.assertEqual(Settings().preview_volume, 0.65)
        self.assertEqual(Settings(preview_volume=4).preview_volume, 1)
        self.assertEqual(Settings(preview_volume=-2).preview_volume, 0)
        self.assertEqual(Settings(settle_ms=50).settle_ms, 20)
        self.assertEqual(Settings(settle_ms=float("nan")).settle_ms, 8)

    def test_round_trip_excludes_mute(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "nested" / "settings.json")
            store.save(Settings(12, 0.6))
            self.assertEqual(store.load(), Settings(12, 0.6))
            self.assertEqual(set(json.loads(store.path.read_text())), {"settle_ms", "preview_volume"})
            store.path.write_text('{"settle_ms": 6, "preview_volume": 0.7, "muted": false}')
            self.assertEqual(store.load(), Settings(6, 0.7))

    def test_missing_corrupt_and_unwritable_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = SettingsStore(path)
            self.assertEqual(store.load(), Settings())
            path.write_text("broken")
            self.assertEqual(store.load(), Settings())
            self.assertIn("could not be read", store.error)
            store = SettingsStore(path / "impossible.json")
            store.save(Settings())
            self.assertIn("could not be saved", store.error)
