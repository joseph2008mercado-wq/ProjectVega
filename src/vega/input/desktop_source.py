"""Nonblocking SDL pump for the desktop runtime; reuses PygameTitanInput."""

from __future__ import annotations

import time

from vega.input.pygame_titan import ConnectedDevice, DisconnectedDevice, PygameTitanInput

import pygame

from vega.input.events import RawEvent
from vega.runtime import DeviceStatus


class DesktopInputSource:
    def __init__(self, *, device_index: int | None = None) -> None:
        self.adapter = PygameTitanInput(device_index=device_index)
        self.initialized = False
        self.retry_at = 0.0
        self.search_at = 0.0
        self.last_status: DeviceStatus | None = None

    def poll(self, now: float) -> list[RawEvent | DeviceStatus]:
        try:
            return self._poll(now)
        except pygame.error as exc:
            # A lost SDL handle must not leave last_status saying Connected:
            # reconnect must publish a new connection edge to the runtime.
            try:
                self.close()
            except pygame.error:
                pass
            self.retry_at = now + 2
            status = DeviceStatus(False, detail=f"Input unavailable: {exc}")
            self.last_status = status
            return [status]

    def _poll(self, now: float) -> list[RawEvent | DeviceStatus]:
        changes: list[RawEvent | DeviceStatus] = []
        if not self.initialized:
            if now < self.retry_at:
                return changes
            self.retry_at = now + 2
            try:
                pygame.display.init()
                # SDL owns a hidden window, Qt owns the visible application.
                pygame.display.set_mode((1, 1), pygame.HIDDEN)
                pygame.joystick.init()
                self.initialized = True
            except pygame.error as exc:
                self._status(DeviceStatus(False, detail=f"Input unavailable: {exc}"), changes)
                return changes

        if self.adapter.joystick is None and self.adapter.guid is None and now >= self.search_at:
            self.search_at = now + 0.5
            try:
                device = self.adapter.connect_initial()
                self._status(DeviceStatus(True, device.name, "Connected"), changes)
            except ValueError as exc:
                self._status(DeviceStatus(False, detail=f"Waiting · {exc}"), changes)

        for event in pygame.event.get():
            # Before the first selection, use connect_initial's unambiguous
            # device policy instead of adopting whichever device SDL lists first.
            if self.adapter.guid is None:
                continue
            change = self.adapter.handle(event, timestamp=time.perf_counter())
            if isinstance(change, ConnectedDevice):
                self._status(DeviceStatus(True, change.name, "Connected"), changes)
            elif isinstance(change, DisconnectedDevice):
                name = self.last_status.name if self.last_status else "Qanba Titan"
                self._status(DeviceStatus(False, name, "Disconnected · waiting for reconnect"), changes)
            elif change is not None:
                changes.append(change)
        return changes

    def _status(self, status: DeviceStatus, changes: list) -> None:
        if status != self.last_status:
            self.last_status = status
            changes.append(status)

    def close(self) -> None:
        self.initialized = False
        self.search_at = 0
        self.last_status = None
        try:
            self.adapter.close()
        finally:
            pygame.joystick.quit()
            pygame.display.quit()
