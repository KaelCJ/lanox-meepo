#!/usr/bin/env python3
"""Verify the binary register distinguishes current and historical artifacts."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "validate_binary_register.py"
spec = importlib.util.spec_from_file_location("validate_binary_register", SCRIPT)
assert spec is not None and spec.loader is not None
register = importlib.util.module_from_spec(spec)
spec.loader.exec_module(register)


class BinaryRegisterTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True, capture_output=True)
        self.asset = {
            "path": "host-hooks/old.jar",
            "role": "Historical test fixture",
            "sha256": "a" * 64,
            "observed": {},
            "status": "pending",
            "present": False,
            "owner": None,
            "source": None,
            "license": None,
            "redistributionEvidence": None,
            "notes": "Synthetic fixture only",
        }
        notice = self.root / "THIRD_PARTY_NOTICES.md"
        notice.write_text("# Synthetic notice\n", encoding="utf-8")
        self.save_register()

    def save_register(self) -> None:
        path = self.root / "docs/third-party-assets.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            json.dumps({"schemaVersion": 1, "releaseBlocked": True, "assets": [self.asset]}),
            encoding="utf-8",
        )

    def test_removed_binary_is_inventoried_but_release_stays_blocked(self) -> None:
        self.assertEqual(register.validate(self.root, False), [])
        errors = register.validate(self.root, True)
        self.assertTrue(any("not cleared" in error for error in errors))
        self.assertTrue(any("releaseBlocked" in error for error in errors))

    def test_absent_asset_still_requires_valid_hash_and_status(self) -> None:
        self.asset["sha256"] = "not-a-hash"
        self.save_register()
        self.assertTrue(any("sha256" in error for error in register.validate(self.root, False)))
        self.asset["sha256"] = "a" * 64
        self.asset["present"] = "no"
        self.save_register()
        self.assertTrue(any("present must be a boolean" in error for error in register.validate(self.root, False)))

    def test_historical_entry_rejects_reintroduced_file(self) -> None:
        artifact = self.root / self.asset["path"]
        artifact.parent.mkdir()
        artifact.write_bytes(b"unapproved")
        self.assertTrue(any("still present" in error for error in register.validate(self.root, False)))


if __name__ == "__main__":
    unittest.main()
