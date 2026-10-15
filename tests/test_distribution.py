"""Incomplete builds fail before Inno runs. No compiler required."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("verify_distribution", Path(__file__).resolve().parents[1] / "scripts/verify-distribution.py")
distribution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(distribution)


class DistributionTests(unittest.TestCase):
    def test_missing_required_files_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "missing Vega.exe"):
                distribution.verify(Path(directory), write=True)

    def test_missing_changed_or_unexpected_payload_fails(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(distribution, "REQUIRED", ("Vega.exe",)):
            root = Path(directory)
            exe = root / "Vega.exe"
            exe.write_bytes(b"app")
            distribution.verify(root, write=True)
            distribution.verify(root)
            exe.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "changed"):
                distribution.verify(root)
            exe.write_bytes(b"app")
            (root / "extra.dll").write_bytes(b"unexpected")
            with self.assertRaisesRegex(ValueError, "changed"):
                distribution.verify(root)
