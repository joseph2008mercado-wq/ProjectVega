"""Pygame event adapter checks with a fake controller, no hardware needed."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class FakeJoystick:
    def __init__(self, instance_id: int) -> None:
        self.instance_id = instance_id
        self.closed = False

    def get_instance_id(self) -> int:
        return self.instance_id

    def get_name(self) -> str:
        return "Qanba Titan"

    def get_guid(self) -> str:
        return "same-guid"

    def quit(self) -> None:
        self.closed = True


fake_pygame = types.ModuleType("pygame")
for code, name in enumerate(
    ("QUIT", "JOYDEVICEADDED", "JOYDEVICEREMOVED", "JOYBUTTONDOWN",
     "JOYBUTTONUP", "JOYAXISMOTION", "JOYHATMOTION"),
    start=1,
):
    setattr(fake_pygame, name, code)
current_device = [FakeJoystick(10)]
fake_pygame.joystick = types.SimpleNamespace(
    get_count=lambda: 1,
    Joystick=lambda index: current_device[0],
    init=lambda: None,
)
fake_pygame.display = types.SimpleNamespace(
    init=lambda: None,
    set_caption=lambda title: None,
    set_mode=lambda size: None,
)
fake_pygame.quit = lambda: None

with patch.dict(sys.modules, {"pygame": fake_pygame}):
    adapter_module = importlib.import_module("vega.input.pygame_titan")
    gesture_module = importlib.import_module("vega.diagnostics.inspect_gestures")


def event(kind: int, **fields: object) -> types.SimpleNamespace:
    return types.SimpleNamespace(type=kind, **fields)


class PygameAdapterTests(unittest.TestCase):
    def test_desktop_pump_error_resets_resources_and_announces_reconnect(self):
        with patch.dict(sys.modules, {"pygame": fake_pygame}):
            desktop_module = importlib.import_module("vega.input.desktop_source")
        source = desktop_module.DesktopInputSource()
        source.initialized = True
        current_device[0] = FakeJoystick(55)
        source.adapter.connect_initial()
        display = types.SimpleNamespace(init=lambda: None, set_mode=lambda *args: None, quit=lambda: None)
        devices = types.SimpleNamespace(get_count=lambda: 1, Joystick=lambda i: current_device[0],
                                       init=lambda: None, quit=lambda: None)
        with patch.object(fake_pygame, "error", RuntimeError, create=True), \
             patch.object(fake_pygame, "display", display), \
             patch.object(fake_pygame, "joystick", devices), \
             patch.object(fake_pygame, "HIDDEN", 0, create=True), \
             patch.object(fake_pygame, "event", types.SimpleNamespace(get=lambda: []), create=True):
            with patch.object(fake_pygame.event, "get", side_effect=RuntimeError("SDL lost")):
                self.assertFalse(source.poll(1)[0].connected)
            self.assertFalse(source.initialized)
            self.assertIsNone(source.adapter.joystick)
            self.assertEqual(source.poll(2), [])
            current_device[0] = FakeJoystick(56)
            fake_pygame.event.get = lambda: [event(fake_pygame.JOYDEVICEADDED, device_index=0)]
            self.assertTrue(source.poll(3)[0].connected)
            source.close()

    def test_selected_device_raw_events_and_reconnect(self) -> None:
        first = FakeJoystick(10)
        current_device[0] = first
        adapter = adapter_module.PygameTitanInput()
        connected = adapter.connect_initial()
        self.assertEqual((connected.name, connected.instance_id), ("Qanba Titan", 10))
        self.assertIsNone(adapter.handle(event(fake_pygame.JOYDEVICEADDED, device_index=0), timestamp=0.0))

        button = adapter.handle(
            event(fake_pygame.JOYBUTTONDOWN, instance_id=10, button=2), timestamp=1.0
        )
        self.assertEqual((button.button, button.pressed, button.timestamp), (2, True, 1.0))
        axis = adapter.handle(
            event(fake_pygame.JOYAXISMOTION, instance_id=10, axis=5, value=0.98), timestamp=1.1
        )
        self.assertEqual((axis.axis, axis.value), (5, 0.98))
        hat = adapter.handle(
            event(fake_pygame.JOYHATMOTION, instance_id=10, hat=0, value=(-1, 1)), timestamp=1.2
        )
        self.assertEqual((hat.hat, hat.x, hat.y), (0, -1, 1))
        self.assertIsNone(adapter.handle(
            event(fake_pygame.JOYBUTTONDOWN, instance_id=99, button=2), timestamp=1.3
        ))

        disconnected = adapter.handle(
            event(fake_pygame.JOYDEVICEREMOVED, instance_id=10), timestamp=2.0
        )
        self.assertEqual(disconnected.instance_id, 10)
        self.assertTrue(first.closed)
        self.assertIsNone(adapter.joystick)

        current_device[0] = FakeJoystick(11)
        reconnected = adapter.handle(
            event(fake_pygame.JOYDEVICEADDED, device_index=0), timestamp=3.0
        )
        self.assertEqual(reconnected.instance_id, 11)
        adapter.close()
        self.assertTrue(current_device[0].closed)

    def test_live_loop_finalizes_without_a_followup_joystick_event(self) -> None:
        current_device[0] = FakeJoystick(30)
        batches = iter([
            [event(fake_pygame.JOYBUTTONDOWN, instance_id=30, button=2),
             event(fake_pygame.JOYHATMOTION, instance_id=30, hat=0, value=(-1, 0))],
            [],
            [],
            [event(fake_pygame.QUIT)],
        ])
        fake_pygame.event = types.SimpleNamespace(get=lambda: next(batches))

        class CaptureLog:
            def __init__(self) -> None:
                self.lines: list[str] = []

            def heading(self, message: str) -> None:
                self.lines.append(message)

            def write(self, message: str, *, at: float | None = None) -> None:
                self.lines.append(message)

        clock = iter(i * 0.005 for i in range(1, 20))
        log = CaptureLog()
        with patch.object(gesture_module, "time", types.SimpleNamespace(
            perf_counter=lambda: next(clock), sleep=lambda seconds: None
        )):
            gesture_module.run(log, settle_ms=8.0, device_index=None)

        strums = [line for line in log.lines if line.startswith("STRUM ")]
        self.assertEqual(len(strums), 1)
        self.assertIn("direction=LEFT character=NORMAL", strums[0])
        self.assertIn("fingering=[FACE_1]", strums[0])
        self.assertTrue(current_device[0].closed)

    def test_desktop_missing_startup_then_connect_disconnect_reconnect(self) -> None:
        with patch.dict(sys.modules, {"pygame": fake_pygame}):
            desktop_module = importlib.import_module("vega.input.desktop_source")
        from vega.runtime import DeviceStatus

        count = [0]
        queued = []
        display = types.SimpleNamespace(init=lambda: None, set_mode=lambda *args: None, quit=lambda: None)
        devices = types.SimpleNamespace(get_count=lambda: count[0], Joystick=lambda i: current_device[0],
                                       init=lambda: None, quit=lambda: None)
        with patch.object(fake_pygame, "display", display), \
             patch.object(fake_pygame, "joystick", devices), \
             patch.object(fake_pygame, "HIDDEN", 0, create=True), \
             patch.object(fake_pygame, "event", types.SimpleNamespace(get=lambda: queued.copy()), create=True):
            source = desktop_module.DesktopInputSource()
            missing = source.poll(0)
            self.assertIsInstance(missing[0], DeviceStatus)
            self.assertFalse(missing[0].connected)
            self.assertEqual(source.poll(0.1), [])
            count[0] = 1
            current_device[0] = FakeJoystick(40)
            self.assertTrue(source.poll(0.6)[0].connected)
            queued[:] = [event(fake_pygame.JOYDEVICEREMOVED, instance_id=40)]
            self.assertFalse(source.poll(1)[0].connected)
            current_device[0] = FakeJoystick(41)
            queued[:] = [event(fake_pygame.JOYDEVICEADDED, device_index=0)]
            self.assertTrue(source.poll(2)[0].connected)
            queued[:] = [event(fake_pygame.JOYBUTTONDOWN, instance_id=41, button=2)]
            self.assertTrue(source.poll(3)[0].pressed)
            source.close()
            self.assertTrue(current_device[0].closed)


if __name__ == "__main__":
    unittest.main()
