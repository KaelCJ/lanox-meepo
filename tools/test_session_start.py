#!/usr/bin/env python3
"""Verify the Python SessionStart handlers with synthetic context only."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/session_start.py"


class SessionStartTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.script = self.root / "tools/session_start.py"
        self.script.parent.mkdir()
        self.script.write_bytes(SCRIPT.read_bytes())
        self.context = self.root / ".workspace-assistant/foundation/host-hooks/session-start-context.md"
        self.context.parent.mkdir(parents=True)
        self.text = '# Demo "rules" \\ path\n中文\tcontrol:\x01\n'
        self.context.write_bytes(self.text.encode("utf-8"))
        self.other_cwd = self.root / "subdirectory"
        self.other_cwd.mkdir()

    def run_hook(self, host: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PATH"] = ""
        return subprocess.run(
            [sys.executable, str(self.script), host],
            input="not JSON; this handler does not read stdin",
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=self.other_cwd,
            env=environment,
            check=False,
        )

    def test_host_responses_and_utf8_escaping(self) -> None:
        for host in ("claude", "codex"):
            with self.subTest(host=host):
                result = self.run_hook(host)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(len(result.stdout.splitlines()), 1)
                self.assertIn("\\u0001", result.stdout)
                output = json.loads(result.stdout)["hookSpecificOutput"]
                self.assertEqual(output["hookEventName"], "SessionStart")
                self.assertEqual(output["additionalContext"], self.text)
                if host == "claude":
                    self.assertIs(output["reloadSkills"], True)
                else:
                    self.assertNotIn("reloadSkills", output)

    def test_preserves_original_line_endings(self) -> None:
        self.context.write_bytes(b"first\r\nsecond\r\n")
        result = self.run_hook("codex")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"], "first\r\nsecond\r\n")

    def test_missing_or_invalid_context_never_emits_success(self) -> None:
        self.context.unlink()
        missing = self.run_hook("codex")
        self.assertNotEqual(missing.returncode, 0)
        self.assertEqual(missing.stdout, "")
        self.assertIn("cannot read SessionStart context", missing.stderr)

        self.context.write_bytes(b"\xffinvalid UTF-8")
        invalid = self.run_hook("claude")
        self.assertNotEqual(invalid.returncode, 0)
        self.assertEqual(invalid.stdout, "")

    def test_codex_config_invokes_python(self) -> None:
        config = json.loads((ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))
        entry = config["hooks"]["SessionStart"][0]
        self.assertEqual(entry["matcher"], "startup|clear|compact")
        self.assertEqual(entry["hooks"][0]["command"], "python tools/session_start.py codex")


if __name__ == "__main__":
    unittest.main()
