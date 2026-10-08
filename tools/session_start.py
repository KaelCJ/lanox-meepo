#!/usr/bin/env python3
"""Emit the shared SessionStart context for Claude Code or Codex."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CONTEXT = Path(".workspace-assistant/foundation/host-hooks/session-start-context.md")


def response(host: str, context: str) -> dict:
    output = {"hookEventName": "SessionStart"}
    if host == "claude":
        output["reloadSkills"] = True
    output["additionalContext"] = context
    return {"hookSpecificOutput": output}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", choices=("claude", "codex"))
    options = parser.parse_args()
    context_path = Path(__file__).resolve().parents[1] / CONTEXT
    try:
        context = context_path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        print(f"ERROR: cannot read SessionStart context: {error}", file=sys.stderr)
        return 1
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(response(options.host, context), ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
