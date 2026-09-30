from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any


def _valid_facet(facet: dict[str, Any]) -> bool:
    confidence = facet.get("confidence", 0)
    return isinstance(confidence, (int, float)) and confidence >= 0.35


def aggregate(
    task_metas: list[dict[str, Any]], facets: list[dict[str, Any]],
    inventory: dict[str, int], failures: dict[str, int],
) -> dict[str, Any]:
    tools: Counter[str] = Counter()
    tool_errors: Counter[str] = Counter()
    extensions: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    hour_counts: Counter[str] = Counter()
    response_times: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    task_types: Counter[str] = Counter()
    goals: Counter[str] = Counter()
    friction_categories: Counter[str] = Counter()
    success_categories: Counter[str] = Counter()
    sentiment: Counter[str] = Counter()
    months: Counter[str] = Counter()
    total_tokens = 0
    total_duration = 0
    total_turns = 0
    total_aborted = 0
    total_children = 0
    total_compactions = 0
    total_patch_success = 0
    total_patch_failure = 0
    total_observed_files = 0
    total_user_messages = 0
    active_days: set[str] = set()
    user_events: list[tuple[datetime, str]] = []

    for task in task_metas:
        tools.update(task.get("tool_counts", {}))
        tool_errors.update(task.get("tool_error_counts", {}))
        extensions.update(task.get("extension_counts", {}))
        sources[str(task.get("source") or "unknown")] += 1
        hour_counts.update(task.get("user_hour_counts", {}))
        response_times.update(task.get("response_time_buckets", {}))
        total_tokens += int(task.get("token_usage", 0) or 0)
        total_duration += int(task.get("active_duration_ms", 0) or 0)
        total_turns += int(task.get("turns_started", 0) or 0)
        total_aborted += int(task.get("turns_aborted", 0) or 0)
        total_children += int(task.get("child_threads", 0) or 0)
        total_compactions += int(task.get("compactions", 0) or 0)
        total_patch_success += int(task.get("patch_success", 0) or 0)
        total_patch_failure += int(task.get("patch_failure", 0) or 0)
        total_observed_files += int(task.get("observed_files", 0) or 0)
        total_user_messages += int(task.get("user_messages", 0) or 0)
        active_days.update(str(value) for value in task.get("active_days", []) if value)
        for item in task.get("user_turns", []):
            if not isinstance(item, dict) or not isinstance(item.get("timestamp"), str):
                continue
            try:
                user_events.append((datetime.fromisoformat(item["timestamp"]), str(task.get("task_alias", ""))))
            except ValueError:
                pass
        started_at = task.get("started_at")
        if isinstance(started_at, str) and len(started_at) >= 7:
            months[started_at[:7]] += 1

    valid_facets = sorted(
        (facet for facet in facets if _valid_facet(facet)),
        key=lambda value: str(value.get("task_alias", "")),
    )
    for facet in valid_facets:
        outcomes[str(facet.get("outcome", "unknown"))] += 1
        task_types[str(facet.get("task_type", "other"))] += 1
        goals.update(str(value) for value in facet.get("goal_categories", []) if value)
        for item in facet.get("explicit_user_sentiment", []):
            if isinstance(item, dict) and item.get("level"):
                sentiment[str(item["level"])] += 1
        for item in facet.get("frictions", []):
            if isinstance(item, dict) and item.get("category"):
                friction_categories[str(item["category"])] += 1
        for item in facet.get("successes", []):
            if isinstance(item, dict) and item.get("category"):
                success_categories[str(item["category"])] += 1

    evidence_refs = sorted({
        ref
        for facet in valid_facets
        for field in ("explicit_user_sentiment", "successes", "frictions", "user_corrections")
        for item in facet.get(field, [])
        if isinstance(item, dict)
        for ref in item.get("evidence_refs", [])
        if isinstance(ref, str)
    })
    tasks = []
    facet_by_alias = {facet.get("task_alias"): facet for facet in valid_facets}
    for task in sorted(task_metas, key=lambda value: value.get("started_at") or "", reverse=True):
        facet = facet_by_alias.get(task.get("task_alias"))
        tasks.append({
            "task_alias": task.get("task_alias"),
            "date": (task.get("started_at") or "")[:10],
            "turns": task.get("turns_started", 0),
            "child_threads": task.get("child_threads", 0),
            "tools": sum(task.get("tool_counts", {}).values()),
            "outcome": facet.get("outcome") if facet else "not_analyzed",
            "summary": facet.get("brief_summary") if facet else "尚未生成语义 Facet",
            "confidence": facet.get("confidence") if facet else 0,
        })
    user_events.sort()
    parallel_pairs: set[tuple[str, str]] = set()
    parallel_events = 0
    for index, (timestamp, alias) in enumerate(user_events):
        window_start = timestamp - timedelta(minutes=30)
        recent = user_events[max(0, index - 80):index]
        recent_aliases = {other for other_time, other in recent if other_time >= window_start and other != alias}
        for other in recent_aliases:
            parallel_pairs.add(tuple(sorted((alias, other))))
            parallel_events += 1
    date_values = [task.get("started_at") for task in task_metas if isinstance(task.get("started_at"), str)]
    return {
        "coverage": {
            **inventory,
            "task_meta_success": len(task_metas),
            "effective_tasks": sum(1 for task in task_metas if task.get("user_turns")),
            "facet_success": len(valid_facets),
            **failures,
        },
        "metrics": {
            "turns": total_turns,
            "aborted_turns": total_aborted,
            "child_threads_in_parsed_tasks": total_children,
            "token_usage_observed": total_tokens,
            "active_duration_ms": total_duration,
            "compactions": total_compactions,
            "patch_success": total_patch_success,
            "patch_failure": total_patch_failure,
            "observed_files": total_observed_files,
            "user_messages": total_user_messages,
            "active_days": len(active_days),
            "date_start": min(date_values)[:10] if date_values else "",
            "date_end": max(date_values)[:10] if date_values else "",
            "parallel_task_pairs": len(parallel_pairs),
            "parallel_events": parallel_events,
        },
        "distributions": {
            "tools": dict(tools.most_common(12)),
            "tool_errors": dict(tool_errors.most_common(12)),
            "extensions": dict(extensions.most_common(12)),
            "sources": dict(sources.most_common()),
            "hours": dict(sorted(hour_counts.items())),
            "response_times": dict(response_times),
            "outcomes": dict(outcomes.most_common()),
            "task_types": dict(task_types.most_common()),
            "goals": dict(goals.most_common(12)),
            "frictions": dict(friction_categories.most_common(12)),
            "successes": dict(success_categories.most_common(12)),
            "sentiment": dict(sentiment.most_common()),
            "months": dict(sorted(months.items())),
        },
        "facets": valid_facets,
        "tasks": tasks,
        "evidence_refs": evidence_refs,
    }


def narrative_payload(aggregated: dict[str, Any]) -> dict[str, Any]:
    facets = []
    for facet in aggregated.get("facets", []):
        facets.append({
            key: facet.get(key) for key in (
                "task_alias", "underlying_goal", "goal_categories", "task_type", "outcome",
                "explicit_user_sentiment", "successes", "frictions", "user_corrections",
                "interaction_pattern", "brief_summary", "confidence",
            )
        })
    coverage = aggregated.get("coverage", {})
    stable_coverage = {
        key: coverage.get(key, 0)
        for key in (
            "task_meta_success", "effective_tasks", "facet_success",
            "task_meta_failure", "facet_failure",
        )
    }
    return {
        # Chapter semantics depend on the analyzed sample, not on volatile scan bookkeeping
        # such as current JSONL bytes, live threads, pending roots, or cache-hit counters.
        # Full reconciliation remains available in the report coverage section and manifest.
        "coverage": stable_coverage,
        "metrics": aggregated.get("metrics", {}),
        "distributions": aggregated.get("distributions", {}),
        "facets": facets,
    }
