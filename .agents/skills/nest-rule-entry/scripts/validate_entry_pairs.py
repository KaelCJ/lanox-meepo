#!/usr/bin/env python3
"""Validate AGENTS.md canonical entries and CLAUDE.md import wrappers."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


EXPECTED_IMPORT = "@AGENTS.md"
DEFAULT_EXCLUDES = {".git", "target", "build", "dist"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate AGENTS.md canonical entries and CLAUDE.md import wrappers."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--directory",
        action="append",
        help="Directory containing an active entry pair. Repeat for multiple directories.",
    )
    group.add_argument(
        "--root",
        help="Discover CLAUDE.md entry directories below this root, including hidden directories.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Relative directory subtree to exclude when using --root. Repeat as needed.",
    )
    return parser.parse_args()


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def validate_directory(value: str) -> list[str]:
    directory = Path(value).expanduser().resolve()
    if not directory.is_dir():
        return [f"not a directory: {directory}"]

    agents_path = directory / "AGENTS.md"
    claude_path = directory / "CLAUDE.md"
    missing = [path.name for path in (agents_path, claude_path) if not path.is_file()]
    if missing:
        return [f"{directory}: missing {', '.join(missing)}"]

    agents = normalize(agents_path.read_text(encoding="utf-8"))
    claude = normalize(claude_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    if claude.strip() != EXPECTED_IMPORT:
        errors.append(
            f"{claude_path}: must contain exactly '{EXPECTED_IMPORT}' and no duplicated or host-specific正文"
        )
    if "<!-- host-only:" in agents or "<!-- host-only:" in claude:
        errors.append(f"{directory}: host-only blocks are not enabled by the current entry contract")
    if "@CLAUDE.md" in agents or "@CLAUDE.md" in claude:
        errors.append(f"{directory}: reverse CLAUDE.md import is forbidden")
    return errors


def discover_directories(root_value: str, excludes: list[str]) -> list[str]:
    root = Path(root_value).expanduser().resolve()
    if not root.is_dir():
        return [str(root)]

    excluded = {
        Path(item).as_posix().strip("/").rstrip("/")
        for item in excludes
        if item
    }
    try:
        command = ["rg", "--files", "--hidden", "-g", "CLAUDE.md"]
        for item in sorted(DEFAULT_EXCLUDES):
            command.extend(["-g", f"!{item}/**"])
        for item in excluded:
            command.extend(["-g", f"!{item}/**"])
        result = subprocess.run(
            command,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr.strip() or "rg failed")
        return sorted(
            {
                str((root / line.strip()).parent)
                for line in result.stdout.splitlines()
                if line.strip()
            }
        )
    except (FileNotFoundError, OSError, RuntimeError):
        pass

    directories: set[Path] = set()
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        relative_current = current_path.relative_to(root).as_posix()
        current_parts = relative_current.split("/") if relative_current else []
        if any(part in DEFAULT_EXCLUDES for part in current_parts):
            dirnames[:] = []
            continue
        if any(
            relative_current == item or relative_current.startswith(f"{item}/")
            for item in excluded
        ):
            dirnames[:] = []
            continue

        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not os.path.islink(current_path / dirname)
            and dirname not in DEFAULT_EXCLUDES
            and not any(
                (
                    f"{relative_current}/{dirname}" == item
                    or f"{relative_current}/{dirname}".startswith(f"{item}/")
                )
                for item in excluded
            )
        ]
        if "CLAUDE.md" in filenames:
            directories.add(current_path)
    return [str(path) for path in sorted(directories)]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()
    directories = args.directory or discover_directories(args.root, args.exclude)
    errors = [
        error
        for directory in directories
        for error in validate_directory(directory)
    ]
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {len(directories)} entry pair(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
