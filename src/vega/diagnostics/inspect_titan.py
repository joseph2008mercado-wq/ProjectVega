"""Inspect pygame/SDL joystick events without assigning musical meanings."""

from __future__ import annotations

import argparse
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

# SDL reads this during initialization. Keep joystick events flowing while the
# inspector's window is not focused so focus-change tests are meaningful.
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

import pygame  # noqa: E402


CHECKLIST = """QANBA TITAN DISCOVERY CHECKLIST
  [ ] Confirm the physical lever switch setting for this run: DP, LS, or RS.
  [ ] Press and release each of the 8 main buttons individually, in a known order.
  [ ] Hold at least two main buttons together, then release them separately.
  [ ] Move the lever UP, DOWN, LEFT, RIGHT; return to NEUTRAL each time.
  [ ] Move through all four diagonals; return to NEUTRAL each time.
  [ ] Press and release L3 and R3.
  [ ] Press and release Options, Create/Share, and the touchpad press.
  [ ] Try every other exposed control, including switches if they emit events.
  [ ] Change focus to another app and back; check whether events continue.
  [ ] Unplug and reconnect the Titan; check device IDs and event recovery.
  [ ] Repeat this session in Titan DP, LS, and RS lever settings.

Run one labeled session per lever setting when possible. The label is a note
you provide; pygame cannot read the physical DP/LS/RS switch position.
Axes are logged as raw SDL floats. NEGATIVE/POSITIVE describe sign, not a
physical direction; ZERO means exactly 0.0. Hats use SDL x/y directions.
Close the inspector window or press Ctrl+C in the terminal to finish.
"""


def hat_direction(value: tuple[int, int]) -> str:
    x, y = value
    if x == 0 and y == 0:
        return "NEUTRAL"
    parts = []
    if y > 0:
        parts.append("UP")
    elif y < 0:
        parts.append("DOWN")
    if x > 0:
        parts.append("RIGHT")
    elif x < 0:
        parts.append("LEFT")
    return "+".join(parts)


def axis_sign(value: float) -> str:
    if value < 0:
        return "NEGATIVE"
    if value > 0:
        return "POSITIVE"
    return "ZERO"


@dataclass
class ControllerState:
    joystick: pygame.joystick.Joystick
    buttons: dict[int, int] = field(default_factory=dict)
    axes: dict[int, float] = field(default_factory=dict)
    hats: dict[int, tuple[int, int]] = field(default_factory=dict)


class SessionLog:
    def __init__(self, file: TextIO | None) -> None:
        self.file = file
        self.started_at = time.perf_counter()

    def write(self, message: str, *, at: float | None = None) -> None:
        stamp = time.perf_counter() if at is None else at
        line = f"[perf={stamp:.9f} elapsed={stamp - self.started_at:.6f}s] {message}"
        print(line, flush=True)
        if self.file is not None:
            print(line, file=self.file, flush=True)

    def heading(self, message: str) -> None:
        print(message, flush=True)
        if self.file is not None:
            print(message, file=self.file, flush=True)


class Inspector:
    def __init__(self, log: SessionLog) -> None:
        self.log = log
        self.controllers: dict[int, ControllerState] = {}

    def connect(self, device_index: int, *, at: float, initial: bool = False) -> None:
        try:
            joystick = pygame.joystick.Joystick(device_index)
            instance_id = joystick.get_instance_id()
            if instance_id in self.controllers:
                return  # Startup enumeration also generates JOYDEVICEADDED.
            state = ControllerState(joystick)
            state.buttons = {
                i: joystick.get_button(i) for i in range(joystick.get_numbuttons())
            }
            state.axes = {i: joystick.get_axis(i) for i in range(joystick.get_numaxes())}
            state.hats = {i: joystick.get_hat(i) for i in range(joystick.get_numhats())}
        except pygame.error as exc:
            self.log.write(f"CONNECT_ERROR device_index={device_index} error={exc!r}", at=at)
            return

        self.controllers[instance_id] = state
        self.log.write(
            f"{'INITIAL' if initial else 'CONNECTED'} "
            f"device_index={device_index} instance_id={instance_id} "
            f"name={joystick.get_name()!r} guid={joystick.get_guid()!r} "
            f"buttons={joystick.get_numbuttons()} axes={joystick.get_numaxes()} "
            f"hats={joystick.get_numhats()} balls={joystick.get_numballs()}",
            at=at,
        )
        self.log.write(
            f"BASELINE instance_id={instance_id} "
            f"buttons_down={[i for i, value in state.buttons.items() if value]} "
            f"axes={state.axes!r} "
            f"hats={{{', '.join(f'{i}: {value!r} ({hat_direction(value)})' for i, value in state.hats.items())}}}",
            at=at,
        )

    def disconnect(self, instance_id: int, *, at: float) -> None:
        state = self.controllers.pop(instance_id, None)
        if state is None:
            return
        self.log.write(f"DISCONNECTED instance_id={instance_id}", at=at)
        try:
            state.joystick.quit()
        except pygame.error as exc:
            self.log.write(f"CLOSE_ERROR instance_id={instance_id} error={exc!r}", at=at)

    def handle(self, event: pygame.event.Event, *, at: float) -> bool:
        if event.type == pygame.QUIT:
            self.log.write("WINDOW_CLOSED", at=at)
            return False
        if event.type == pygame.WINDOWFOCUSGAINED:
            self.log.write("FOCUS_GAINED inspector_window", at=at)
            return True
        if event.type == pygame.WINDOWFOCUSLOST:
            self.log.write("FOCUS_LOST inspector_window", at=at)
            return True
        if event.type == pygame.JOYDEVICEADDED:
            self.connect(event.device_index, at=at)
            return True
        if event.type == pygame.JOYDEVICEREMOVED:
            self.disconnect(event.instance_id, at=at)
            return True

        instance_id = getattr(event, "instance_id", None)
        state = self.controllers.get(instance_id)
        if state is None:
            return True

        if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP):
            value = 1 if event.type == pygame.JOYBUTTONDOWN else 0
            if state.buttons.get(event.button) != value:
                state.buttons[event.button] = value
                self.log.write(
                    f"BUTTON instance_id={instance_id} button={event.button} "
                    f"{'PRESSED' if value else 'RELEASED'}",
                    at=at,
                )
        elif event.type == pygame.JOYHATMOTION:
            value = tuple(event.value)
            previous = state.hats.get(event.hat)
            if previous != value:
                state.hats[event.hat] = value
                self.log.write(
                    f"HAT instance_id={instance_id} hat={event.hat} "
                    f"{previous!r} ({hat_direction(previous) if previous is not None else 'UNKNOWN'}) "
                    f"-> {value!r} ({hat_direction(value)})",
                    at=at,
                )
        elif event.type == pygame.JOYAXISMOTION:
            value = float(event.value)
            previous = state.axes.get(event.axis)
            if previous != value:
                state.axes[event.axis] = value
                old_label = axis_sign(previous) if previous is not None else "UNKNOWN"
                self.log.write(
                    f"AXIS instance_id={instance_id} axis={event.axis} "
                    f"{previous!r} ({old_label}) -> {value!r} ({axis_sign(value)})",
                    at=at,
                )
        elif event.type == pygame.JOYBALLMOTION:
            # Ball values are relative motion, not state: repeated deltas are real events.
            self.log.write(
                f"BALL instance_id={instance_id} ball={event.ball} rel={tuple(event.rel)!r}",
                at=at,
            )
        return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log", type=Path, metavar="FILE", help="Save the console transcript; refuses to overwrite an existing file."
    )
    parser.add_argument(
        "--mode", choices=("DP", "LS", "RS"), default="UNSPECIFIED",
        help="Physical Titan lever switch setting for this session (user supplied).",
    )
    return parser.parse_args(argv)


def run(log: SessionLog, *, mode: str) -> None:
    log.heading(CHECKLIST)
    log.write(
        f"SESSION mode={mode} python={platform.python_version()} "
        f"pygame={pygame.version.ver} SDL={pygame.get_sdl_version()} "
        f"platform={platform.platform()!r}"
    )

    pygame.display.init()
    pygame.joystick.init()
    pygame.display.set_caption("Project Vega - Titan input inspector (close to stop)")
    pygame.display.set_mode((480, 120))
    log.write(f"CONTROLLERS count={pygame.joystick.get_count()}")
    inspector = Inspector(log)

    try:
        for device_index in range(pygame.joystick.get_count()):
            inspector.connect(device_index, at=time.perf_counter(), initial=True)
        running = True
        while running:
            for event in pygame.event.get():
                received_at = time.perf_counter()
                running = inspector.handle(event, at=received_at)
                if not running:
                    break
            time.sleep(0.005)
    finally:
        log.write("SESSION_END")
        pygame.quit()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    file: TextIO | None = None
    if args.log is not None:
        try:
            file = args.log.open("x", encoding="utf-8", buffering=1)
        except OSError as exc:
            print(f"Cannot create log {args.log}: {exc}", file=sys.stderr)
            return 2
    try:
        log = SessionLog(file)
        try:
            run(log, mode=args.mode)
        except KeyboardInterrupt:
            log.write("INTERRUPTED Ctrl+C")
        except pygame.error as exc:
            log.write(f"PYGAME_ERROR {exc!r}")
            return 1
        return 0
    finally:
        if file is not None:
            file.close()


if __name__ == "__main__":
    raise SystemExit(main())
