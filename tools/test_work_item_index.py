#!/usr/bin/env python3
"""Exercise work-item IDs and legacy index records without real workspace data."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".agents/skills/nest-work-item/scripts/work_item_index.py"
SCHEMA = ROOT / ".agents/skills/nest-work-item/assets/index.schema.json"

spec = importlib.util.spec_from_file_location("work_item_index", SCRIPT)
assert spec is not None and spec.loader is not None
work_item_index = importlib.util.module_from_spec(spec)
spec.loader.exec_module(work_item_index)


class WorkItemIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "10-工作项"
        initialized = work_item_index.initialize(self.root)
        self.assertEqual(initialized["idStrategy"], "r-uuid4")

    def run_index(self, *arguments: str, without_java: bool = False) -> dict:
        environment = os.environ.copy()
        if without_java:
            environment["PATH"] = ""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def create_entry(self, item_id: str, title: str) -> str:
        directory = self.root / f"2026-01-02_{item_id}_{title}"
        directory.mkdir()
        (directory / "README.md").write_text(f"# {title}\n", encoding="utf-8")
        return f"{directory.name}/README.md"

    def test_uuid4_cli_needs_no_java(self) -> None:
        generated = [self.run_index("new-id", without_java=True) for _ in range(12)]
        identifiers = [value["id"] for value in generated]
        self.assertEqual(len(set(identifiers)), len(identifiers))
        for value in generated:
            self.assertEqual(value["idStrategy"], "r-uuid4")
            self.assertRegex(value["id"], r"^R[0-9a-f]{32}$")
            self.assertEqual(uuid.UUID(value["id"][1:]).version, 4)

    def test_collisions_check_both_indexes(self) -> None:
        tokens = [uuid.UUID(int=value) for value in (0, 1, 2)]
        current = {"items": [{"id": "R" + tokens[0].hex}]}
        archive = {"items": [{"id": "r" + tokens[1].hex}]}
        with patch.object(work_item_index.uuid, "uuid4", side_effect=tokens) as generator:
            self.assertEqual(
                work_item_index.generated_work_item_id(current, archive),
                "R" + tokens[2].hex,
            )
        self.assertEqual(generator.call_count, 3)

        with patch.object(work_item_index.uuid, "uuid4", return_value=tokens[0]) as generator:
            with self.assertRaisesRegex(RuntimeError, "could not allocate a unique UUID4"):
                work_item_index.generated_work_item_id(current, archive)
        self.assertEqual(generator.call_count, 10)

    def test_legacy_and_new_ids_share_lifecycle(self) -> None:
        legacy_id = "Rabcdefghijklmnopqrs"
        new_id = self.run_index("new-id")["id"]
        for item_id, title in ((legacy_id, "legacy"), (new_id, "new")):
            entry = self.create_entry(item_id, title)
            self.run_index(
                "create", "--id", item_id, "--title", title,
                "--entry", entry, "--created-at", "2026-01-02T12:00:00+00:00",
            )
        self.assertEqual(self.run_index("validate")["currentCount"], 2)
        self.assertEqual(self.run_index("resolve", legacy_id)["item"]["id"], legacy_id)
        self.assertEqual(self.run_index("resolve", new_id)["item"]["id"], new_id)
        self.assertEqual(self.run_index("list")["itemCount"], 2)

        self.run_index("archive", legacy_id, "--at", "2026-01-03T12:00:00+00:00")
        self.assertEqual(self.run_index("validate")["archiveCount"], 1)
        self.assertEqual(self.run_index("resolve", legacy_id)["source"], "archive.json")
        self.run_index("unarchive", legacy_id, "--at", "2026-01-04T12:00:00+00:00")
        self.assertEqual(self.run_index("validate")["currentCount"], 2)
        self.assertEqual(self.run_index("resolve", legacy_id)["source"], "current.json")

    def test_stored_id_schema_remains_format_agnostic(self) -> None:
        source = json.loads(SCHEMA.read_text(encoding="utf-8"))
        installed = json.loads((self.root / "index.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(source, installed)
        for name in ("currentItem", "archiveItem"):
            identifier = source["$defs"][name]["properties"]["id"]
            self.assertEqual(identifier["pattern"], r"\S")
            self.assertTrue(re.search(identifier["pattern"], "Rabcdefghijklmnopqrs"))


if __name__ == "__main__":
    unittest.main()
