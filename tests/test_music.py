"""Pure musical invariants: no Qt, hardware, audio device or clock sleeps."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vega.model import FaceControl, StrumCharacter, StrumDirection
from vega.music.harmony import BankAction, FretSelection, interpret, next_bank
from vega.music.guitar import Fretboard, STANDARD_TUNING, voice
from vega.music.plan import ScheduledStringEvent, plan_strum
from vega.music.strum import StrumGesture


class MusicTests(unittest.TestCase):
    def test_three_banks_arithmetic_and_wrap(self):
        for bank in (1, 2, 3):
            self.assertEqual(FretSelection.from_faces(frozenset(FaceControl), bank).frets,
                             tuple(range((bank - 1) * 8 + 1, bank * 8 + 1)))
        self.assertEqual(next_bank(3, BankAction.BANK_NEXT), 1)
        self.assertEqual(next_bank(1, BankAction.BANK_PREVIOUS), 3)
        with self.assertRaises(ValueError): next_bank(0, BankAction.BANK_NEXT)

    def test_fretboard_landmarks_and_configurable_tuning(self):
        board = Fretboard()
        for fret in (0, 1, 12, 24):
            self.assertEqual(tuple(board.note(s, fret) for s in range(6, 0, -1)),
                             tuple(n + fret for n in STANDARD_TUNING))
        self.assertEqual(Fretboard((38, 45, 50, 55, 59, 64)).note(6, 12), 50)
        for s, f in ((0, 1), (7, 1), (1, -1), (1, 25)):
            with self.assertRaises(ValueError): board.note(s, f)

    def test_harmony_recognizes_common_intervals(self):
        cases = {(0,): "Root / unison", (0, 7): "Fifth", (0, 4, 7): "Major",
                 (0, 3, 7): "Minor", (0, 4, 7, 10): "Dominant 7",
                 (0, 4, 7, 11): "Major 7", (0, 3, 7, 10): "Minor 7"}
        for intervals, name in cases.items():
            harmony = interpret(FretSelection(1, tuple(1 + i for i in intervals)))
            self.assertEqual(harmony.root, 41)
            self.assertEqual(harmony.intervals, intervals)
            self.assertEqual(harmony.identity, name)

    def test_custom_and_octave_pitches_preserved(self):
        harmony = interpret(FretSelection(1, (3, 4, 15)))
        self.assertEqual(harmony.pitches, (43, 44, 55))
        self.assertEqual(harmony.pitch_classes, frozenset((7, 8)))
        self.assertEqual(harmony.intervals, (0, 1))
        self.assertEqual(harmony.identity, "Custom")

    def test_open_strings_in_every_bank(self):
        for bank in (1, 2, 3):
            voicing = voice(interpret(FretSelection(bank, ())))
            self.assertEqual(tuple(s.note for s in voicing.strings), STANDARD_TUNING)
            self.assertTrue(all(s.state == "open" for s in voicing.strings))

    def test_voicings_valid_compact_deterministic_root_bass(self):
        for root in range(1, 13):
            for intervals in ((0,), (0, 7), (0, 4, 7), (0, 3, 7), (0, 4, 7, 10), (0, 1, 2)):
                harmony = interpret(FretSelection(1, tuple(root + n for n in intervals)))
                voicing = voice(harmony)
                self.assertEqual(voicing, voice(harmony))
                self.assertEqual(tuple(s.string for s in voicing.strings), (6, 5, 4, 3, 2, 1))
                sounding = [s for s in voicing.strings if s.note is not None]
                self.assertTrue(sounding)
                self.assertEqual(sounding[0].note % 12, harmony.root % 12)
                self.assertEqual([s.note for s in sounding], sorted(s.note for s in sounding))
                for string in sounding:
                    self.assertIn(string.note % 12, harmony.pitch_classes)
                    self.assertTrue(0 <= string.fret <= 24)
                    self.assertTrue(0 <= string.note <= 127)
                    self.assertEqual(string.note, Fretboard().note(string.string, string.fret))
                stopped = [s.fret for s in sounding if s.fret]
                if stopped: self.assertLessEqual(max(stopped) - min(stopped), 4)

    def test_strum_coverage_velocity_order_offsets(self):
        voicing = voice(interpret(FretSelection(1, ())))
        for character, coverage, velocity in ((StrumCharacter.FULL, 6, 110),
                                              (StrumCharacter.NORMAL, 4, 90),
                                              (StrumCharacter.STRICT, 3, 72)):
            plans = []
            for direction in StrumDirection:
                gesture = StrumGesture(direction, character, 1, frozenset())
                plan = plan_strum(gesture, voicing, 12)
                self.assertEqual(len(plan.notes), coverage)
                self.assertTrue(all(n.velocity == velocity for n in plan.notes))
                for i, n in enumerate(plan.notes): self.assertAlmostEqual(n.offset, i * .012)
                plans.append(plan)
            self.assertEqual([n.string for n in plans[0].notes], list(reversed([n.string for n in plans[1].notes])))
            self.assertEqual([n.string for n in plans[1].notes], list(range(coverage, 0, -1)))

    def test_documented_f_major_and_dense_custom_selection(self):
        result = voice(interpret(FretSelection(1, (1, 5, 8))))
        self.assertEqual(tuple(s.fret for s in result.strings), (1, 3, 3, 2, 1, 1))
        self.assertEqual(tuple(s.note for s in result.strings), (41, 48, 53, 57, 60, 65))
        harmony = interpret(FretSelection(1, tuple(range(1, 9))))
        self.assertEqual(len(harmony.pitch_classes), 8)
        self.assertEqual(len(voice(harmony).strings), 6)
        self.assertEqual(harmony.identity, "Custom")

    def test_invalid_scheduled_notes_and_spread(self):
        for n, v, o, d in ((128, 90, 0, 1), (0, 0, 0, 1), (40, 90, -1, 1),
                           (40, 90, float("nan"), 1), (40, 90, 0, 0)):
            with self.assertRaises(ValueError): ScheduledStringEvent(n, 6, v, o, d)
        with self.assertRaises(ValueError):
            plan_strum(StrumGesture(StrumDirection.RIGHT, StrumCharacter.FULL, 0, frozenset()),
                       voice(interpret(FretSelection(1, ()))), 0)
