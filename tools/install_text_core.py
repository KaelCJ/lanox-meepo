#!/usr/bin/env python3
"""Copy the initial text-only workflow from an authorized local source."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


WORK_ITEM = ".agents/skills/nest-work-item/"
ASSETS = (
    ".agents/skills/nest-audit-entry/SKILL.md",
    WORK_ITEM + "SKILL.md",
    WORK_ITEM + "assets/index.schema.json",
    WORK_ITEM + "references/工作项README模板.md",
    WORK_ITEM + "references/索引与定位方法.md",
    WORK_ITEM + "references/方法/原始需求方法.md",
    WORK_ITEM + "references/方法/执行方法.md",
    WORK_ITEM + "references/方法/方案/方案方法.md",
    WORK_ITEM + "references/方法/方案/时序设计方法.md",
    WORK_ITEM + "references/方法/正式需求方法.md",
    WORK_ITEM + "references/方法/认知拉齐方法.md",
    WORK_ITEM + "references/流程/创建工作项方法.md",
    WORK_ITEM + "references/流程/只读Review方法.md",
    WORK_ITEM + "references/流程/建档方法.md",
    WORK_ITEM + "references/流程/更新工作项方法.md",
    WORK_ITEM + "references/流程/继续工作项方法.md",
    WORK_ITEM + "scripts/work_item_index.py",
    ".claude/commands/nest-audit-entry.md",
    ".claude/commands/nest-work-item.md",
)


def install(source: Path, target: Path) -> None:
    if not source.is_dir() or not target.is_dir():
        raise ValueError("source and target must be existing directories")
    if any((target / name).exists() for name in (".agents", ".claude")):
        raise ValueError("target already has .agents or .claude; no files were copied")

    for relative in ASSETS:
        if not (source / relative).is_file():
            raise ValueError(f"missing source asset: {relative}")

    for relative in ASSETS:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True, help="Existing target project without .agents or .claude")
    options = parser.parse_args()
    try:
        install(Path(__file__).resolve().parents[1], options.target.expanduser())
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Copied {len(ASSETS)} allowlisted files; no host hook was installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
