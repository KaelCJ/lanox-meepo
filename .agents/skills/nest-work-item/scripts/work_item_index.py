#!/usr/bin/env python3
"""Query and maintain the authoritative JSON work-item indexes."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


WORK_ITEM_ROOT_RELATIVE = Path(".workspace-assistant/10-工作项")
CURRENT_FILE = "current.json"
ARCHIVE_FILE = "archive.json"
SCHEMA_FILE = "index.schema.json"
ARCHIVE_DIRECTORY = "归档"
SCHEMA_VERSION = 2
WORK_ITEM_DIRECTORY = re.compile(r"^\d{4}-\d{2}-\d{2}_.+_.+$")
RFC3339_SECONDS = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$"
)
PRIORITIES = ("P0", "P1", "P2", "P3", "未设置")
PRIORITY_RANK = {value: index for index, value in enumerate(PRIORITIES)}
CURRENT_FIELDS = {
    "id",
    "title",
    "type",
    "product",
    "priority",
    "createdAt",
    "updatedAt",
    "entry",
}
ARCHIVE_FIELDS = CURRENT_FIELDS | {"archivedAt"}
ROOT_FIELDS = {"schemaVersion", "items"}
CURRENT_SUMMARY_HEADING = "## 当前简介"
UUID19_JAR = Path(__file__).resolve().parent.parent / "assets" / "nest-uuid19.jar"


def emit(value: Dict[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    sys.stdout.write(payload + "\n")


def now_seconds() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def discover_root(explicit: Optional[Path], allow_missing: bool = False) -> Path:
    if explicit is not None:
        root = explicit.expanduser().resolve()
        if root.exists() and not root.is_dir():
            raise ValueError(f"work-item root is not a directory: {root}")
        if not root.exists() and not allow_missing:
            raise FileNotFoundError(root)
        return root

    starts = [Path.cwd(), Path(__file__).resolve()]
    for start in starts:
        directory = start if start.is_dir() else start.parent
        for parent in (directory, *directory.parents):
            candidate = parent / WORK_ITEM_ROOT_RELATIVE
            if candidate.is_dir():
                return candidate.resolve()
    raise FileNotFoundError(WORK_ITEM_ROOT_RELATIVE)


def index_paths(root: Path) -> Tuple[Path, Path, Path]:
    return root / CURRENT_FILE, root / ARCHIVE_FILE, root / SCHEMA_FILE


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as error:
        raise ValueError(
            f"invalid JSON in {path}: line {error.lineno}, column {error.colno}"
        ) from error
    if not isinstance(value, dict):
        raise ValueError(f"index root must be an object: {path}")
    return value


def require_exact_fields(
    value: Dict[str, Any], expected: Iterable[str], context: str
) -> None:
    expected_set = set(expected)
    actual = set(value)
    missing = sorted(expected_set - actual)
    extra = sorted(actual - expected_set)
    if missing:
        raise ValueError(f"{context} missing fields: {', '.join(missing)}")
    if extra:
        raise ValueError(f"{context} has unsupported fields: {', '.join(extra)}")


def parse_timestamp(value: Any, field: str, item_id: str) -> datetime:
    if not isinstance(value, str) or RFC3339_SECONDS.fullmatch(value) is None:
        raise ValueError(
            f"{item_id} {field} must be RFC 3339 with timezone and second precision"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        result = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(f"{item_id} {field} is not a valid timestamp") from error
    if result.tzinfo is None:
        raise ValueError(f"{item_id} {field} must include a timezone")
    return result


def is_reparse_point(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(attributes & reparse)


def require_plain_existing_path(root: Path, path: Path, context: str) -> None:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(f"{context} escapes work-item root") from error

    current = resolved_root
    relative = path.resolve(strict=False).relative_to(resolved_root)
    for part in relative.parts:
        current = current / part
        if current.exists() and is_reparse_point(current):
            raise ValueError(f"{context} contains a reparse point: {current}")


def validate_entry(
    root: Path,
    item: Dict[str, Any],
    archived: bool,
) -> None:
    item_id = item["id"]
    entry = item["entry"]
    if entry is None:
        if not archived:
            raise ValueError(f"{item_id} current entry must not be null")
        return
    if not isinstance(entry, str) or not entry.strip():
        raise ValueError(f"{item_id} entry must be a non-empty string or null")
    if "\\" in entry:
        raise ValueError(f"{item_id} entry must use forward slashes")

    relative = PurePosixPath(entry)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError(f"{item_id} entry must be a normalized relative path")
    if relative.name != "README.md":
        raise ValueError(f"{item_id} entry must target README.md")

    expected_parent = root / ARCHIVE_DIRECTORY if archived else root
    item_directory = root.joinpath(*relative.parts).parent
    if item_directory.parent.resolve(strict=False) != expected_parent.resolve(strict=False):
        lifecycle = ARCHIVE_FILE if archived else CURRENT_FILE
        raise ValueError(f"{item_id} entry does not match {lifecycle} membership")
    if re.fullmatch(
        rf"\d{{4}}-\d{{2}}-\d{{2}}_{re.escape(item_id)}_.+", item_directory.name
    ) is None:
        raise ValueError(f"{item_id} entry directory does not match its ID")

    readme = root.joinpath(*relative.parts)
    require_plain_existing_path(root, readme, f"{item_id} entry")
    if not readme.is_file():
        raise ValueError(f"{item_id} README is missing: {readme}")


def validate_item(root: Path, item: Any, archived: bool) -> None:
    if not isinstance(item, dict):
        raise ValueError("work-item record must be an object")
    expected = ARCHIVE_FIELDS if archived else CURRENT_FIELDS
    item_id = str(item.get("id", "<unknown>"))
    require_exact_fields(item, expected, f"work item {item_id}")

    item_id = item["id"]
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("work-item ID must be a non-empty string")
    if not isinstance(item["title"], str) or not item["title"].strip():
        raise ValueError(f"{item_id} title must not be empty")
    for field in ("type", "product"):
        value = item[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{item_id} {field} must be a non-negative integer")
    if item["priority"] not in PRIORITIES:
        raise ValueError(f"{item_id} priority is invalid: {item['priority']}")

    created = parse_timestamp(item["createdAt"], "createdAt", item_id)
    updated = parse_timestamp(item["updatedAt"], "updatedAt", item_id)
    if updated < created:
        raise ValueError(f"{item_id} updatedAt must not precede createdAt")
    if archived:
        archived_at = parse_timestamp(item["archivedAt"], "archivedAt", item_id)
        if archived_at < created:
            raise ValueError(f"{item_id} archivedAt must not precede createdAt")

    validate_entry(root, item, archived)


def validate_indexes(
    root: Path,
    current: Dict[str, Any],
    archive: Dict[str, Any],
) -> None:
    ids = set()
    entries = set()
    for name, index, archived in (
        (CURRENT_FILE, current, False),
        (ARCHIVE_FILE, archive, True),
    ):
        require_exact_fields(index, ROOT_FIELDS, name)
        if index["schemaVersion"] != SCHEMA_VERSION:
            raise ValueError(f"{name} schemaVersion must be {SCHEMA_VERSION}")
        if not isinstance(index["items"], list):
            raise ValueError(f"{name} items must be an array")
        for item in index["items"]:
            validate_item(root, item, archived)
            key = item["id"].casefold()
            if key in ids:
                raise ValueError(f"duplicate work-item ID: {item['id']}")
            ids.add(key)
            if item["entry"] is not None:
                entry = root.joinpath(*PurePosixPath(item["entry"]).parts).resolve()
                if entry in entries:
                    raise ValueError(f"duplicate work-item entry: {item['entry']}")
                entries.add(entry)

    current_path, archive_path, schema_path = index_paths(root)
    for path in (current_path, archive_path, schema_path):
        require_plain_existing_path(root, path, path.name)
    if schema_path.is_file():
        read_json(schema_path)
    else:
        raise FileNotFoundError(schema_path)


def load_indexes(root: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    current_path, archive_path, _ = index_paths(root)
    if not current_path.is_file() or not archive_path.is_file():
        missing = [
            str(path)
            for path in (current_path, archive_path)
            if not path.is_file()
        ]
        raise FileNotFoundError(", ".join(missing))
    current = read_json(current_path)
    archive = read_json(archive_path)
    validate_indexes(root, current, archive)
    return current, archive


def serialize(value: Dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def stage_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    return temporary


def restore_bytes(path: Path, content: Optional[bytes]) -> None:
    if content is None:
        if path.exists():
            path.unlink()
        return
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.restore")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def replace_many(values: Sequence[Tuple[Path, str]]) -> None:
    originals = {path: path.read_bytes() if path.exists() else None for path, _ in values}
    staged: Dict[Path, Path] = {}
    replaced: List[Path] = []
    try:
        for path, text in values:
            staged[path] = stage_text(path, text)
        for path, _ in values:
            os.replace(staged[path], path)
            replaced.append(path)
    except OSError as error:
        rollback_errors: List[str] = []
        for path in reversed(replaced):
            try:
                restore_bytes(path, originals[path])
            except OSError as rollback_error:
                rollback_errors.append(f"{path}: {rollback_error}")
        detail = (
            f"; rollback failed: {'; '.join(rollback_errors)}"
            if rollback_errors
            else ""
        )
        raise OSError(f"atomic index replacement failed: {error}{detail}") from error
    finally:
        for temporary in staged.values():
            if temporary.exists():
                temporary.unlink()


def write_indexes(root: Path, current: Dict[str, Any], archive: Dict[str, Any]) -> None:
    validate_indexes(root, current, archive)
    current_path, archive_path, _ = index_paths(root)
    replace_many(
        [
            (path, serialize(index))
            for path, index in (
                (current_path, current),
                (archive_path, archive),
            )
            if read_json(path) != index
        ]
    )


def schema_asset() -> Path:
    path = Path(__file__).resolve().parent.parent / "assets" / SCHEMA_FILE
    if not path.is_file():
        raise FileNotFoundError(path)
    read_json(path)
    return path


def generated_work_item_id(
    current: Dict[str, Any], archive: Dict[str, Any]
) -> str:
    java = shutil.which("java")
    if java is None:
        raise RuntimeError("Java is required to generate Nest UUID19 work-item IDs")
    if not UUID19_JAR.is_file():
        raise FileNotFoundError(UUID19_JAR)

    used = {item["id"].casefold() for _, item in scoped_items(current, archive, "all")}
    for _ in range(10):
        result = subprocess.run(
            [java, "-jar", str(UUID19_JAR)],
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            timeout=10,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or "unknown UUID19 generator error"
            raise RuntimeError(f"Nest UUID19 generator failed: {detail}")
        token = result.stdout.strip()
        if re.fullmatch(r"R[0-9a-zA-Z]{19}", token) is None:
            raise RuntimeError("Nest UUID19 generator returned an invalid work-item ID")
        if token.casefold() not in used:
            return token
    raise RuntimeError("could not allocate a unique Nest UUID19 work-item ID")


def existing_work_item_directories(root: Path) -> List[Path]:
    result: List[Path] = []
    for parent in (root, root / ARCHIVE_DIRECTORY):
        if not parent.is_dir():
            continue
        result.extend(
            child
            for child in parent.iterdir()
            if child.is_dir() and WORK_ITEM_DIRECTORY.fullmatch(child.name)
        )
    return result


def initialize(root: Path) -> Dict[str, Any]:
    current_path, archive_path, schema_path = index_paths(root)
    blockers = [
        path
        for path in (
            current_path,
            archive_path,
            schema_path,
            root / "README.md",
        )
        if path.exists()
    ]
    blockers.extend(existing_work_item_directories(root))
    if blockers:
        raise ValueError(
            "work-item indexes can only be initialized in a fresh space; found: "
            + ", ".join(str(path) for path in blockers)
        )

    root.mkdir(parents=True, exist_ok=True)
    current = {"schemaVersion": SCHEMA_VERSION, "items": []}
    archive = {"schemaVersion": SCHEMA_VERSION, "items": []}
    schema_text = schema_asset().read_text(encoding="utf-8")
    try:
        replace_many(
            (
                (current_path, serialize(current)),
                (archive_path, serialize(archive)),
                (schema_path, schema_text),
            )
        )
        validate_indexes(root, current, archive)
    except (OSError, ValueError):
        for path in (current_path, archive_path, schema_path):
            if path.exists():
                path.unlink()
        raise
    return {
        "initialized": True,
        "currentIndex": str(current_path),
        "archiveIndex": str(archive_path),
        "schema": str(schema_path),
        "idStrategy": "uuid19",
    }


def read_summary(root: Path, item: Dict[str, Any]) -> str:
    entry = item["entry"]
    if entry is None:
        return ""
    readme = root.joinpath(*PurePosixPath(entry).parts)
    lines = readme.read_text(encoding="utf-8-sig").splitlines()
    starts = [
        position
        for position, line in enumerate(lines)
        if line.strip() == CURRENT_SUMMARY_HEADING
    ]
    if len(starts) > 1:
        raise ValueError(f"duplicate {CURRENT_SUMMARY_HEADING}: {item['id']}")
    if starts:
        content: List[str] = []
        for line in lines[starts[0] + 1 :]:
            if line.startswith("## "):
                break
            content.append(line)
        value = "\n".join(content).strip()
        if not value:
            raise ValueError(f"empty {CURRENT_SUMMARY_HEADING}: {item['id']}")
        return value

    introduction: List[str] = []
    title_found = False
    for line in lines:
        if not title_found:
            title_found = line.startswith("# ")
            continue
        if line.startswith("## "):
            break
        introduction.append(line)
    return "\n".join(introduction).strip()


def list_current(root: Path, current: Dict[str, Any], limit: int) -> Dict[str, Any]:
    if limit < 0 or limit > 100:
        raise ValueError("limit must be between 0 and 100")
    ordered = sorted(
        enumerate(current["items"]),
        key=lambda pair: (PRIORITY_RANK[pair[1]["priority"]], pair[0]),
    )
    items = [item for _, item in ordered]
    selected = items if limit == 0 else items[:limit]
    result = [{**item, "current": read_summary(root, item)} for item in selected]
    return {
        "items": result,
        "itemCount": len(items),
        "truncated": limit > 0 and len(items) > limit,
    }


def find_matches(
    root: Path, items: Iterable[Dict[str, Any]], query: str, limit: int
) -> Tuple[List[Dict[str, Any]], int]:
    needle = query.strip().casefold()
    if not needle:
        raise ValueError("query must not be empty")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    matches = [
        item
        for item in items
        if needle
        in " ".join(
            str(item.get(field, ""))
            for field in ("id", "title", "type", "product", "priority", "entry")
        ).casefold()
        or (
            item["entry"] is not None
            and needle
            in root.joinpath(*PurePosixPath(item["entry"]).parts)
            .read_text(encoding="utf-8-sig")
            .casefold()
        )
    ]
    return matches[:limit], len(matches)


def scoped_items(
    current: Dict[str, Any], archive: Dict[str, Any], scope: str
) -> List[Tuple[str, Dict[str, Any]]]:
    result: List[Tuple[str, Dict[str, Any]]] = []
    if scope in {"current", "all"}:
        result.extend((CURRENT_FILE, item) for item in current["items"])
    if scope in {"archive", "all"}:
        result.extend((ARCHIVE_FILE, item) for item in archive["items"])
    return result


def resolve_item(
    current: Dict[str, Any], archive: Dict[str, Any], item_id: str
) -> Dict[str, Any]:
    for source, item in scoped_items(current, archive, "all"):
        if item["id"] == item_id:
            return {"found": True, "source": source, "item": item}
    return {"found": False, "source": None, "item": None}


def create_item(
    root: Path,
    current: Dict[str, Any],
    archive: Dict[str, Any],
    options: argparse.Namespace,
) -> Dict[str, Any]:
    timestamp = options.created_at or now_seconds()
    updated_at = options.updated_at or timestamp
    item = {
        "id": options.item_id,
        "title": options.title,
        "type": options.item_type,
        "product": options.product,
        "priority": options.priority,
        "createdAt": timestamp,
        "updatedAt": updated_at,
        "entry": options.entry,
    }
    current["items"].append(item)
    write_indexes(root, current, archive)
    return {"created": True, "item": item}


def move_item(
    root: Path,
    current: Dict[str, Any],
    archive: Dict[str, Any],
    item_id: str,
    archive_item: bool,
    timestamp: Optional[str],
) -> Dict[str, Any]:
    source_items = current["items"] if archive_item else archive["items"]
    target_items = archive["items"] if archive_item else current["items"]
    item = next((value for value in source_items if value["id"] == item_id), None)
    if item is None:
        source_name = CURRENT_FILE if archive_item else ARCHIVE_FILE
        raise ValueError(f"{item_id} is not present in {source_name}")
    if item["entry"] is None:
        raise ValueError(f"{item_id} has no directory entry to move")

    relative = PurePosixPath(item["entry"])
    source_readme = root.joinpath(*relative.parts)
    source_directory = source_readme.parent
    if archive_item:
        target_directory = root / ARCHIVE_DIRECTORY / source_directory.name
        target_entry = (
            PurePosixPath(ARCHIVE_DIRECTORY) / source_directory.name / "README.md"
        ).as_posix()
    else:
        target_directory = root / source_directory.name
        target_entry = (PurePosixPath(source_directory.name) / "README.md").as_posix()

    require_plain_existing_path(root, source_directory, f"{item_id} source directory")
    require_plain_existing_path(root, target_directory, f"{item_id} target directory")
    if not source_directory.is_dir():
        raise FileNotFoundError(source_directory)
    if target_directory.exists():
        raise ValueError(f"target work-item directory already exists: {target_directory}")
    target_directory.parent.mkdir(parents=True, exist_ok=True)

    at = timestamp or now_seconds()
    moved_item = dict(item)
    moved_item["entry"] = target_entry
    moved_item["updatedAt"] = at
    if archive_item:
        moved_item["archivedAt"] = at
    else:
        moved_item.pop("archivedAt", None)

    source_items.remove(item)
    target_items.append(moved_item)
    os.replace(source_directory, target_directory)
    try:
        write_indexes(root, current, archive)
    except (OSError, ValueError):
        os.replace(target_directory, source_directory)
        raise
    return {
        "moved": True,
        "source": CURRENT_FILE if archive_item else ARCHIVE_FILE,
        "target": ARCHIVE_FILE if archive_item else CURRENT_FILE,
        "item": moved_item,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, help="Explicit work-item root directory")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="Validate both indexes and all entries")
    commands.add_parser("init", help="Initialize indexes in a genuinely fresh space")

    list_command = commands.add_parser("list", help="List current work items")
    list_command.add_argument("--limit", type=int, default=5)

    resolve_command = commands.add_parser("resolve", help="Resolve one work-item ID")
    resolve_command.add_argument("item_id")

    find_command = commands.add_parser("find", help="Search index fields and entry READMEs")
    find_command.add_argument("query")
    find_command.add_argument("--scope", choices=("current", "archive", "all"), default="current")
    find_command.add_argument("--limit", type=int, default=10)

    commands.add_parser("new-id", help="Generate one unused Nest UUID19 work-item ID")

    candidates = commands.add_parser(
        "candidates", help="Search both indexes and entry READMEs"
    )
    candidates.add_argument("query")
    candidates.add_argument("--limit", type=int, default=10)
    candidates.set_defaults(scope="all")

    create = commands.add_parser("create", help="Add one current work-item record")
    create.add_argument("--id", dest="item_id", required=True)
    create.add_argument("--title", required=True)
    create.add_argument("--entry", required=True)
    create.add_argument("--type", dest="item_type", type=int, default=0)
    create.add_argument("--product", type=int, default=0)
    create.add_argument("--priority", choices=PRIORITIES, default="未设置")
    create.add_argument("--created-at")
    create.add_argument("--updated-at")

    archive_command = commands.add_parser(
        "archive", help="Move a current work item and its record into the archive"
    )
    archive_command.add_argument("item_id")
    archive_command.add_argument("--at")

    unarchive_command = commands.add_parser(
        "unarchive", help="Move an archived work item and its record into current"
    )
    unarchive_command.add_argument("item_id")
    unarchive_command.add_argument("--at")
    return result


def main(arguments: Optional[Sequence[str]] = None) -> int:
    options = parser().parse_args(arguments)
    try:
        root = discover_root(options.root, allow_missing=options.command == "init")
        payload: Dict[str, Any] = {"root": str(root)}
        if options.command == "init":
            payload.update(initialize(root))
            emit(payload)
            return 0

        current, archive = load_indexes(root)
        if options.command == "validate":
            payload.update(
                {
                    "valid": True,
                    "currentCount": len(current["items"]),
                    "archiveCount": len(archive["items"]),
                }
            )
        elif options.command == "list":
            payload.update(list_current(root, current, options.limit))
        elif options.command == "resolve":
            payload.update(resolve_item(current, archive, options.item_id))
        elif options.command in {"find", "candidates"}:
            values = scoped_items(current, archive, options.scope)
            matches, count = find_matches(
                root,
                ({"source": source, **item} for source, item in values),
                options.query,
                options.limit,
            )
            payload.update(
                {
                    "query": options.query,
                    "matches": matches,
                    "matchCount": count,
                    "truncated": count > options.limit,
                }
            )
            if options.command == "find":
                payload["scope"] = options.scope
        elif options.command == "new-id":
            payload.update(
                {
                    "id": generated_work_item_id(current, archive),
                    "idStrategy": "uuid19",
                }
            )
        elif options.command == "create":
            payload.update(create_item(root, current, archive, options))
        elif options.command == "archive":
            payload.update(
                move_item(root, current, archive, options.item_id, True, options.at)
            )
        else:
            payload.update(
                move_item(root, current, archive, options.item_id, False, options.at)
            )
        emit(payload)
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        emit({"error": str(error)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
