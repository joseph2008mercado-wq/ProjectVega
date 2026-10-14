"""Deterministic horizontal-acquisition and diagonal-transition tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vega.input.events import RawAxisEvent, RawButtonEvent, RawHatEvent
from vega.input.pipeline import VegaInputPipeline
from vega.model import FaceControl, StrumCharacter, StrumDirection


def play_hats(*positions: tuple[int, int], step: float = 0.002) -> list:
    pipeline = VegaInputPipeline()
    gestures = []
    for index, (x, y) in enumerate(positions):
        gestures.extend(pipeline.on_raw(RawHatEvent(0, x, y, index * step)))
    gestures.extend(pipeline.flush(len(positions) * step + 1.0))
    return gestures


def labels(gestures: list) -> list[tuple[StrumDirection, StrumCharacter]]:
    return [(gesture.direction, gesture.character) for gesture in gestures]


class StrumTests(unittest.TestCase):
    def test_basic_left_and_right_normal(self) -> None:
        self.assertEqual(
            labels(play_hats((0, 0), (-1, 0))),
            [(StrumDirection.LEFT, StrumCharacter.NORMAL)],
        )
        self.assertEqual(
            labels(play_hats((0, 0), (1, 0))),
            [(StrumDirection.RIGHT, StrumCharacter.NORMAL)],
        )

    def test_face_changes_alone_do_not_strum(self) -> None:
        pipeline = VegaInputPipeline()
        self.assertEqual(pipeline.on_raw(RawButtonEvent(2, True, 0.0)), [])
        self.assertEqual(pipeline.on_raw(RawAxisEvent(5, 1.0, 0.1)), [])
        self.assertEqual(pipeline.flush(1.0), [])
        self.assertEqual(
            pipeline.state.fingering,
            frozenset({FaceControl.FACE_1, FaceControl.FACE_7}),
        )

    def test_same_side_does_not_retrigger(self) -> None:
        self.assertEqual(
            labels(play_hats((0, 0), (-1, 0), (-1, 0), (-1, 0))),
            [(StrumDirection.LEFT, StrumCharacter.NORMAL)],
        )

    def test_horizontal_zero_rearms(self) -> None:
        self.assertEqual(
            labels(play_hats((-1, 0), (0, 0), (-1, 0))),
            [(StrumDirection.LEFT, StrumCharacter.NORMAL)] * 2,
        )

    def test_alternating_normal_strokes(self) -> None:
        self.assertEqual(
            labels(play_hats((0, 0), (-1, 0), (0, 0), (1, 0), (0, 0), (-1, 0))),
            [
                (StrumDirection.LEFT, StrumCharacter.NORMAL),
                (StrumDirection.RIGHT, StrumCharacter.NORMAL),
                (StrumDirection.LEFT, StrumCharacter.NORMAL),
            ],
        )

    def test_strict_rearms_at_up_without_full_center(self) -> None:
        self.assertEqual(
            labels(play_hats((0, 1), (-1, 1), (0, 1), (1, 1), (0, 1), (-1, 1))),
            [
                (StrumDirection.LEFT, StrumCharacter.STRICT),
                (StrumDirection.RIGHT, StrumCharacter.STRICT),
                (StrumDirection.LEFT, StrumCharacter.STRICT),
            ],
        )

    def test_full_rearms_at_down_without_full_center(self) -> None:
        self.assertEqual(
            labels(play_hats((0, -1), (-1, -1), (0, -1), (1, -1), (0, -1), (-1, -1))),
            [
                (StrumDirection.LEFT, StrumCharacter.FULL),
                (StrumDirection.RIGHT, StrumCharacter.FULL),
                (StrumDirection.LEFT, StrumCharacter.FULL),
            ],
        )

    def test_vertical_only_creates_no_strokes(self) -> None:
        self.assertEqual(play_hats((0, 0), (0, 1), (0, 0), (0, -1), (0, 0)), [])
        self.assertEqual(play_hats((0, 1), (0, -1)), [])

    def test_intermediate_cardinals_produce_one_diagonal_stroke(self) -> None:
        cases = [
            ([(0, 0), (0, -1), (-1, -1)], StrumDirection.LEFT, StrumCharacter.FULL),
            ([(0, 0), (-1, 0), (-1, 1)], StrumDirection.LEFT, StrumCharacter.STRICT),
            ([(0, 0), (0, 1), (1, 1)], StrumDirection.RIGHT, StrumCharacter.STRICT),
            ([(0, 0), (1, 0), (1, -1)], StrumDirection.RIGHT, StrumCharacter.FULL),
            ([(0, 1), (-1, 1), (-1, 0), (0, 0)], StrumDirection.LEFT, StrumCharacter.STRICT),
            ([(0, -1), (1, -1), (1, 0), (0, 0)], StrumDirection.RIGHT, StrumCharacter.FULL),
        ]
        for positions, direction, character in cases:
            with self.subTest(positions=positions):
                self.assertEqual(labels(play_hats(*positions)), [(direction, character)])

    def test_direct_side_change_requires_horizontal_zero_to_rearm(self) -> None:
        self.assertEqual(
            labels(play_hats((0, 0), (-1, 0), (1, 0), (1, 1))),
            [(StrumDirection.LEFT, StrumCharacter.NORMAL)],
        )

    def test_settle_window_is_deterministic_and_configurable(self) -> None:
        pipeline = VegaInputPipeline(settle_seconds=0.008)
        self.assertEqual(pipeline.on_raw(RawHatEvent(0, -1, 0, 1.0)), [])
        self.assertEqual(pipeline.on_raw(RawHatEvent(0, -1, 1, 1.004)), [])
        gestures = pipeline.flush(1.008)
        self.assertEqual(labels(gestures), [(StrumDirection.LEFT, StrumCharacter.STRICT)])
        self.assertEqual(gestures[0].timestamp, 1.0)

        pipeline = VegaInputPipeline(settle_seconds=0.008)
        pipeline.on_raw(RawHatEvent(0, 1, 0, 2.0))
        gestures = pipeline.on_raw(RawHatEvent(0, 1, -1, 2.020))
        self.assertEqual(labels(gestures), [(StrumDirection.RIGHT, StrumCharacter.NORMAL)])
        self.assertEqual(pipeline.flush(3.0), [])

    def test_short_tap_is_not_lost(self) -> None:
        pipeline = VegaInputPipeline(settle_seconds=0.008)
        pipeline.on_raw(RawHatEvent(0, -1, 0, 1.0))
        gestures = pipeline.on_raw(RawHatEvent(0, 0, 0, 1.002))
        self.assertEqual(labels(gestures), [(StrumDirection.LEFT, StrumCharacter.NORMAL)])
        self.assertEqual(pipeline.flush(2.0), [])

    def test_fingering_is_snapshotted_at_horizontal_acquisition(self) -> None:
        pipeline = VegaInputPipeline()
        pipeline.on_raw(RawButtonEvent(2, True, 0.0))
        pipeline.on_raw(RawButtonEvent(3, True, 0.001))
        pipeline.on_raw(RawAxisEvent(5, 1.0, 0.002))
        pipeline.on_raw(RawHatEvent(0, -1, 0, 0.003))
        pipeline.on_raw(RawButtonEvent(2, False, 0.004))
        pipeline.on_raw(RawButtonEvent(0, True, 0.005))
        gesture = pipeline.flush(0.020)[0]
        self.assertEqual(
            gesture.fingering,
            frozenset({FaceControl.FACE_1, FaceControl.FACE_2, FaceControl.FACE_7}),
        )
        self.assertEqual(
            pipeline.state.fingering,
            frozenset({FaceControl.FACE_2, FaceControl.FACE_5, FaceControl.FACE_7}),
        )

    def test_reset_drops_pending_stroke_and_physical_state(self) -> None:
        pipeline = VegaInputPipeline()
        pipeline.on_raw(RawButtonEvent(2, True, 0.0))
        pipeline.on_raw(RawHatEvent(0, -1, 0, 0.001))
        pipeline.reset()
        self.assertEqual(pipeline.flush(1.0), [])
        self.assertEqual(pipeline.state.fingering, frozenset())
        self.assertEqual((pipeline.state.lever_x, pipeline.state.lever_y), (0, 0))


if __name__ == "__main__":
    unittest.main()
