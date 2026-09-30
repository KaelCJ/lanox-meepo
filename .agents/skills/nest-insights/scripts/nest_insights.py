#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from insights.aggregate import aggregate, narrative_payload
from insights.contracts import (
    PARSER_VERSION, REPORT_FILENAME_PREFIX, atomic_write_json, cache_path, digest, read_json,
)
from insights.discover import build_inventory, candidate_roots, locate_codex_home
from insights.facet_runner import ModelCallError, load_cached_facet, run_facet
from insights.narratives import generate_sections
from insights.parse_rollout import build_facet_packet, parse_task, source_fingerprint
from insights.render import render_report


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ASSET_DIR = SKILL_DIR / "assets"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan Codex session history and generate a Chinese HTML insights report."
    )
    parser.add_argument("--workspace-root", type=Path, help="Git workspace receiving the report")
    parser.add_argument("--codex-home", type=Path, help="Override CODEX_HOME for diagnostics")
    parser.add_argument("--scan-only", action="store_true", help="Do not call Codex models")
    parser.add_argument("--max-new-task-meta", type=int, default=1000)
    parser.add_argument("--max-new-facets", type=int, default=50)
    parser.add_argument("--facet-sample-size", type=int, default=50)
    parser.add_argument("--facet-concurrency", type=int, default=4)
    parser.add_argument("--chapter-concurrency", type=int, default=3)
    parser.add_argument("--model", help="Optional model override")
    parser.add_argument("--include-active", action="store_true", help="Include writer-locked threads")
    parser.add_argument("--no-chapters", action="store_true", help="Render deterministic report without chapter calls")
    parser.add_argument("--json-summary", action="store_true", help="Print machine-readable final summary")
    return parser.parse_args()


def git_root(explicit: Path | None) -> Path:
    if explicit is not None:
        root = explicit.expanduser().resolve()
    else:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError("current directory is not inside a Git workspace")
        root = Path(completed.stdout.strip()).resolve()
    if not (root / ".git").exists():
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if completed.returncode != 0 or Path(completed.stdout.strip()).resolve() != root:
            raise RuntimeError(f"not a Git workspace root: {root}")
    return root


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        completed = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return completed.returncode == 0 and str(pid) in completed.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_lock(runtime_root: Path) -> Path:
    lock = runtime_root / "run.lock"
    runtime_root.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        age = time.time() - lock.stat().st_mtime
        owner_alive = False
        try:
            owner = read_json(lock)
            owner_pid = int(owner.get("pid", 0))
            owner_alive = pid_alive(owner_pid)
        except (OSError, ValueError, TypeError, AttributeError, SystemError):
            owner_alive = False
        if owner_alive and age < 6 * 60 * 60:
            raise RuntimeError("another Nest Insights run appears active") from exc
        stale = runtime_root / f"run.lock.stale-{int(time.time())}"
        os.replace(lock, stale)
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(json.dumps({"pid": os.getpid(), "started_at": datetime.now(timezone.utc).isoformat()}))
    return lock


def load_valid_task_cache(path: Path, fingerprint: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = read_json(path)
    except (OSError, ValueError):
        return None
    if (
        value.get("status") == "success"
        and value.get("parser_version") == PARSER_VERSION
        and value.get("source_fingerprint") == fingerprint
        and isinstance(value.get("task_meta"), dict)
    ):
        return value["task_meta"]
    return None


def save_task_cache(path: Path, task: dict[str, Any]) -> None:
    atomic_write_json(path, {
        "status": "success", "parser_version": PARSER_VERSION,
        "source_fingerprint": task["source_fingerprint"], "task_meta": task,
    })


def empty_sections(reason: str) -> dict[str, dict[str, Any]]:
    names = (
        "at_a_glance", "project_areas", "interaction_style", "what_works",
        "friction_analysis", "suggestions", "on_the_horizon", "fun_ending",
    )
    return {
        name: {
            "title": name, "lead": reason, "findings": [], "actions": [],
            "closing": "继续运行并生成更多 Facet 后，本章会自动补齐。", "confidence": 0,
        }
        for name in names
    }


def select_facet_sample(task_metas: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    valid = [task for task in task_metas if task.get("user_turns")]
    if limit <= 0:
        return []
    if len(valid) <= limit:
        return sorted(valid, key=lambda value: str(value.get("task_alias", "")))
    chronological = sorted(valid, key=lambda value: value.get("started_at") or "")
    temporal_count = max(1, limit * 7 // 10)
    temporal_indices = {
        round(index * (len(chronological) - 1) / max(1, temporal_count - 1))
        for index in range(temporal_count)
    }
    selected = {chronological[index]["task_alias"]: chronological[index] for index in temporal_indices}
    high_signal = sorted(
        valid,
        key=lambda task: (
            int(task.get("turns_started", 0)), int(task.get("turns_aborted", 0)),
            int(task.get("child_threads", 0)), int(task.get("compactions", 0)),
            str(task.get("task_alias", "")),
        ),
        reverse=True,
    )
    for task in high_signal:
        if len(selected) >= limit:
            break
        selected.setdefault(task["task_alias"], task)
    return sorted(selected.values(), key=lambda value: str(value.get("task_alias", "")))


def previous_attempted_facets(runtime_root: Path) -> set[str]:
    current = runtime_root / "current.json"
    if not current.is_file():
        return set()
    try:
        value = read_json(current)
        run_id = str(value.get("run_id", ""))
    except (OSError, ValueError, TypeError, AttributeError):
        return set()
    attempted = runtime_root / "runs" / run_id / "model-work" / "facets"
    if not attempted.is_dir():
        return set()
    return {path.name for path in attempted.iterdir() if path.is_dir()}


def run() -> dict[str, Any]:
    args = parse_args()
    workspace = git_root(args.workspace_root)
    codex_home = locate_codex_home(args.codex_home)
    if not codex_home.is_dir():
        raise RuntimeError(f"Codex home not found: {codex_home}")
    if not args.scan_only and shutil.which("codex") is None:
        raise RuntimeError("codex CLI not found")

    runtime_root = workspace / ".nest-insights"
    cache_root = runtime_root / "cache"
    generated_at = datetime.now().astimezone()
    run_id = generated_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_root = runtime_root / "runs" / run_id
    isolated_root = run_root / "model-work"
    report_filename = f"{REPORT_FILENAME_PREFIX}-{generated_at.strftime('%Y%m%d-%H%M%S')}.html"
    report_path = workspace / report_filename
    lock = acquire_lock(runtime_root)

    try:
        inventory = build_inventory(codex_home)
        roots = candidate_roots(inventory)
        current_ids = {
            value for key in ("CODEX_THREAD_ID", "CODEX_SESSION_ID")
            if isinstance((value := os.environ.get(key)), str) and value
        }
        deferred_roots = {
            root for root in roots
            if root in current_ids
            or root in inventory.live_thread_ids
            or any(child in inventory.live_thread_ids for child in inventory.descendants(root))
        }
        if not args.include_active:
            roots = [root for root in roots if root not in deferred_roots]

        task_metas: list[dict[str, Any]] = []
        task_failures = 0
        task_cache_hits = 0
        new_task_meta = 0
        pending_roots: list[tuple[str, Path, str]] = []
        for root in roots:
            fingerprint = source_fingerprint(inventory, root)
            path = cache_path(cache_root, "task-meta", root)
            cached = load_valid_task_cache(path, fingerprint)
            if cached is not None:
                task_metas.append(cached)
                task_cache_hits += 1
            elif new_task_meta < max(0, args.max_new_task_meta):
                pending_roots.append((root, path, fingerprint))
                new_task_meta += 1

        for root, path, _ in pending_roots:
            try:
                task = parse_task(inventory, root)
                save_task_cache(path, task)
                task_metas.append(task)
            except (OSError, ValueError, KeyError, TypeError):
                task_failures += 1

        task_metas.sort(key=lambda value: value.get("started_at") or "", reverse=True)
        facets: list[dict[str, Any]] = []
        facet_failures = 0
        facet_cache_hits = 0
        facet_candidates = [task for task in task_metas if task.get("user_turns")]
        uncached_tasks: list[dict[str, Any]] = []
        for task in facet_candidates:
            packet = build_facet_packet(task)
            cache_file = cache_path(cache_root, "facets", task["task_alias"])
            cached_facet = load_cached_facet(packet, cache_file, args.model)
            if cached_facet is not None:
                facets.append(cached_facet)
                facet_cache_hits += 1
            else:
                uncached_tasks.append(task)

        new_limit = min(max(0, args.max_new_facets), max(0, args.facet_sample_size))
        previous_attempts = previous_attempted_facets(runtime_root)
        retry_tasks = sorted(
            (task for task in uncached_tasks if task.get("task_alias") in previous_attempts),
            key=lambda value: str(value.get("task_alias", "")),
        )[:new_limit]
        retry_aliases = {str(task.get("task_alias")) for task in retry_tasks}
        remaining_slots = max(0, new_limit - len(retry_tasks))
        new_tasks = select_facet_sample(
            [task for task in uncached_tasks if str(task.get("task_alias")) not in retry_aliases],
            remaining_slots,
        )
        facet_tasks = retry_tasks + new_tasks
        pending_packets = [
            (
                build_facet_packet(task),
                cache_path(cache_root, "facets", task["task_alias"]),
            )
            for task in facet_tasks
        ]

        if not args.scan_only:
            def execute_facet(item: tuple[dict[str, Any], Path]) -> tuple[dict[str, Any], bool]:
                packet, cache_file = item
                return run_facet(
                    packet, cache_file, ASSET_DIR / "facet.schema.json",
                    isolated_root / "facets" / packet["task_alias"], args.model,
                    ASSET_DIR / "chunk-summary.schema.json",
                )

            with ThreadPoolExecutor(max_workers=max(1, args.facet_concurrency)) as executor:
                futures = [executor.submit(execute_facet, item) for item in pending_packets]
                for future in as_completed(futures):
                    try:
                        facet, hit = future.result()
                    except (ModelCallError, OSError, ValueError):
                        facet_failures += 1
                    else:
                        facets.append(facet)
                        facet_cache_hits += int(hit)

        inventory_metrics = dict(inventory.reconciliation)
        failures = {
            "deferred_live": len(deferred_roots) if not args.include_active else 0,
            "task_meta_failure": task_failures,
            "task_meta_cache_hits": task_cache_hits,
            "task_meta_pending": max(0, len(roots) - len(task_metas) - task_failures),
            "facet_failure": facet_failures,
            "facet_cache_hits": facet_cache_hits,
            "facet_pending": max(0, len(facet_candidates) - len(facets)),
            "facet_candidate_tasks": len(facet_candidates),
            "facet_selected_tasks": len(facets) + facet_failures,
            "facet_unselected_tasks": max(
                0, len(facet_candidates) - len(facets) - facet_failures
            ),
            "facet_attempted_this_run": len(pending_packets),
            "facet_retried_this_run": len(retry_tasks),
        }
        aggregated = aggregate(task_metas, facets, inventory_metrics, failures)
        sections = empty_sections(
            "当前为只读扫描报告，尚未调用模型生成章节。" if args.scan_only
            else "当前 Facet 覆盖不足，尚未形成可靠章节。"
        )
        chapter_stats = {"chapter_success": 0, "chapter_failure": 0, "chapter_cache_hits": 0}
        if not args.scan_only and not args.no_chapters and facets:
            payload = narrative_payload(aggregated)
            sections, chapter_stats = generate_sections(
                payload, set(aggregated.get("evidence_refs", [])), cache_root,
                ASSET_DIR / "section.schema.json", isolated_root / "chapters",
                args.model, args.chapter_concurrency,
            )
            aggregated["coverage"].update(chapter_stats)
        else:
            aggregated["coverage"].update(chapter_stats)

        manifest = {
            "run_id": run_id,
            "generated_at": generated_at.isoformat(),
            "workspace_identity": digest(str(workspace)),
            "codex_home_identity": digest(str(codex_home)),
            "report": report_filename,
            "scan_only": args.scan_only,
            "include_active": args.include_active,
            "parser_version": PARSER_VERSION,
            "coverage": aggregated["coverage"],
        }
        atomic_write_json(run_root / "manifest.json", manifest)
        atomic_write_json(run_root / "report-model.json", {
            "aggregated": aggregated, "sections": sections,
        })
        atomic_write_json(runtime_root / "current.json", {
            "run_id": run_id,
            "manifest": str((run_root / "manifest.json").relative_to(runtime_root)).replace("\\", "/"),
            "report": report_filename,
        })
        render_report(report_path, aggregated, sections, generated_at)
        return {
            "status": "success", "report": str(report_path), "run_id": run_id,
            "coverage": aggregated["coverage"],
        }
    finally:
        lock.unlink(missing_ok=True)


def main() -> int:
    try:
        summary = run()
    except KeyboardInterrupt:
        print("Nest Insights interrupted; completed caches were preserved.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Nest Insights failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if "--json-summary" in sys.argv:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        coverage = summary["coverage"]
        print(f"Report: {summary['report']}")
        print(
            "Coverage: "
            f"JSONL={coverage.get('filesystem_jsonl', 0)}, "
            f"Root={coverage.get('root_threads', 0)}, "
            f"TaskMeta={coverage.get('task_meta_success', 0)}, "
            f"Facet={coverage.get('facet_success', 0)}, "
            f"FacetFailed={coverage.get('facet_failure', 0)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
