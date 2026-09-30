from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import PARSER_VERSION, digest
from .discover import Inventory
from .redact import normalize_tool, redact_text, safe_extension


KNOWN_PAYLOAD_TYPES = {
    "task_started", "task_complete", "turn_aborted", "user_message", "agent_message",
    "token_count", "function_call", "function_call_output", "custom_tool_call",
    "custom_tool_call_output", "local_shell_call", "patch_apply_end", "mcp_tool_call_end",
    "sub_agent_activity", "context_compacted", "compacted", "thread_rolled_back",
    "thread_settings_applied", "message", "reasoning", "web_search_call", "ghost_snapshot",
}


def task_alias(root_id: str) -> str:
    return f"T-{digest(root_id)[:8].upper()}"


def member_ids(inventory: Inventory, root_id: str) -> list[str]:
    return [root_id, *inventory.descendants(root_id)]


def member_paths(inventory: Inventory, root_id: str) -> list[tuple[str, Path]]:
    result: list[tuple[str, Path]] = []
    for thread_id in member_ids(inventory, root_id):
        record = inventory.threads.get(thread_id)
        if record and record.rollout_path.is_file():
            result.append((thread_id, record.rollout_path))
    return result


def source_fingerprint(inventory: Inventory, root_id: str) -> str:
    parts: list[dict[str, Any]] = []
    for thread_id, path in member_paths(inventory, root_id):
        stat = path.stat()
        try:
            identity = str(path.relative_to(inventory.codex_home)).replace("\\", "/")
        except ValueError:
            identity = digest(str(path.resolve()))
        parts.append({
            "thread": digest(thread_id), "identity": identity,
            "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
        })
    return digest({"parser": PARSER_VERSION, "members": parts})


def _response_text(payload: dict[str, Any]) -> str:
    content = payload.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    chunks: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") in {"input_text", "output_text", "text"}:
            value = block.get("text")
            if isinstance(value, str):
                chunks.append(value)
    return "\n".join(chunks)


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _safe_int(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _response_bucket(seconds: float) -> str:
    if seconds < 30:
        return "<30s"
    if seconds < 120:
        return "30s–2m"
    if seconds < 600:
        return "2–10m"
    if seconds < 3600:
        return "10–60m"
    if seconds < 14400:
        return "1–4h"
    return ">4h"


def parse_task(inventory: Inventory, root_id: str) -> dict[str, Any]:
    alias = task_alias(root_id)
    members = member_paths(inventory, root_id)
    root_event_users: list[dict[str, str]] = []
    root_response_users: list[dict[str, str]] = []
    root_finals: list[dict[str, str]] = []
    child_finals: list[dict[str, str]] = []
    tools: Counter[str] = Counter()
    tool_errors: Counter[str] = Counter()
    extensions: Counter[str] = Counter()
    user_hour_counts: Counter[str] = Counter()
    response_time_buckets: Counter[str] = Counter()
    unknown_events: Counter[str] = Counter()
    quality_flags: list[str] = []
    turn_status: dict[str, str] = {}
    turn_tokens: dict[str, int] = {}
    turn_duration: dict[str, int] = {}
    call_ids: set[str] = set()
    call_tools: dict[str, str] = {}
    patch_success = 0
    patch_failure = 0
    observed_files = 0
    compactions = 0
    rollbacks = 0
    parse_errors = 0
    timestamps: list[datetime] = []
    user_dates: set[str] = set()
    last_root_answer_at: datetime | None = None

    for thread_id, path in members:
        is_root = thread_id == root_id
        current_turn = ""
        last_token_for_turn = 0
        try:
            stream = path.open("rb")
        except OSError:
            quality_flags.append("unreadable-member")
            continue
        with stream:
            for raw_line in stream:
                try:
                    record = json.loads(raw_line)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    parse_errors += 1
                    continue
                if not isinstance(record, dict):
                    continue
                parsed_ts = _timestamp(record.get("timestamp"))
                if parsed_ts:
                    timestamps.append(parsed_ts)
                payload = record.get("payload")
                if not isinstance(payload, dict):
                    continue
                payload_type = payload.get("type")
                if not isinstance(payload_type, str):
                    continue
                if payload_type not in KNOWN_PAYLOAD_TYPES:
                    unknown_events[payload_type] += 1

                if payload_type == "task_started":
                    turn_id = payload.get("turn_id")
                    current_turn = turn_id if isinstance(turn_id, str) else f"implicit-{len(turn_status) + 1}"
                    turn_status[current_turn] = "started"
                    last_token_for_turn = 0
                elif payload_type == "user_message" and is_root:
                    message = redact_text(payload.get("message"), 1800)
                    if message:
                        item = {"turn_id": current_turn, "text": message}
                        if parsed_ts:
                            item["timestamp"] = parsed_ts.isoformat()
                            user_hour_counts[f"{parsed_ts.hour:02d}"] += 1
                            user_dates.add(parsed_ts.date().isoformat())
                            if last_root_answer_at and parsed_ts >= last_root_answer_at:
                                response_time_buckets[_response_bucket((parsed_ts - last_root_answer_at).total_seconds())] += 1
                        root_event_users.append(item)
                elif payload_type == "message" and payload.get("role") == "user" and is_root:
                    message = redact_text(_response_text(payload), 1800)
                    if message:
                        item = {"turn_id": current_turn, "text": message}
                        if parsed_ts:
                            item["timestamp"] = parsed_ts.isoformat()
                        root_response_users.append(item)
                elif payload_type == "task_complete":
                    turn_id = payload.get("turn_id")
                    turn_key = turn_id if isinstance(turn_id, str) else current_turn
                    turn_status[turn_key] = "completed"
                    duration = _safe_int(payload.get("duration_ms"))
                    if duration:
                        turn_duration[turn_key] = duration
                    if last_token_for_turn:
                        turn_tokens[turn_key] = last_token_for_turn
                    message = redact_text(payload.get("last_agent_message"), 1400)
                    if message:
                        target = root_finals if is_root else child_finals
                        item = {"turn_id": turn_key, "text": message}
                        if parsed_ts:
                            item["timestamp"] = parsed_ts.isoformat()
                        target.append(item)
                        if is_root and parsed_ts:
                            last_root_answer_at = parsed_ts
                    current_turn = ""
                    last_token_for_turn = 0
                elif payload_type == "turn_aborted":
                    turn_id = payload.get("turn_id")
                    turn_key = turn_id if isinstance(turn_id, str) else current_turn
                    turn_status[turn_key] = "aborted"
                    if last_token_for_turn:
                        turn_tokens[turn_key] = last_token_for_turn
                    current_turn = ""
                    last_token_for_turn = 0
                elif payload_type == "token_count":
                    info = payload.get("info")
                    usage = info.get("last_token_usage") if isinstance(info, dict) else None
                    if isinstance(usage, dict):
                        last_token_for_turn = _safe_int(usage.get("total_tokens"))
                elif payload_type in {"function_call", "custom_tool_call", "local_shell_call"}:
                    call_id = payload.get("call_id") or payload.get("id")
                    call_key = call_id if isinstance(call_id, str) else f"anonymous-{len(call_ids)}"
                    if call_key not in call_ids:
                        call_ids.add(call_key)
                        tool_name = normalize_tool(payload.get("name"))
                        tools[tool_name] += 1
                        call_tools[call_key] = tool_name
                elif payload_type in {"function_call_output", "custom_tool_call_output"}:
                    call_id = payload.get("call_id") or payload.get("id")
                    call_key = call_id if isinstance(call_id, str) else ""
                    if payload.get("success") is False or payload.get("is_error") is True:
                        tool_errors[call_tools.get(call_key, "unknown")] += 1
                elif payload_type == "mcp_tool_call_end":
                    if payload.get("success") is False or payload.get("is_error") is True:
                        tool_errors[normalize_tool(payload.get("name"))] += 1
                elif payload_type == "patch_apply_end":
                    success = payload.get("success")
                    if success is True:
                        patch_success += 1
                    elif success is False:
                        patch_failure += 1
                    changes = payload.get("changes")
                    if isinstance(changes, dict):
                        observed_files += len(changes)
                        for value in changes:
                            extension = safe_extension(value)
                            if extension:
                                extensions[extension] += 1
                elif payload_type in {"context_compacted", "compacted"}:
                    compactions += 1
                elif payload_type == "thread_rolled_back":
                    rollbacks += max(1, _safe_int(payload.get("num_turns")))

    user_messages = root_event_users or root_response_users
    if not root_event_users and root_response_users:
        quality_flags.append("user-message-fallback")
    if parse_errors:
        quality_flags.append("jsonl-parse-errors")
    if unknown_events:
        quality_flags.append("unknown-events")
    if not user_messages:
        quality_flags.append("no-canonical-user-turn")

    evidence_users = [
        {"evidence_id": f"{alias}/U{index:02d}", **item}
        for index, item in enumerate(user_messages, start=1)
    ]
    evidence_finals = [
        {"evidence_id": f"{alias}/A{index:02d}", **item}
        for index, item in enumerate(root_finals, start=1)
    ]
    evidence_children = [
        {"evidence_id": f"{alias}/C{index:02d}", **item}
        for index, item in enumerate(child_finals[:12], start=1)
    ]
    record = inventory.threads.get(root_id)
    return {
        "schema_version": PARSER_VERSION,
        "source_fingerprint": source_fingerprint(inventory, root_id),
        "task_alias": alias,
        "root_thread_id": root_id,
        "started_at": min(timestamps).isoformat() if timestamps else None,
        "updated_at": max(timestamps).isoformat() if timestamps else None,
        "source": record.source if record else "unknown",
        "cli_version": record.cli_version if record else "unknown",
        "member_threads": len(members),
        "child_threads": max(0, len(members) - 1),
        "turns_started": sum(1 for value in turn_status.values() if value in {"started", "completed", "aborted"}),
        "turns_completed": sum(1 for value in turn_status.values() if value == "completed"),
        "turns_aborted": sum(1 for value in turn_status.values() if value == "aborted"),
        "active_duration_ms": sum(turn_duration.values()),
        "token_usage": sum(turn_tokens.values()),
        "tool_counts": dict(tools.most_common()),
        "tool_error_counts": dict(tool_errors.most_common()),
        "patch_success": patch_success,
        "patch_failure": patch_failure,
        "observed_files": observed_files,
        "extension_counts": dict(extensions.most_common()),
        "compactions": compactions,
        "rollbacks": rollbacks,
        "user_messages": len(evidence_users),
        "active_days": sorted(user_dates),
        "user_hour_counts": dict(sorted(user_hour_counts.items())),
        "response_time_buckets": dict(response_time_buckets),
        "parse_errors": parse_errors,
        "unknown_events": dict(unknown_events.most_common()),
        "user_turns": evidence_users,
        "final_answers": evidence_finals,
        "child_results": evidence_children,
        "quality_flags": sorted(set(quality_flags)),
    }


def build_facet_packet(task: dict[str, Any], chunk_chars: int = 22000) -> dict[str, Any]:
    timeline: list[dict[str, Any]] = []
    for role, field in (("user", "user_turns"), ("assistant", "final_answers"), ("child", "child_results")):
        for item in task.get(field, []):
            if not isinstance(item, dict) or not item.get("evidence_id"):
                continue
            timeline.append({
                "role": role,
                "evidence_id": item.get("evidence_id"),
                "timestamp": item.get("timestamp"),
                "text": item.get("text", ""),
            })
    timeline.sort(key=lambda item: (str(item.get("timestamp") or ""), str(item.get("evidence_id") or "")))
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    for item in timeline:
        item_chars = len(json.dumps(item, ensure_ascii=False))
        if current and current_chars + item_chars > chunk_chars:
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(item)
        current_chars += item_chars
    if current:
        chunks.append(current)
    return {
        "task_alias": task["task_alias"],
        "started_date": (task.get("started_at") or "")[:10],
        "updated_date": (task.get("updated_at") or "")[:10],
        "metrics": {
            key: task.get(key) for key in (
                "member_threads", "child_threads", "turns_started", "turns_completed",
                "turns_aborted", "active_duration_ms", "token_usage", "tool_counts",
                "patch_success", "patch_failure", "observed_files", "extension_counts",
                "compactions", "rollbacks", "user_messages", "active_days",
                "user_hour_counts", "response_time_buckets", "tool_error_counts",
            )
        },
        "transcript_chunks": [
            {"index": index, "entries": entries}
            for index, entries in enumerate(chunks, start=1)
        ],
        "quality_flags": list(task.get("quality_flags", [])),
    }
