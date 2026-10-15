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
    def test_geometry_policy_at_target_resolutions_and_dpi(self):
        from vega.app.geometry import initial_size
        for width, height in ((1280, 720), (1366, 768), (1920, 1080)):
            for scale in (1, 1.25, 1.5):
                available = (int(width / scale), int((height - 48) / scale))
                w, h = initial_size(*available)
                self.assertLess(w, available[0])
                self.assertLess(h, available[1])

    def test_music_midi_and_scroll_access_at_narrow_sizes(self):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication, QScrollArea
        from PySide6.QtCore import QPoint, QRect
        from vega.app.window import VegaWindow
        from vega.audio.preview import PreviewSynth
        from vega.input.events import RawButtonEvent
        from vega.runtime import DeviceStatus, VegaRuntime
        from vega.midi.output import MidiOutput
        from vega.settings import Settings, SettingsStore
        from test_preview import FakeAudio
        from test_runtime import FakeSource
        from test_midi import FakeMidi
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            source = FakeSource()
            runtime = VegaRuntime(source, PreviewSynth(FakeAudio()), Settings(), MidiOutput(FakeMidi()))
            window = VegaWindow(runtime, SettingsStore(Path(directory) / "settings.json"))
            window.timer.stop()
            window.show()
            app.processEvents()
            window.bank_next.click()
            self.assertEqual(window.faces.fret_labels, (2, 4, 5, 7, 9, 10, 11, 12))
            self.assertEqual(window.bank_label.text(), "Set 2 of 3")
            self.assertEqual(window.set_name.text(), "Major / Dominant")
            source.events = [DeviceStatus(True), RawButtonEvent(2, True, 1, 1)]
            runtime.tick(1)
            window.refresh()
            self.assertEqual(window.held_frets.text(), "Held frets: 2")
            self.assertIn("F#", window.harmony.text())
            self.assertTrue(all(w.text() for w in window.string_labels))
            window.midi_refresh.click()
            self.assertEqual(window.midi_port.count(), 3)
            window.connect_port(1)
            self.assertIn("Connected", window.midi_status.text())
            window.midi_channel.setValue(3)
            self.assertEqual(runtime.midi.channel, 3)
            window.spread.setValue(12)
            self.assertEqual(runtime.settings.spread_ms, 12)
            scroll = window.centralWidget()
            self.assertIsInstance(scroll, QScrollArea)
            self.assertTrue(scroll.widgetResizable())
            for width, height in ((900, 940), (860, 600), (780, 580), (640, 440), (480, 350), (360, 300)):
                window.resize(width, height)
                for _ in range(3): app.processEvents()
                self.assertEqual(scroll.horizontalScrollBar().maximum(), 0, (width, height))
                for widget in (window.bank_next, window.settle, window.spread, window.midi_port, window.midi_panic):
                    scroll.ensureWidgetVisible(widget)
                    app.processEvents()
                    rect = QRect(widget.mapTo(scroll.viewport(), QPoint(0, 0)), widget.size())
                    self.assertTrue(scroll.viewport().rect().contains(rect), (width, height, widget.objectName(), rect))
            window.close()

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
            self.assertEqual(window.windowTitle(), "Vega")
            self.assertFalse(window.windowIcon().pixmap(16, 16).isNull())
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
