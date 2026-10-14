"""Optional offscreen Qt checks; no controller, speakers, or visible window."""

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "desktop extra not installed")
class WindowTests(unittest.TestCase):
    def test_controls_update_runtime_and_close_cleanly(self):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        from vega.app.window import VegaWindow
        from vega.audio.preview import PreviewSynth
        from vega.runtime import VegaRuntime
        from vega.settings import Settings, SettingsStore
        from test_preview import FakeAudio
        from test_runtime import FakeSource

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            source = FakeSource()
            audio = FakeAudio()
            runtime = VegaRuntime(source, PreviewSynth(audio), Settings())
            window = VegaWindow(runtime, SettingsStore(Path(directory) / "settings.json"))
            window.show()
            app.processEvents()
            self.assertTrue(window.mute.isChecked())
            window.settle.setValue(6)
            self.assertEqual(runtime.pipeline.recognizer.settle_seconds, 0.006)
            window.mute.click()
            self.assertFalse(runtime.preview.muted)
            window.volume.setValue(50)
            self.assertEqual(runtime.preview.volume, 0.5)
            window.panic.click()
            self.assertGreater(audio.stops, 0)
            self.assertFalse(window.grab().isNull())
            window.resize(780, 580)
            app.processEvents()
            self.assertGreater(window.centralWidget().verticalScrollBar().maximum(), 0)
            window.close()
            self.assertTrue(source.closed)
            self.assertTrue(audio.closed)
            self.assertEqual(window.store.load().settle_ms, 6)
