"""Logic checks with a fake pygame device; no Titan or window required."""

from __future__ import annotations

import importlib
import io
import sys
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


class FakeJoystick:
    def __init__(self) -> None:
        self.closed = False

    def get_instance_id(self) -> int:
        return 7

    def get_name(self) -> str:
        return "Test controller"

    def get_guid(self) -> str:
        return "test-guid"

    def get_numbuttons(self) -> int:
        return 1

    def get_numaxes(self) -> int:
        return 1

    def get_numhats(self) -> int:
        return 1

    def get_numballs(self) -> int:
        return 0

    def get_button(self, index: int) -> int:
        return 0

    def get_axis(self, index: int) -> float:
        return 0.0

    def get_hat(self, index: int) -> tuple[int, int]:
        return (0, 0)

    def quit(self) -> None:
        self.closed = True


fake_pygame = types.ModuleType("pygame")
for code, name in enumerate(
    (
        "QUIT", "WINDOWFOCUSGAINED", "WINDOWFOCUSLOST", "JOYDEVICEADDED",
        "JOYDEVICEREMOVED", "JOYBUTTONDOWN", "JOYBUTTONUP", "JOYHATMOTION",
        "JOYAXISMOTION", "JOYBALLMOTION",
    ),
    start=1,
):
    setattr(fake_pygame, name, code)
fake_pygame.error = RuntimeError
joystick = FakeJoystick()
fake_pygame.joystick = types.SimpleNamespace(Joystick=lambda index: joystick)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
with patch.dict(sys.modules, {"pygame": fake_pygame}):
    inspector_module = importlib.import_module("vega.diagnostics.inspect_titan")


def event(kind: int, **fields: object) -> types.SimpleNamespace:
    return types.SimpleNamespace(type=kind, instance_id=7, **fields)


class InspectorTests(unittest.TestCase):
    def test_direction_labels(self) -> None:
        self.assertEqual(inspector_module.hat_direction((0, 0)), "NEUTRAL")
        self.assertEqual(inspector_module.hat_direction((1, 1)), "UP+RIGHT")
        self.assertEqual(inspector_module.hat_direction((-1, -1)), "DOWN+LEFT")
        self.assertEqual(inspector_module.axis_sign(0.0), "ZERO")

    def test_changed_events_and_reconnect(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            log = inspector_module.SessionLog(None)
            subject = inspector_module.Inspector(log)
            subject.connect(0, at=log.started_at, initial=True)
            subject.connect(0, at=log.started_at)
            subject.handle(event(fake_pygame.JOYBUTTONDOWN, button=0), at=1.0)
            subject.handle(event(fake_pygame.JOYBUTTONDOWN, button=0), at=1.1)
            subject.handle(event(fake_pygame.JOYBUTTONUP, button=0), at=1.2)
            subject.handle(event(fake_pygame.JOYHATMOTION, hat=0, value=(1, 1)), at=1.3)
            subject.handle(event(fake_pygame.JOYHATMOTION, hat=0, value=(0, 0)), at=1.4)
            subject.handle(event(fake_pygame.JOYAXISMOTION, axis=0, value=-1.0), at=1.5)
            subject.disconnect(7, at=1.6)
            subject.disconnect(7, at=1.7)
            subject.connect(0, at=1.8)

        lines = output.getvalue()
        self.assertEqual(lines.count("button=0 PRESSED"), 1)
        self.assertIn("button=0 RELEASED", lines)
        self.assertIn("(UP+RIGHT)", lines)
        self.assertIn("(NEUTRAL)", lines)
        self.assertIn("axis=0 0.0 (ZERO) -> -1.0 (NEGATIVE)", lines)
        self.assertEqual(lines.count("DISCONNECTED instance_id=7"), 1)
        self.assertIn("CONNECTED device_index=0", lines)
        self.assertTrue(joystick.closed)


if __name__ == "__main__":
    unittest.main()
