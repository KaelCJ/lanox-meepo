#!/usr/bin/env python3
"""Validate a generated audit run without judging the security conclusions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


API_FILES = (
    "agent/brief.md",
    "agent/brief.json",
    "contract.md",
    "protection-chain.md",
    "call-graph.md",
    "sequence.mmd",
    "data-model.md",
    "data-model.mmd",
    "findings.md",
    "unconfirmed.md",
    "review.md",
    "verdict.json",
)
VERDICT_STATES = {"通过", "失败", "未确认", "不适用"}
RUN_STATES = {"pending", "in_progress", "complete", "blocked", "needs_review"}
SEVERITIES = {"严重", "高", "中", "低", "无"}
PRIORITIES = {"P0", "P1", "P2", "P3", "无"}
CONFIDENCES = {"高", "中", "低"}
REQUIRED_VERDICT_KEYS = {
    "api_id",
    "status",
    "local_verdict",
    "global_baseline",
    "release_verdict",
    "severity",
    "priority",
    "confidence",
    "finding_ids",
    "unconfirmed_fact_ids",
    "review",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path, help="Generated audit run directory")
    parser.add_argument("--stage", choices=("inventory", "deep", "review", "all"), default="all")
    parser.add_argument("--allow-pending", action="store_true", help="Report pending APIs without failing")
    args = parser.parse_args()
    root = args.run.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        errors.append("missing manifest.json")
        print_report(root, errors, warnings)
        return 1
    try:
        manifest = load_json(manifest_path)
    except (OSError, ValueError) as exc:
        errors.append(f"invalid manifest.json: {exc}")
        print_report(root, errors, warnings)
        return 1

    entries = manifest.get("apis") if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or not entries:
        errors.append("manifest.apis must be a non-empty list")
        entries = []
    ids = [str(item.get("api_id", "")) for item in entries if isinstance(item, dict)]
    if len(ids) != len(set(ids)):
        errors.append("manifest contains duplicate api_id values")
    if manifest.get("api_count") != len(entries):
        errors.append("manifest.api_count does not match manifest.apis")

    if args.stage in {"inventory", "deep", "review", "all"}:
        for path in (root / "ledger.json", root / "macro" / "api-inventory.csv"):
            if not path.is_file():
                errors.append(f"missing inventory artifact: {path.relative_to(root)}")

    pending = 0
    complete = 0
    blocked = 0
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("manifest contains a non-object API entry")
            continue
        api_id = str(entry.get("api_id", ""))
        directory = str(entry.get("directory", ""))
        api_root = root / "apis" / directory
        if not api_id or not directory:
            errors.append("API entry missing api_id or directory")
            continue
        if not api_root.is_dir():
            errors.append(f"{api_id}: missing directory {api_root.relative_to(root)}")
            continue
        if args.stage in {"deep", "review", "all"}:
            for relative in API_FILES:
                path = api_root / relative
                if not path.is_file() or not path.read_text(encoding="utf-8-sig").strip():
                    errors.append(f"{api_id}: missing or empty {relative}")
        verdict_path = api_root / "verdict.json"
        if not verdict_path.is_file():
            continue
        try:
            verdict = load_json(verdict_path)
        except (OSError, ValueError) as exc:
            errors.append(f"{api_id}: invalid verdict.json: {exc}")
            continue
        missing_keys = REQUIRED_VERDICT_KEYS - set(verdict)
        if missing_keys:
            errors.append(f"{api_id}: verdict missing {', '.join(sorted(missing_keys))}")
            continue
        if verdict.get("api_id") != api_id:
            errors.append(f"{api_id}: verdict.api_id mismatch")
        status = verdict.get("status")
        if status not in RUN_STATES:
            errors.append(f"{api_id}: invalid status {status!r}")
        elif status == "pending" or status == "in_progress":
            pending += 1
            if not args.allow_pending and args.stage in {"deep", "review", "all"}:
                errors.append(f"{api_id}: deep audit is not complete ({status})")
        elif status == "complete":
            complete += 1
        else:
            blocked += 1
            if not args.allow_pending and args.stage in {"deep", "review", "all"}:
                errors.append(f"{api_id}: blocked or needs review ({status})")
        if verdict.get("local_verdict") not in VERDICT_STATES:
            errors.append(f"{api_id}: invalid local_verdict {verdict.get('local_verdict')!r}")
        if verdict.get("release_verdict") not in {"通过", "失败", "未确认"}:
            errors.append(f"{api_id}: invalid release_verdict {verdict.get('release_verdict')!r}")
        if verdict.get("confidence") not in CONFIDENCES:
            errors.append(f"{api_id}: invalid confidence {verdict.get('confidence')!r}")
        if verdict.get("global_baseline") not in VERDICT_STATES:
            errors.append(f"{api_id}: invalid global_baseline {verdict.get('global_baseline')!r}")
        if verdict.get("severity") not in SEVERITIES:
            errors.append(f"{api_id}: invalid severity {verdict.get('severity')!r}")
        if verdict.get("priority") not in PRIORITIES:
            errors.append(f"{api_id}: invalid priority {verdict.get('priority')!r}")
        review = verdict.get("review")
        if not isinstance(review, dict) or review.get("status") not in {"pending", "complete", "conflict"}:
            errors.append(f"{api_id}: invalid review object")
        elif args.stage in {"review", "all"} and review.get("required") and review.get("status") != "complete":
            errors.append(f"{api_id}: required review is not complete")

    if pending and args.allow_pending:
        warnings.append(f"pending/in-progress APIs: {pending}")
    if blocked and args.allow_pending:
        warnings.append(f"blocked/needs-review APIs: {blocked}")
    print_report(root, errors, warnings, complete=complete, pending=pending, blocked=blocked)
    return 1 if errors else 0


def print_report(root: Path, errors: list[str], warnings: list[str], **counts: int) -> None:
    print(json.dumps({"run": str(root), "ok": not errors, "counts": counts, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
