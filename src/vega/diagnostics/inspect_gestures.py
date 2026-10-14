"""Show live symbolic Titan PC+DP state and finalized Vega Guitar gestures."""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path
from typing import TextIO

from vega.input.pygame_titan import ConnectedDevice, DisconnectedDevice, PygameTitanInput

import pygame

from vega.diagnostics.inspect_titan import SessionLog
from vega.input.pipeline import VegaInputPipeline
from vega.music.strum import StrumGesture


CHECKLIST = """VEGA GUITAR LIVE GESTURE CHECKLIST
Set the Titan system switch to PC and the lever switch to DP.
Start with all face buttons released and the lever centered.

  [ ] Normal: LEFT -> horizontal neutral -> RIGHT -> horizontal neutral, quickly.
  [ ] FULL lower arc: DOWN+LEFT -> DOWN -> DOWN+RIGHT -> DOWN -> DOWN+LEFT.
      Expect LEFT/FULL, RIGHT/FULL, LEFT/FULL.
  [ ] STRICT upper arc: UP+LEFT -> UP -> UP+RIGHT -> UP -> UP+LEFT.
      Expect LEFT/STRICT, RIGHT/STRICT, LEFT/STRICT.
  [ ] Quarter circles: DOWN -> DOWN+RIGHT -> RIGHT; DOWN -> DOWN+LEFT -> LEFT;
      UP -> UP+RIGHT -> RIGHT; UP -> UP+LEFT -> LEFT. Expect one stroke each.
  [ ] Vertical only: UP -> CENTER -> DOWN -> CENTER. Expect no STRUM lines.
  [ ] Hold LEFT after CENTER -> LEFT. Expect only one gesture.
  [ ] Hold several FACE buttons, strum, then change them immediately.
      The STRUM fingering should retain the buttons held at stroke start.
  [ ] Alternate LEFT/RIGHT rapidly, returning x to 0 between strokes.

Ctrl+C in the terminal or close the inspector window to exit.
"""


def nonnegative_milliseconds(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("settle window must be a number of milliseconds") from exc
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("settle window must be finite and non-negative")
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settle-ms", type=nonnegative_milliseconds, default=8.0,
                        metavar="NUMBER", help="Diagonal settle window in milliseconds (default: 8).")
    parser.add_argument("--log", type=Path, metavar="FILE",
                        help="Save this session; refuses to overwrite an existing file.")
    parser.add_argument("--device-index", type=int, metavar="INDEX",
                        help="Select a controller when several are connected.")
    return parser.parse_args(argv)


def held_names(pipeline: VegaInputPipeline) -> str:
    return " ".join(face.name for face in sorted(pipeline.state.fingering, key=lambda face: face.value)) or "(none)"


def show_gestures(log: SessionLog, gestures: list[StrumGesture]) -> None:
    for gesture in gestures:
        names = ", ".join(face.name for face in sorted(gesture.fingering, key=lambda face: face.value))
        log.write(
            f"STRUM direction={gesture.direction.name} character={gesture.character.name} "
            f"fingering=[{names}] timestamp={gesture.timestamp:.9f}"
        )


def run(log: SessionLog, *, settle_ms: float, device_index: int | None) -> None:
    log.heading(CHECKLIST)
    log.write(f"PROFILE Qanba Titan PC+DP | settle window={settle_ms:g} ms")
    pygame.display.init()
    pygame.joystick.init()
    pygame.display.set_caption("Project Vega - live gesture inspector (close to stop)")
    pygame.display.set_mode((480, 120))
    controller = PygameTitanInput(device_index=device_index)
    pipeline = VegaInputPipeline(settle_seconds=settle_ms / 1000.0)

    try:
        device = controller.connect_initial()
        log.write(f"CONTROLLER name={device.name!r} guid={device.guid!r} "
                  f"device_index={device.device_index} instance_id={device.instance_id}")
        running = True
        while running:
            for event in pygame.event.get():
                timestamp = time.perf_counter()
                if event.type == pygame.QUIT:
                    running = False
                    break
                change = controller.handle(event, timestamp=timestamp)
                if isinstance(change, DisconnectedDevice):
                    pipeline.reset()
                    log.write(f"DISCONNECTED instance_id={change.instance_id}; symbolic state reset", at=timestamp)
                elif isinstance(change, ConnectedDevice):
                    pipeline.reset()
                    log.write(f"RECONNECTED name={change.name!r} guid={change.guid!r} "
                              f"instance_id={change.instance_id}", at=timestamp)
                elif change is not None:
                    before_faces = pipeline.state.fingering
                    before_lever = (pipeline.state.lever_x, pipeline.state.lever_y)
                    gestures = pipeline.on_raw(change)
                    after_faces = pipeline.state.fingering
                    for face in sorted(after_faces - before_faces, key=lambda face: face.value):
                        log.write(f"FACE DOWN: {face.name} | HELD: {held_names(pipeline)}", at=timestamp)
                    for face in sorted(before_faces - after_faces, key=lambda face: face.value):
                        log.write(f"FACE UP: {face.name} | HELD: {held_names(pipeline)}", at=timestamp)
                    after_lever = (pipeline.state.lever_x, pipeline.state.lever_y)
                    if after_lever != before_lever:
                        log.write(f"LEVER x={after_lever[0]} y={after_lever[1]}", at=timestamp)
                    show_gestures(log, gestures)
            # The recognizer may be waiting for the settle deadline with no
            # further SDL event. Flush every loop so the stroke is not lost.
            show_gestures(log, pipeline.flush(time.perf_counter()))
            time.sleep(0.001)
    finally:
        controller.close()
        pygame.quit()
        log.write("SESSION_END")


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
            run(log, settle_ms=args.settle_ms, device_index=args.device_index)
        except KeyboardInterrupt:
            log.write("INTERRUPTED Ctrl+C")
        except (pygame.error, ValueError) as exc:
            log.write(f"ERROR {exc}")
            return 1
        return 0
    finally:
        if file is not None:
            file.close()


if __name__ == "__main__":
    raise SystemExit(main())
