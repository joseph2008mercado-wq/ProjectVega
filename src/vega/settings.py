"""Small, per-user preferences. Playback permission is deliberately not saved."""

from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from vega.music.fret_sets import FACTORY_FRET_SETS, FretSet, read_sets, validate_sets


DEFAULT_PREVIEW_VOLUME = 0.65


def bounded(value: object, low: float, high: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return min(high, max(low, number)) if math.isfinite(number) else default


@dataclass
class Settings:
    settle_ms: float = 8.0
    preview_volume: float = DEFAULT_PREVIEW_VOLUME
    spread_ms: float = 10.0
    fret_sets: tuple[FretSet, ...] = FACTORY_FRET_SETS
    active_set: int = 1
    midi_port: str = ""
    midi_channel: int = 1
    window_geometry: str = ""

    def __post_init__(self) -> None:
        self.settle_ms = bounded(self.settle_ms, 0, 20, 8)
        self.preview_volume = bounded(self.preview_volume, 0, 1, DEFAULT_PREVIEW_VOLUME)
        self.spread_ms = bounded(self.spread_ms, 1, 30, 10)
        validate_sets(self.fret_sets)
        if type(self.active_set) is not int or self.active_set not in (1, 2, 3):
            self.active_set = 1
        if type(self.midi_channel) is not int or not 1 <= self.midi_channel <= 16:
            self.midi_channel = 1
        if not isinstance(self.midi_port, str):
            self.midi_port = ""
        if not isinstance(self.window_geometry, str):
            self.window_geometry = ""


def config_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "ProjectVega" / "settings.json"


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path is not None else config_path()
        self.error = ""
        self._extra: dict = {}

    def load(self) -> Settings:
        self.error = ""
        self._extra = {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("expected a settings object")
            self._extra = {key: value for key, value in data.items()
                           if key not in Settings.__dataclass_fields__ and key != "muted"}
            return Settings(data.get("settle_ms", 8), data.get("preview_volume", DEFAULT_PREVIEW_VOLUME),
                            data.get("spread_ms", 10), read_sets(data.get("fret_sets")),
                            data.get("active_set", 1), data.get("midi_port", ""),
                            data.get("midi_channel", 1), data.get("window_geometry", ""))
        except FileNotFoundError:
            return Settings()
        except (OSError, ValueError) as exc:
            self.error = f"Settings could not be read; using defaults: {exc}"
            return Settings()

    def save(self, settings: Settings) -> None:
        self.error = ""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self._extra | asdict(settings), indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.path)
        except OSError as exc:
            self.error = f"Settings could not be saved: {exc}"
