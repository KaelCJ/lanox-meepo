#!/usr/bin/env python3
"""Check the offline text-only installation in a disposable target."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/install_text_core.py"
ENTRY_CHECK = ROOT / ".agents/skills/nest-rule-entry/scripts/validate_entry_pairs.py"

spec = importlib.util.spec_from_file_location("install_text_core", SCRIPT)
assert spec is not None and spec.loader is not None
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class TextCoreInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.target = self.root / "target"
        self.target.mkdir()

    def test_installs_only_explicit_text_assets(self) -> None:
        (self.target / "app.txt").write_text("keep me\n", encoding="utf-8")
        installer.install(ROOT, self.target)
        installed = {
            path.relative_to(self.target).as_posix()
            for directory in (".agents", ".claude")
            for path in (self.target / directory).rglob("*")
            if path.is_file()
        }
        self.assertEqual(installed, set(installer.ASSETS))
        self.assertEqual((self.target / "app.txt").read_text(encoding="utf-8"), "keep me\n")
        self.assertFalse(list(self.target.rglob("*.jar")))
        self.assertFalse((self.target / ".codex").exists())
        self.assertFalse((self.target / ".workspace-assistant").exists())
        self.assertFalse((self.target / ".claude/settings.local.json").exists())
        self.assertFalse((self.target / ".claude/worktrees").exists())
        for name in ("nest-audit-entry", "nest-work-item"):
            command = (self.target / f".claude/commands/{name}.md").read_text(encoding="utf-8")
            self.assertIn(f".agents/skills/{name}/SKILL.md", command)
        for relative in installed:
            if not relative.endswith(".md"):
                continue
            path = self.target / relative
            for link in re.findall(r"\[[^]]+\]\(([^)#]+)(?:#[^)]*)?\)", path.read_text(encoding="utf-8")):
                if "://" not in link:
                    self.assertTrue((path.parent / link).is_file(), f"broken reference: {relative} -> {link}")
        schema = json.loads((self.target / installer.WORK_ITEM / "assets/index.schema.json").read_text(encoding="utf-8"))
        self.assertNotIn(".local", schema["$id"])

    def test_installed_index_runs_without_java(self) -> None:
        installer.install(ROOT, self.target)
        script = self.target / installer.WORK_ITEM / "scripts/work_item_index.py"
        index = self.target / ".workspace-assistant/10-工作项"
        environment = os.environ.copy()
        environment["PATH"] = ""

        def run(*arguments: str) -> dict:
            result = subprocess.run(
                [sys.executable, str(script), "--root", str(index), *arguments],
                capture_output=True, text=True, encoding="utf-8", env=environment,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)

        self.assertEqual(run("init")["idStrategy"], "r-uuid4")
        self.assertTrue(re.fullmatch(r"R[0-9a-f]{32}", run("new-id")["id"]))
        self.assertTrue(run("validate")["valid"])

    def test_target_entry_pair_is_not_copied_from_source(self) -> None:
        installer.install(ROOT, self.target)
        missing = subprocess.run(
            [sys.executable, str(ENTRY_CHECK), "--directory", str(self.target)],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("missing AGENTS.md, CLAUDE.md", missing.stderr)
        (self.target / "AGENTS.md").write_text("# Synthetic target rules\n", encoding="utf-8")
        (self.target / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
        verified = subprocess.run(
            [sys.executable, str(ENTRY_CHECK), "--directory", str(self.target)],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
        self.assertIn("PASS: 1 entry pair(s)", verified.stdout)

    def test_does_not_overwrite_existing_agent_assets(self) -> None:
        existing = self.target / ".agents/skills/custom/SKILL.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("custom\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "already has .agents"):
            installer.install(ROOT, self.target)
        self.assertEqual(existing.read_text(encoding="utf-8"), "custom\n")
        self.assertFalse((self.target / ".claude").exists())

    def test_rejects_missing_source_before_writing(self) -> None:
        source = self.root / "source"
        for relative in installer.ASSETS:
            asset = source / relative
            asset.parent.mkdir(parents=True, exist_ok=True)
            asset.write_bytes(b"text\n")
        (source / installer.ASSETS[0]).unlink()
        with self.assertRaisesRegex(ValueError, "missing source asset"):
            installer.install(source, self.target)
        self.assertEqual(list(self.target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
