"""Deletion-boundary tests for the one-time Setup migration, not an installer."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("legacy_migration", Path(__file__).resolve().parents[1] / "packaging/legacy_migration.py")
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class LegacyMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "installed"
        self.root.mkdir()
        for name in ("Vega.exe", "unins000.exe"):
            (self.root / name).write_bytes(b"replacement")
        old_exe = b"old Vega executable"
        self.relative = "releases\\" + hashlib.sha256(old_exe).hexdigest()
        self.release = self.root / "releases" / self.relative.split("\\")[1]
        self.release.mkdir(parents=True)
        (self.release / "Vega.exe").write_bytes(old_exe)
        (self.release / "_internal").mkdir()
        (self.release / "_internal" / "owned.dll").write_bytes(b"owned")
        self.data = {"Owner": "ProjectVega.local.v1", "Releases": [
            {"Directory": self.relative, "Files": ["Vega.exe", "_internal\\owned.dll"]}]}
        self.marker = self.root / "install.json"
        self.write_manifest()

    def write_manifest(self):
        self.marker.write_text(json.dumps(self.data), encoding="utf-8-sig")

    def test_removes_only_proven_files_and_empty_known_directories(self):
        (self.release / "keep.txt").write_text("unknown")
        (self.root / "settings.json").write_text("also unknown")
        migration.cleanup(self.root)
        self.assertFalse((self.release / "Vega.exe").exists())
        self.assertFalse((self.release / "_internal").exists())
        self.assertEqual((self.release / "keep.txt").read_text(), "unknown")
        self.assertEqual((self.root / "settings.json").read_text(), "also unknown")
        self.assertTrue((self.root / "Vega.exe").is_file())
        self.assertFalse(self.marker.exists())
        migration.cleanup(self.root)  # Already migrated is harmless.

    def test_no_unknown_files_removes_old_release_tree(self):
        migration.cleanup(self.root)
        self.assertFalse((self.root / "releases").exists())
        self.assertFalse(self.marker.exists())

    def test_every_entry_validated_before_any_deletion(self):
        for name in ("..\\outside.txt", "C:\\outside.txt", "\\outside.txt", "file:stream",
                     "_internal/owned.dll", "", "file.", "NUL", "dir\\..\\file"):
            with self.subTest(name=name):
                self.data["Releases"][0]["Files"] = ["Vega.exe", "_internal\\owned.dll", name]
                self.write_manifest()
                self.assertEqual(migration.main(self.root), 1)
                self.assertTrue((self.release / "Vega.exe").exists())
                self.assertTrue((self.release / "_internal" / "owned.dll").exists())

    def test_wrong_hash_owner_or_missing_replacement_preserved(self):
        (self.release / "Vega.exe").write_bytes(b"different")
        self.assertEqual(migration.main(self.root), 1)
        self.assertTrue(self.marker.exists())
        self.data["Owner"] = "other"
        self.write_manifest()
        self.assertEqual(migration.main(self.root), 1)
        (self.root / "unins000.exe").unlink()
        self.assertEqual(migration.main(self.root), 1)
        self.assertTrue((self.release / "_internal" / "owned.dll").exists())

    def test_redirected_file_or_parent_is_never_followed(self):
        original = Path.is_junction
        for target in (self.root.parent, self.release, self.release / "_internal" / "owned.dll"):
            with patch.object(Path, "is_junction", lambda path: path == target or original(path)):
                self.assertEqual(migration.main(self.root), 1)
                self.assertTrue((self.release / "Vega.exe").exists())

    def test_malformed_and_duplicate_keys_preserved(self):
        for content in ('not json', '[]', '{"Owner":"other","Owner":"ProjectVega.local.v1","Releases":[]}',
                        '{"Owner":"ProjectVega.local.v1","Releases":[]}'):
            self.marker.write_text(content)
            self.assertEqual(migration.main(self.root), 1)
            self.assertTrue((self.release / "Vega.exe").exists())

    def test_locked_file_retains_executable_proof_and_manifest(self):
        original = Path.unlink
        def locked(path, *args, **kwargs):
            if path.name == "owned.dll":
                raise PermissionError("locked")
            return original(path, *args, **kwargs)
        with patch.object(Path, "unlink", locked):
            self.assertEqual(migration.main(self.root), 1)
        self.assertTrue((self.release / "Vega.exe").exists())
        self.assertTrue(self.marker.exists())
