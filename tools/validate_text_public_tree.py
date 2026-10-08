#!/usr/bin/env python3
"""Fail if a proposed public Git tree contains known private or non-text assets."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


BLOCKED_PREFIXES = (
    ".workspace-assistant/",
    ".api-security-audit/",
    ".nest-insights/",
    ".codex/sessions/",
    ".claude/worktrees/",
    ".agents/skills/nest-rule-java/",
    ".agents/skills/nest-audit-java/",
    ".agents/skills/nest-audit-security-api/",
    ".agents/skills/nest-insights/",
)
BLOCKED_FILES = {
    ".codex/hooks.json",
    ".claude/settings.local.json",
    ".claude/commands/nest-rule-java.md",
    ".claude/commands/nest-audit-java.md",
    ".claude/commands/nest-audit-security-api.md",
    ".claude/commands/nest-insights.md",
}
BINARY_SUFFIXES = {
    ".bin", ".class", ".db", ".dll", ".dylib", ".exe", ".gif",
    ".ico", ".jar", ".jpeg", ".jpg", ".pdf", ".png", ".pyc",
    ".so", ".sqlite", ".sqlite3", ".wasm", ".webp", ".zip",
}


def git_paths(root: Path, ref: str | None) -> list[str]:
    command = ["git", "-C", str(root)]
    command += ["ls-tree", "-r", "-z", "--name-only", ref] if ref else ["ls-files", "-z"]
    result = subprocess.run(command, capture_output=True, check=True)
    return [path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


def problems(paths: list[str]) -> list[str]:
    errors = []
    for path in paths:
        reason = None
        if path.startswith(BLOCKED_PREFIXES) or path in BLOCKED_FILES:
            reason = "private or unreviewed path"
        elif path == ".env" or path.startswith(".env."):
            reason = "environment file"
        elif Path(path).suffix.lower() in BINARY_SUFFIXES:
            reason = "binary asset requires separate release review"
        elif path.startswith("nest-insights-report-") and path.endswith(".html"):
            reason = "generated session report"
        if reason:
            errors.append(f"{path}: {reason}")
    return errors


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ref", help="Inspect a committed Git tree (e.g. HEAD); default checks the index")
    parser.add_argument("--list-paths", action="store_true", help="Print blocked paths in a trusted local environment")
    options = parser.parse_args()
    try:
        paths = git_paths(options.root.resolve(), options.ref)
    except (OSError, UnicodeDecodeError, subprocess.CalledProcessError) as error:
        print(f"ERROR: could not inspect Git tree: {error}", file=sys.stderr)
        return 1
    errors = problems(paths)
    if errors:
        print(f"BLOCKED: {len(errors)} known private, unreviewed or binary Git entries", file=sys.stderr)
        if options.list_paths:
            for error in errors:
                print(f"  {error}", file=sys.stderr)
        else:
            print("Run again with --list-paths in a trusted local environment for details.", file=sys.stderr)
        return 1
    print(f"PASS: no blocked paths among {len(paths)} Git entries (path check only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
