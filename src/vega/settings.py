"""Small, per-user preferences. Playback permission is deliberately not saved."""

from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path


def bounded(value: object, low: float, high: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return min(high, max(low, number)) if math.isfinite(number) else default


@dataclass
class Settings:
    settle_ms: float = 8.0
    preview_volume: float = 0.35

    def __post_init__(self) -> None:
        self.settle_ms = bounded(self.settle_ms, 0, 20, 8)
        self.preview_volume = bounded(self.preview_volume, 0, 1, 0.35)


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

    def load(self) -> Settings:
        self.error = ""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("expected a settings object")
            return Settings(data.get("settle_ms", 8), data.get("preview_volume", 0.35))
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
            temporary.write_text(json.dumps(asdict(settings), indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.path)
        except OSError as exc:
            self.error = f"Settings could not be saved: {exc}"
