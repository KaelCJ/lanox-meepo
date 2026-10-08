#!/usr/bin/env python3
"""Exercise the public-tree preflight against synthetic Git indexes and commits."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "validate_text_public_tree.py"
spec = importlib.util.spec_from_file_location("validate_text_public_tree", SCRIPT)
assert spec is not None and spec.loader is not None
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PublicTreeTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git("init", "-q")
        (self.root / ".gitignore").write_text(".workspace-assistant/\n", encoding="utf-8")
        (self.root / "README.md").write_text("# Synthetic fixture\n", encoding="utf-8")
        self.git("add", ".gitignore", "README.md")

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, check=True)

    def test_clean_text_tree_passes(self) -> None:
        self.assertEqual(preflight.problems(preflight.git_paths(self.root, None)), [])
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture")
        self.assertEqual(preflight.problems(preflight.git_paths(self.root, "HEAD")), [])

    def test_ignored_but_tracked_private_record_is_blocked(self) -> None:
        record = self.root / ".workspace-assistant/10-工作项/private/README.md"
        record.parent.mkdir(parents=True)
        record.write_text("private fixture\n", encoding="utf-8")
        self.git("add", "-f", ".workspace-assistant/10-工作项/private/README.md")
        errors = preflight.problems(preflight.git_paths(self.root, None))
        self.assertTrue(any("private/README.md" in error for error in errors))
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture")
        self.assertTrue(preflight.problems(preflight.git_paths(self.root, "HEAD")))

    def test_pending_jar_and_unregistered_binary_are_blocked(self) -> None:
        for name in ("pending.jar", "unknown.bin"):
            (self.root / name).write_bytes(b"\x00test")
        self.git("add", "pending.jar", "unknown.bin")
        errors = preflight.problems(preflight.git_paths(self.root, None))
        self.assertEqual(len(errors), 2)
        self.assertTrue(all("binary asset" in error for error in errors))

    def test_unreviewed_skill_and_hook_are_blocked(self) -> None:
        errors = preflight.problems([
            ".agents/skills/nest-rule-java/SKILL.md",
            ".claude/commands/nest-rule-java.md",
            ".codex/hooks.json",
            ".nest-insights/cache.json",
            ".api-security-audit/run/manifest.json",
        ])
        self.assertEqual(len(errors), 5)


if __name__ == "__main__":
    unittest.main()
