"""Verified Titan PC+DP mapping and trigger-axis behavior."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vega.input.events import RawAxisEvent, RawButtonEvent, RawHatEvent
from vega.input.state import PhysicalState
from vega.input.titan_profile import TitanPcDpProfile
from vega.model import ButtonChange, ButtonControl, FaceChange, FaceControl, LeverChange


class TitanProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = TitanPcDpProfile()

    def test_all_eight_physical_faces(self) -> None:
        buttons = {
            2: FaceControl.FACE_1,
            3: FaceControl.FACE_2,
            5: FaceControl.FACE_3,
            4: FaceControl.FACE_4,
            0: FaceControl.FACE_5,
            1: FaceControl.FACE_6,
        }
        for button, face in buttons.items():
            with self.subTest(button=button):
                self.assertEqual(
                    self.profile.translate(RawButtonEvent(button, True, 1.0)),
                    FaceChange(face, True, 1.0),
                )
                self.assertEqual(
                    self.profile.translate(RawButtonEvent(button, False, 2.0)),
                    FaceChange(face, False, 2.0),
                )

        self.assertEqual(
            self.profile.translate(RawAxisEvent(5, 0.99, 3.0)),
            FaceChange(FaceControl.FACE_7, True, 3.0),
        )
        self.assertEqual(
            self.profile.translate(RawAxisEvent(4, 1.0, 4.0)),
            FaceChange(FaceControl.FACE_8, True, 4.0),
        )

    def test_axis_startup_release_press_and_tolerance(self) -> None:
        self.assertIsNone(self.profile.translate(RawAxisEvent(5, 0.0, 0.0)))
        self.assertIsNone(self.profile.translate(RawAxisEvent(5, -1.0000305185, 0.1)))
        self.assertIsNone(self.profile.translate(RawAxisEvent(5, -0.98, 0.2)))
        self.assertEqual(
            self.profile.translate(RawAxisEvent(5, 0.97, 0.3)),
            FaceChange(FaceControl.FACE_7, True, 0.3),
        )
        self.assertIsNone(self.profile.translate(RawAxisEvent(5, 1.0, 0.4)))
        self.assertIsNone(self.profile.translate(RawAxisEvent(5, 0.0, 0.5)))
        self.assertEqual(
            self.profile.translate(RawAxisEvent(5, -0.97, 0.6)),
            FaceChange(FaceControl.FACE_7, False, 0.6),
        )

    def test_verified_options_button_press_and_release(self) -> None:
        for pressed, timestamp in ((True, 1.0), (False, 2.0)):
            self.assertEqual(self.profile.translate(RawButtonEvent(7, pressed, timestamp)),
                             ButtonChange(ButtonControl.OPTIONS, pressed, timestamp))

    def test_options_state_is_separate_from_fingering_and_resets(self) -> None:
        state = PhysicalState()
        state.apply(FaceChange(FaceControl.FACE_1, True, 0))
        self.assertTrue(state.apply(ButtonChange(ButtonControl.OPTIONS, True, 1)))
        self.assertFalse(state.apply(ButtonChange(ButtonControl.OPTIONS, True, 2)))
        self.assertEqual(state.fingering, frozenset({FaceControl.FACE_1}))
        self.assertEqual(state.held_buttons, {ButtonControl.OPTIONS})
        state.reset()
        self.assertFalse(state.held_buttons)

    def test_axis_reset_clears_previous_press(self) -> None:
        self.profile.translate(RawAxisEvent(4, 1.0, 0.0))
        self.profile.reset()
        self.assertIsNone(self.profile.translate(RawAxisEvent(4, 0.0, 1.0)))
        self.assertIsNone(self.profile.translate(RawAxisEvent(4, -1.0, 1.1)))

    def test_dp_hat_and_unmapped_controls(self) -> None:
        for x in (-1, 0, 1):
            for y in (-1, 0, 1):
                with self.subTest(x=x, y=y):
                    self.assertEqual(
                        self.profile.translate(RawHatEvent(0, x, y, 1.0)),
                        LeverChange(x, y, 1.0),
                    )
        self.assertIsNone(self.profile.translate(RawHatEvent(1, 1, 0, 1.0)))
        self.assertIsNone(self.profile.translate(RawButtonEvent(10, True, 1.0)))
        self.assertIsNone(self.profile.translate(RawAxisEvent(0, 1.0, 1.0)))

    def test_symbolic_state_preserves_multiple_faces(self) -> None:
        state = PhysicalState()
        state.apply(FaceChange(FaceControl.FACE_1, True, 0.0))
        state.apply(FaceChange(FaceControl.FACE_7, True, 0.0))
        snapshot = state.fingering
        self.assertEqual(snapshot, frozenset({FaceControl.FACE_1, FaceControl.FACE_7}))
        self.assertFalse(state.apply(FaceChange(FaceControl.FACE_1, True, 0.1)))
        state.apply(FaceChange(FaceControl.FACE_1, False, 0.2))
        self.assertEqual(snapshot, frozenset({FaceControl.FACE_1, FaceControl.FACE_7}))
        self.assertEqual(state.fingering, frozenset({FaceControl.FACE_7}))


if __name__ == "__main__":
    unittest.main()
