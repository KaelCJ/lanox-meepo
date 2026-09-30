#!/usr/bin/env python3
"""Create an isolated per-API audit run from a CSV or JSON manifest."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS = ("API_ID", "Protocol_Method_Path")
PLACEHOLDER_FILES = {
    "contract.md": "# Contract\n\n待 G2 API Agent 独立填写。\n",
    "protection-chain.md": "# Protection chain\n\n待 G2 API Agent 独立填写。\n",
    "call-graph.md": "# Call graph and source/sink\n\n待 G2 API Agent 独立填写。\n",
    "sequence.mmd": "sequenceDiagram\n    %% 待 G2 API Agent 独立填写\n",
    "data-model.md": "# Data model\n\n待 G2 API Agent 独立填写。\n",
    "data-model.mmd": "erDiagram\n    %% 待 G2 API Agent 独立填写\n",
    "findings.md": "# Findings\n\n当前 API 尚未完成独立深审。\n",
    "unconfirmed.md": "# Unconfirmed facts\n\n当前 API 尚未完成独立深审。\n",
    "review.md": "# Independent review\n\n待 G4 reviewer 填写。\n",
}


def read_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        records = raw.get("apis", raw) if isinstance(raw, dict) else raw
        if not isinstance(records, list):
            raise ValueError("JSON manifest must be a list or an object with an 'apis' list")
        return [dict(item) for item in records]

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def slug_for(record: dict[str, Any]) -> str:
    api_id = str(record["API_ID"]).strip()
    path = str(record["Protocol_Method_Path"]).strip()
    tail = path.split(" ", 1)[-1].strip("/")
    tail = re.sub(r"[^A-Za-z0-9._-]+", "-", tail).strip("-") or "root"
    return f"{api_id}-{tail}"[:120]


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="G1 CSV or JSON API manifest")
    parser.add_argument("--output", required=True, type=Path, help="New audit run directory")
    parser.add_argument("--run-id", default=None, help="Stable run identifier")
    args = parser.parse_args()

    records = read_records(args.manifest)
    if not records:
        raise ValueError("manifest contains no API records")
    missing = [column for column in REQUIRED_COLUMNS if any(not str(row.get(column, "")).strip() for row in records)]
    if missing:
        raise ValueError(f"manifest has missing required values: {', '.join(missing)}")

    ids = [str(row["API_ID"]).strip() for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError("manifest contains duplicate API_ID values")

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"output already exists and is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for directory in ("macro", "shared/domains", "shared/flows", "shared/variants", "apis", "findings"):
        (output / directory).mkdir(parents=True, exist_ok=True)

    fieldnames: list[str] = []
    for row in records:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with (output / "macro" / "api-inventory.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    manifest_records: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    for record in records:
        api_id = str(record["API_ID"]).strip()
        directory = slug_for(record)
        api_root = output / "apis" / directory
        if api_root.exists():
            raise FileExistsError(f"API directory collision: {api_root}")
        (api_root / "agent").mkdir(parents=True)
        brief = {
            "api_id": api_id,
            "protocol_method_path": record.get("Protocol_Method_Path"),
            "manifest_record": record,
            "allowed_inputs": ["this API record", "macro indexes", "relevant source/config", "skill references"],
            "forbidden_inputs": ["other API findings/verdicts", "reviewer conclusions", "unstated business assumptions"],
        }
        write_json(api_root / "agent" / "brief.json", brief)
        write_text(
            api_root / "agent" / "brief.md",
            "# 独立 API 深审任务\n\n"
            f"- API ID：`{api_id}`\n"
            f"- 入口：`{record.get('Protocol_Method_Path', '')}`\n"
            "- 只读取本 brief、G1 宏观索引、相关源码和本 Skill references。\n"
            "- 禁止读取其他 API 的 findings、verdict 或 reviewer 结论。\n"
            "- G1 风险项只是待验证假设；必须从当前 API 的输入、分支、主体、对象和 sink 重新证明。\n"
            "- 必须填写当前目录下的 contract、protection-chain、call-graph、sequence、data-model、findings、unconfirmed 和 verdict。\n",
        )
        write_json(api_root / "agent" / "result.json", {"api_id": api_id, "status": "pending"})
        for name, content in PLACEHOLDER_FILES.items():
            write_text(api_root / name, content)
        write_json(
            api_root / "verdict.json",
            {
                "api_id": api_id,
                "status": "pending",
                "local_verdict": "未确认",
                "global_baseline": "未确认",
                "release_verdict": "未确认",
                "severity": "无",
                "priority": "无",
                "confidence": "低",
                "finding_ids": [],
                "unconfirmed_fact_ids": [],
                "review": {"required": False, "status": "pending"},
            },
        )
        manifest_records.append({"api_id": api_id, "directory": directory, "record": record})
        statuses.append({"api_id": api_id, "directory": directory, "status": "pending"})

    write_json(
        output / "manifest.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_manifest": str(args.manifest.resolve()),
            "api_count": len(records),
            "apis": manifest_records,
        },
    )
    write_json(
        output / "ledger.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "current_stage": "G1",
            "gate_status": {"G1": "complete", "G2": "pending", "G3": "pending", "G4": "pending", "G5": "pending"},
            "api_status": statuses,
            "rules": {"skill": "nest-audit-security-api", "target_statuses": ["通过", "失败", "未确认", "不适用"]},
        },
    )
    write_text(output / "macro" / "protection-profiles.md", "# G1 Protection profiles\n\n待主 Agent 填写宏观组件索引；不能代替逐 API 证据。\n")
    write_text(output / "macro" / "global-findings.md", "# Global baseline findings\n\n待主 Agent 填写全局日志、CORS、配置和部署问题。\n")
    write_text(output / "shared" / "domain-index.md", "# Domain index\n\n待 G1 填写共享实体、业务域和潜在跨 API 流程。\n")
    write_text(output / "findings" / "prioritized-findings.md", "# Prioritized findings\n\n待 G5 汇总。\n")
    write_text(output / "findings" / "remediation-plan.md", "# Remediation plan\n\n待 G5 汇总。\n")
    print(json.dumps({"run_id": run_id, "output": str(output), "api_count": len(records)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
