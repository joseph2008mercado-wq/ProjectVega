"""Pygame joystick events for one selected Titan, without musical mapping."""

from __future__ import annotations

import os
from dataclasses import dataclass

# SDL reads this during initialization. Keep receiving events when another
# application has focus, as the raw Titan inspector does.
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

import pygame  # noqa: E402

from vega.input.events import RawAxisEvent, RawButtonEvent, RawEvent, RawHatEvent


@dataclass(frozen=True)
class ConnectedDevice:
    device_index: int
    instance_id: int
    name: str
    guid: str


@dataclass(frozen=True)
class DisconnectedDevice:
    instance_id: int


DeviceChange = ConnectedDevice | DisconnectedDevice


class PygameTitanInput:
    """Select one joystick and pass only its raw events to the input pipeline.

    A supplied device index selects the initial device. Otherwise a unique
    Qanba/Titan name is preferred, with a sole connected controller as a
    fallback. Reconnects match the original GUID; a new SDL instance ID is
    expected. Raw button/axis/hat IDs are interpreted only by the DP profile.
    """

    def __init__(self, *, device_index: int | None = None) -> None:
        self.requested_index = device_index
        self.joystick: pygame.joystick.Joystick | None = None
        self.guid: str | None = None

    def connect_initial(self) -> ConnectedDevice:
        devices = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        if not devices:
            raise ValueError("No joystick detected. Connect the Titan and start again.")

        if self.requested_index is not None:
            if not 0 <= self.requested_index < len(devices):
                for device in devices:
                    device.quit()
                raise ValueError(f"Device index {self.requested_index} is not connected.")
            selected_index = self.requested_index
        else:
            matches = [
                i for i, device in enumerate(devices)
                if "qanba" in device.get_name().lower() or "titan" in device.get_name().lower()
            ]
            if len(matches) == 1:
                selected_index = matches[0]
            elif len(devices) == 1:
                selected_index = 0
            else:
                choices = ", ".join(f"{i}: {device.get_name()}" for i, device in enumerate(devices))
                for device in devices:
                    device.quit()
                raise ValueError(f"Select the Titan with --device-index. Detected: {choices}")

        selected = devices[selected_index]
        for index, device in enumerate(devices):
            if index != selected_index:
                device.quit()
        self.joystick = selected
        self.guid = selected.get_guid()
        return self._describe(selected_index, selected)

    def handle(self, event: pygame.event.Event, *, timestamp: float) -> RawEvent | DeviceChange | None:
        if event.type == pygame.JOYDEVICEREMOVED:
            if self.joystick is None or event.instance_id != self.joystick.get_instance_id():
                return None
            instance_id = event.instance_id
            self.joystick.quit()
            self.joystick = None
            return DisconnectedDevice(instance_id)

        if event.type == pygame.JOYDEVICEADDED:
            device = pygame.joystick.Joystick(event.device_index)
            if self.joystick is not None:
                # SDL also reports already-connected devices at startup.
                if device.get_instance_id() != self.joystick.get_instance_id():
                    device.quit()
                return None
            if self.guid is not None and device.get_guid() != self.guid:
                device.quit()
                return None
            self.joystick = device
            self.guid = device.get_guid()
            return self._describe(event.device_index, device)

        if self.joystick is None or getattr(event, "instance_id", None) != self.joystick.get_instance_id():
            return None
        instance_id = event.instance_id
        if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP):
            return RawButtonEvent(
                button=event.button,
                pressed=event.type == pygame.JOYBUTTONDOWN,
                timestamp=timestamp,
                instance_id=instance_id,
            )
        if event.type == pygame.JOYAXISMOTION:
            return RawAxisEvent(event.axis, float(event.value), timestamp, instance_id)
        if event.type == pygame.JOYHATMOTION:
            x, y = event.value
            return RawHatEvent(event.hat, x, y, timestamp, instance_id)
        return None

    def close(self) -> None:
        if self.joystick is not None:
            self.joystick.quit()
            self.joystick = None

    @staticmethod
    def _describe(index: int, device: pygame.joystick.Joystick) -> ConnectedDevice:
        return ConnectedDevice(index, device.get_instance_id(), device.get_name(), device.get_guid())
