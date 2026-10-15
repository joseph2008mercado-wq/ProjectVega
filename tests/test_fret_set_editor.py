"""Qt editor staging and silent runtime integration."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

from vega.music.fret_sets import FACTORY_FRET_SETS, FretSet


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "desktop extra not installed")
class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_save_cancel_reset_and_limits(self):
        from vega.app.fret_set_editor import FretSetEditor
        from PySide6.QtWidgets import QDialogButtonBox
        custom = (FretSet("Custom", (24,) * 8), *FACTORY_FRET_SETS[1:])
        dialog = FretSetEditor(custom)
        dialog.show()
        self.app.processEvents()
        self.assertLessEqual(dialog.width(), 500)
        self.assertLessEqual(dialog.height(), 420)
        dialog.reset_this.click()
        self.assertEqual(tuple(s.value() for s in dialog.slots[0]), FACTORY_FRET_SETS[0].frets)
        self.assertEqual(dialog.result_sets, custom)
        dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel).click()
        self.assertEqual(dialog.result_sets, custom)
        dialog = FretSetEditor(custom)
        dialog.names[0].setText("  ")
        dialog.names[1].setText("  Duplicate  ")
        dialog.names[2].setText("  Duplicate  ")
        dialog.slots[0][0].setValue(5)
        dialog.slots[0][1].setValue(5)
        self.assertEqual(dialog.slots[0][0].minimum(), 1)
        self.assertEqual(dialog.slots[0][0].maximum(), 24)
        self.assertEqual(dialog.names[0].maxLength(), 40)
        dialog.buttons.button(QDialogButtonBox.StandardButton.Save).click()
        self.assertEqual(dialog.result_sets[0].name, "Set 1")
        self.assertEqual(dialog.result_sets[0].frets[:2], (5, 5))
        self.assertEqual(dialog.result_sets[1].name, "Duplicate")
        self.assertEqual(dialog.result_sets[2].name, "Duplicate")
        dialog = FretSetEditor(custom)
        dialog.reset_all.click()
        dialog.accept()
        self.assertEqual(dialog.result_sets, FACTORY_FRET_SETS)

    def test_window_editor_updates_labels_persists_and_never_plays(self):
        from vega.app.window import VegaWindow
        from vega.runtime import VegaRuntime
        from vega.audio.preview import PreviewSynth
        from vega.midi.output import MidiOutput
        from vega.settings import Settings, SettingsStore
        from test_runtime import FakeSource
        from test_preview import FakeAudio
        from test_midi import FakeMidi
        audio, midi = FakeAudio(), FakeMidi()
        runtime = VegaRuntime(FakeSource(), PreviewSynth(audio), Settings(), MidiOutput(midi))
        runtime.midi.connect("Vega Guitar")
        runtime.preview.set_muted(False)
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            window = VegaWindow(runtime, store)
            window.timer.stop()
            window.show()
            window.edit_sets.click()
            self.app.processEvents()
            self.assertTrue(window.editor.isVisible())
            window.editor.names[0].setText("My set")
            window.editor.slots[0][0].setValue(24)
            window.editor.accept()
            self.assertEqual(window.set_name.text(), "My set")
            self.assertEqual(window.faces.fret_labels[0], 24)
            self.assertEqual(store.load().fret_sets, runtime.settings.fret_sets)
            self.assertIn("QDialog { background:", window.styleSheet())
            self.assertIn("QLineEdit { color:", window.styleSheet())
            window.open_set_editor()
            window.editor.reset_all.click()
            window.editor.reject()
            self.assertEqual(window.faces.fret_labels[0], 24)
            window.bank_next.click()
            window.bank_previous.click()
            self.assertFalse(audio.requests)
            self.assertFalse(midi.messages)
            window.close()
