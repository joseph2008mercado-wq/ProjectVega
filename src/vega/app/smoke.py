"""Explicit packaging smoke mode. Normal launches never write diagnostic reports."""

import json
import sys
from pathlib import Path

from vega.app.identity import APP_NAME, APP_VERSION, icon_path
from vega.settings import Settings, SettingsStore


class SmokeSettingsStore(SettingsStore):
    """Package checks must not overwrite the user's settings."""

    def load(self) -> Settings:
        return Settings()

    def save(self, settings: Settings) -> None:
        pass


def write_report(window, destination: Path) -> None:
    from PySide6.QtWidgets import QApplication

    state = window.runtime.snapshot()
    console = None
    if sys.platform == "win32":
        import ctypes

        console = bool(ctypes.windll.kernel32.GetConsoleWindow())
    report = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "frozen": bool(getattr(sys, "frozen", False)),
        "gui_initialized": window.isVisible(),
        "qt_platform": QApplication.platformName(),
        "icon_present": icon_path().is_file() and not window.windowIcon().pixmap(32, 32).isNull(),
        "icon_path": str(icon_path()),
        "muted": state.muted,
        "connected": state.device.connected,
        "device_name": state.device.name,
        "device_status": state.device.detail,
        "audio_status": state.audio_status,
        "console_attached": console,
    }
    with destination.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
