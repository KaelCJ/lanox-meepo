from __future__ import annotations

import json
import os
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ThreadRecord:
    thread_id: str
    rollout_path: Path
    created_at: int
    updated_at: int
    source: str
    archived: bool
    has_user_event: bool
    cli_version: str
    model: str


@dataclass
class Inventory:
    codex_home: Path
    jsonl_paths: list[Path]
    state_path: Path | None
    threads: dict[str, ThreadRecord]
    parent_of: dict[str, str]
    children_of: dict[str, list[str]]
    path_to_thread: dict[str, str]
    live_thread_ids: set[str]
    reconciliation: dict[str, int]

    def root_id(self, thread_id: str) -> str:
        current = thread_id
        visited: set[str] = set()
        while current in self.parent_of and current not in visited:
            visited.add(current)
            current = self.parent_of[current]
        return current

    def descendants(self, root_id: str) -> list[str]:
        result: list[str] = []
        stack = list(reversed(self.children_of.get(root_id, [])))
        while stack:
            item = stack.pop()
            result.append(item)
            stack.extend(reversed(self.children_of.get(item, [])))
        return result


def locate_codex_home(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    configured = os.environ.get("CODEX_HOME")
    return (Path(configured) if configured else Path.home() / ".codex").resolve()


def discover_jsonl(codex_home: Path) -> list[Path]:
    paths: list[Path] = []
    for directory in ("sessions", "archived_sessions"):
        root = codex_home / directory
        if root.is_dir():
            paths.extend(root.rglob("*.jsonl"))
    return sorted(paths, key=lambda path: (path.stat().st_mtime_ns, str(path)), reverse=True)


def newest_state(codex_home: Path) -> Path | None:
    paths = list(codex_home.glob("state_*.sqlite"))
    return max(paths, key=lambda path: path.stat().st_mtime_ns) if paths else None


def _has_columns(connection: sqlite3.Connection, table: str, required: set[str]) -> bool:
    columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
    return required.issubset(columns)


def read_state(state_path: Path | None) -> tuple[
    dict[str, ThreadRecord], dict[str, str], dict[str, list[str]], dict[str, str]
]:
    if state_path is None:
        return {}, {}, {}, {}
    uri = f"file:{state_path.as_posix()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    try:
        required = {
            "id", "rollout_path", "created_at", "updated_at", "source", "archived",
            "has_user_event", "cli_version", "model",
        }
        if not _has_columns(connection, "threads", required):
            return {}, {}, {}, {}
        threads: dict[str, ThreadRecord] = {}
        path_to_thread: dict[str, str] = {}
        rows = connection.execute(
            "SELECT id, rollout_path, created_at, updated_at, source, archived, "
            "has_user_event, cli_version, model FROM threads"
        )
        for row in rows:
            if not isinstance(row[0], str) or not isinstance(row[1], str):
                continue
            path = Path(row[1]).expanduser().resolve()
            record = ThreadRecord(
                thread_id=row[0], rollout_path=path, created_at=int(row[2] or 0),
                updated_at=int(row[3] or 0), source=str(row[4] or "unknown"),
                archived=bool(row[5]), has_user_event=bool(row[6]),
                cli_version=str(row[7] or "unknown"), model=str(row[8] or "unknown"),
            )
            threads[record.thread_id] = record
            path_to_thread[str(path).casefold()] = record.thread_id

        parent_of: dict[str, str] = {}
        children_of: dict[str, list[str]] = defaultdict(list)
        if _has_columns(connection, "thread_spawn_edges", {"parent_thread_id", "child_thread_id"}):
            for parent_id, child_id in connection.execute(
                "SELECT parent_thread_id, child_thread_id FROM thread_spawn_edges"
            ):
                if isinstance(parent_id, str) and isinstance(child_id, str):
                    parent_of[child_id] = parent_id
                    children_of[parent_id].append(child_id)
        for children in children_of.values():
            children.sort()
        return threads, parent_of, dict(children_of), path_to_thread
    finally:
        connection.close()


def read_session_id(path: Path) -> str | None:
    try:
        with path.open("rb") as stream:
            for _ in range(4):
                raw = stream.readline()
                if not raw:
                    break
                record = json.loads(raw)
                if isinstance(record, dict) and record.get("type") == "session_meta":
                    payload = record.get("payload")
                    if isinstance(payload, dict):
                        value = payload.get("id") or payload.get("session_id")
                        if isinstance(value, str):
                            return value
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return None


def read_live_threads(codex_home: Path) -> set[str]:
    root = codex_home / "thread-writer-locks"
    if not root.is_dir():
        return set()
    return {
        path.stem for path in root.glob("*.lock")
        if path.name != ".coordination.lock"
    }


def build_inventory(codex_home: Path) -> Inventory:
    jsonl_paths = discover_jsonl(codex_home)
    state_path = newest_state(codex_home)
    threads, parent_of, children_of, path_to_thread = read_state(state_path)
    filesystem = {str(path.resolve()).casefold() for path in jsonl_paths}
    database = set(path_to_thread)
    return Inventory(
        codex_home=codex_home,
        jsonl_paths=jsonl_paths,
        state_path=state_path,
        threads=threads,
        parent_of=parent_of,
        children_of=children_of,
        path_to_thread=path_to_thread,
        live_thread_ids=read_live_threads(codex_home),
        reconciliation={
            "filesystem_jsonl": len(filesystem),
            "sqlite_threads": len(threads),
            "matched_rollouts": len(filesystem & database),
            "filesystem_only": len(filesystem - database),
            "sqlite_only": len(database - filesystem),
            "root_threads": len(set(threads) - set(parent_of)),
            "child_threads": len(set(threads) & set(parent_of)),
            "spawn_edges": len(parent_of),
            "live_threads": len(read_live_threads(codex_home)),
            "total_bytes": sum(path.stat().st_size for path in jsonl_paths),
        },
    )


def candidate_roots(inventory: Inventory) -> list[str]:
    if inventory.threads:
        topology_roots = [
            thread_id for thread_id in inventory.threads
            if thread_id not in inventory.parent_of
        ]
        # Some desktop schema versions keep has_user_event at zero for every row.
        # Treat it as an optimization hint only when the column has positive data;
        # canonical user turns from JSONL remain the validity authority.
        has_positive_hint = any(record.has_user_event for record in inventory.threads.values())
        roots = (
            [thread_id for thread_id in topology_roots if inventory.threads[thread_id].has_user_event]
            if has_positive_hint else topology_roots
        )
        return sorted(
            roots, key=lambda item: inventory.threads[item].updated_at, reverse=True
        )

    roots: list[tuple[int, str]] = []
    for path in inventory.jsonl_paths:
        thread_id = read_session_id(path)
        if thread_id:
            roots.append((path.stat().st_mtime_ns, thread_id))
            inventory.path_to_thread[str(path.resolve()).casefold()] = thread_id
            inventory.threads[thread_id] = ThreadRecord(
                thread_id=thread_id, rollout_path=path, created_at=0,
                updated_at=int(path.stat().st_mtime), source="jsonl-fallback",
                archived="archived_sessions" in path.parts, has_user_event=True,
                cli_version="unknown", model="unknown",
            )
    return [item[1] for item in sorted(roots, reverse=True)]
