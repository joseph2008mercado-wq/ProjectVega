"""Build-machine inventory check; never executed by the end-user installer."""

import argparse
import hashlib
import json
from pathlib import Path

MANIFEST = "distribution.json"
REQUIRED = (
    "Vega.exe", "LICENSE", "THIRD_PARTY_NOTICES.md", "licenses/SOURCES.json",
    "_internal/python313.dll", "_internal/base_library.zip",
    "_internal/VCRUNTIME140.dll", "_internal/portmidi.dll", "_internal/SDL2.dll",
    "_internal/SDL2_mixer.dll", "_internal/PySide6/Qt6Core.dll",
    "_internal/PySide6/Qt6Gui.dll", "_internal/PySide6/Qt6Widgets.dll",
    "_internal/PySide6/MSVCP140.dll", "_internal/PySide6/plugins/platforms/qwindows.dll",
    "_internal/vega/app/resources/vega.ico",
)


def inventory(root: Path) -> dict[str, str]:
    for name in REQUIRED:
        if not (root / name).is_file():
            raise ValueError(f"Incomplete distribution: missing {name}. Rebuild with scripts/build-windows.ps1.")
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f"Redirected distribution path: {path}")
        if path.is_file() and path != root / MANIFEST:
            with path.open("rb") as stream:
                result[path.relative_to(root).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    return result


def verify(root: Path, *, write: bool = False) -> None:
    actual = inventory(root)
    marker = root / MANIFEST
    if write:
        marker.write_text(json.dumps(actual, indent=2) + "\n", encoding="utf-8")
    else:
        expected = json.loads(marker.read_text(encoding="utf-8"))
        if expected != actual:
            raise ValueError("Distribution changed or is incomplete. Rebuild with scripts/build-windows.ps1.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        verify(Path(__file__).resolve().parents[1] / "dist/Vega", write=args.write)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Build validation: {exc}\n")
    print("Distribution inventory verified.")
