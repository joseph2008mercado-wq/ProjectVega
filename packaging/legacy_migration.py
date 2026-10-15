"""One-time cleanup of the retired developer installer, called only by Setup.

No installation, version selection, shortcut or settings management lives here.
The old manifest lists ownership; each release's executable must also match its
SHA-256 directory name. Validate the whole plan before removing individual files.
Unlisted files and nonempty directories are never removed.
"""

import hashlib
import json
import ntpath
from pathlib import Path, PureWindowsPath
import re


def no_redirects(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError("Redirected legacy path; leaving it untouched")


def unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate manifest key")
        result[key] = value
    return result


def owned_files(root: Path) -> list[tuple[Path, list[Path]]]:
    """Return a fully checked deletion plan, or raise without changing files."""
    no_redirects(root)
    marker = root / "install.json"
    no_redirects(marker)
    data = json.loads(marker.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object)
    if (not isinstance(data, dict) or set(data) != {"Owner", "Releases"}
            or data["Owner"] != "ProjectVega.local.v1"
            or not isinstance(data["Releases"], list) or not data["Releases"]):
        raise ValueError("Not a known legacy manifest")
    plan = []
    seen = set()
    for entry in data["Releases"]:
        if not isinstance(entry, dict) or set(entry) != {"Directory", "Files"}:
            raise ValueError("Invalid legacy release")
        directory, names = entry["Directory"], entry["Files"]
        if (not isinstance(directory, str) or not re.fullmatch(r"releases\\[a-f0-9]{64}", directory)
                or directory in seen or not isinstance(names, list) or not names):
            raise ValueError("Invalid legacy release directory or inventory")
        seen.add(directory)
        release = root.joinpath(*PureWindowsPath(directory).parts)
        no_redirects(release)
        paths = []
        file_names = set()
        for name in names:
            if not isinstance(name, str) or not name or "/" in name:
                raise ValueError("Invalid legacy filename")
            parts = name.split("\\")
            if any(not p or p in (".", "..") or p[-1] in " ." or
                   any(c in p for c in ':<>"|?*\x00') or
                   ntpath.isreserved(p) for p in parts):
                raise ValueError("Unsafe legacy filename")
            path = release.joinpath(*parts)
            no_redirects(path)
            if not path.resolve().is_relative_to(release.resolve()):
                raise ValueError("Legacy file escapes its release")
            if name.casefold() in file_names or path.is_dir():
                raise ValueError("Duplicate or non-file inventory entry")
            file_names.add(name.casefold())
            paths.append(path)
        executable = release / "Vega.exe"
        if "vega.exe" not in file_names:
            raise ValueError("Legacy executable not owned")
        with executable.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != release.name:
            raise ValueError("Legacy executable does not match its build hash")
        plan.append((release, paths))
    return plan


def cleanup(root: Path) -> None:
    root = root.absolute()
    if not (root / "install.json").exists():
        return
    # Only after the replacement app and registered uninstaller were installed.
    for name in ("Vega.exe", "unins000.exe"):
        no_redirects(root / name)
        if not (root / name).is_file():
            raise ValueError("Setup-managed replacement is not complete")
    plan = owned_files(root)
    for release, paths in plan:
        # Keep the hash proof until the rest of this release has been removed.
        paths.sort(key=lambda p: p.name.casefold() == "vega.exe")
        directories = {release}
        for path in paths:
            no_redirects(path)
            path.unlink(missing_ok=True)
            directories.update(p for p in path.parents if p.is_relative_to(release))
        for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True):
            no_redirects(directory)
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()  # Never recursive; unknown children survive.
    no_redirects(root / "install.json")
    (root / "install.json").unlink()
    releases = root / "releases"
    no_redirects(releases)
    if releases.is_dir() and not any(releases.iterdir()):
        releases.rmdir()


def main(root: Path) -> int:
    try:
        cleanup(root)
    except (OSError, ValueError, TypeError):
        return 1  # Setup logs this; uncertain files remain, the new app still works.
    return 0
