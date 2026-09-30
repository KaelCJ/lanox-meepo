#!/usr/bin/env python3
"""Mirror the public Nest workspace assets to one absolute target."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable
from uuid import uuid4


FOUNDATION = Path(".workspace-assistant/foundation")
RELEASE_MANIFEST = FOUNDATION / "nest-workspace-release.json"
AGENT_SKILLS = Path(".agents/skills")
CLAUDE_COMMANDS = Path(".claude/commands")
NEST_PREFIX = "nest-"
IGNORED_DIRECTORY_NAMES = {"__pycache__"}
IGNORED_FILE_SUFFIXES = {".pyc", ".pyo"}
CODEX_RULE = Path(".codex/rules/nest-git.rules")
CODEX_HOOKS = Path(".codex/hooks.json")
CODEX_SESSION_START_COMMAND = (
    "java -jar .workspace-assistant/foundation/host-hooks/codex/"
    "codex-session-start.jar"
)
HOOK_MANIFEST_KEY = ".codex/hooks.json#managed-session-start"
SCRIPT_RELATIVE_PATH = Path(
    ".agents/skills/nest-workspace-sync/scripts/sync_workspace.py"
)
MANAGED_SCOPE = (
    ".workspace-assistant/foundation/",
    ".agents/skills/nest-*",
    ".claude/commands/nest-*",
    ".codex/rules/nest-git.rules",
    ".codex/hooks.json: managed SessionStart hook only",
)


class SyncError(RuntimeError):
    """A fail-closed synchronization error."""


def emit(value: Dict[str, Any], *, stream: Any = sys.stdout) -> None:
    try:
        stream.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    stream.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Inspect synchronization status without modifying the target",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Existing target directory as an absolute path",
    )
    parser.add_argument(
        "--backup-root",
        required=False,
        help="Absolute directory below the source workspace's governed temporary root",
    )
    return parser.parse_args()


def source_root() -> Path:
    script = Path(__file__).resolve()
    try:
        root = script.parents[4]
    except IndexError as error:
        raise SyncError(f"cannot derive source workspace from script: {script}") from error
    expected = (root / SCRIPT_RELATIVE_PATH).resolve()
    if expected != script:
        raise SyncError(f"script is outside the expected Skill path: {script}")
    return root


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def reject_filesystem_root(path: Path, label: str) -> None:
    if path.parent == path:
        raise SyncError(f"{label} must not be a filesystem or share root: {path}")


def is_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError as error:
        raise SyncError(f"cannot inspect path: {path}: {error}") from error
    attributes = getattr(info, "st_file_attributes", 0)
    return path.is_symlink() or bool(
        attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def reject_reparse(path: Path, label: str) -> None:
    if is_reparse(path):
        raise SyncError(f"{label} must not be a symlink, junction, or reparse point: {path}")


def reject_existing_reparse_chain(path: Path, label: str) -> None:
    for candidate in reversed((path, *path.parents)):
        if path_exists(candidate):
            reject_reparse(candidate, label)


def absolute_existing_directory(raw: str, label: str) -> Path:
    value = Path(raw)
    if not value.is_absolute():
        raise SyncError(f"{label} must be an absolute path: {raw}")
    if not value.exists() or not value.is_dir():
        raise SyncError(f"{label} must be an existing directory: {value}")
    reject_existing_reparse_chain(value, label)
    resolved = value.resolve()
    reject_filesystem_root(resolved, label)
    return resolved


def require_current_source_directory(source: Path) -> None:
    current = Path.cwd().resolve()
    if not is_within(current, source):
        raise SyncError(
            "the executed Skill and current code space resolve to different sources: "
            f"skill={source}; current={current}"
        )


def absolute_backup_root(raw: str) -> Path:
    value = Path(raw)
    if not value.is_absolute():
        raise SyncError(f"backup root must be an absolute path: {raw}")
    if value.exists() and not value.is_dir():
        raise SyncError(f"backup root is not a directory: {value}")
    reject_existing_reparse_chain(value, "backup root")
    resolved = value.resolve()
    reject_filesystem_root(resolved, "backup root")
    return resolved


def reject_overlap(
    source: Path,
    target: Path,
    backup_root: Path | None = None,
) -> None:
    if is_within(source, target) or is_within(target, source):
        raise SyncError(f"source and target must not be equal or nested: {source} -> {target}")
    if backup_root is not None:
        for workspace, label in ((source, "source"), (target, "target")):
            if is_within(backup_root, workspace) or is_within(workspace, backup_root):
                raise SyncError(f"backup root must not overlap {label} workspace: {backup_root}")


def validate_path_chain(workspace: Path, relative: Path, label: str) -> None:
    current = workspace
    for position, part in enumerate(relative.parts):
        current = current / part
        if path_exists(current):
            reject_reparse(current, label)
            if position < len(relative.parts) - 1 and not current.is_dir():
                raise SyncError(f"{label} parent is not a directory: {current}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_manifest_entry(
    result: Dict[str, Dict[str, Any]],
    folded: Dict[str, str],
    key: str,
    value: Dict[str, Any],
) -> None:
    folded_key = key.casefold()
    previous = folded.get(folded_key)
    if previous is not None and previous != key:
        raise SyncError(f"case-insensitive path collision: {previous} / {key}")
    folded[folded_key] = key
    result[key] = value


def add_tree_manifest(
    workspace: Path,
    relative: Path,
    result: Dict[str, Dict[str, Any]],
    folded: Dict[str, str],
) -> None:
    root = workspace / relative
    if not path_exists(root):
        return
    reject_reparse(root, "managed directory")
    if not root.is_dir():
        raise SyncError(f"managed path is not a directory: {root}")
    add_manifest_entry(
        result,
        folded,
        relative.as_posix(),
        {"type": "directory"},
    )

    for current, directory_names, file_names in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)
        reject_reparse(current_path, "managed directory")
        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in IGNORED_DIRECTORY_NAMES
        )
        file_names = sorted(
            name
            for name in file_names
            if Path(name).suffix.casefold() not in IGNORED_FILE_SUFFIXES
        )
        for name in directory_names:
            path = current_path / name
            reject_reparse(path, "managed directory")
            if not path.is_dir():
                raise SyncError(f"unsupported managed entry type: {path}")
            add_manifest_entry(
                result,
                folded,
                path.relative_to(workspace).as_posix(),
                {"type": "directory"},
            )
        for name in file_names:
            path = current_path / name
            reject_reparse(path, "managed file")
            if not path.is_file():
                raise SyncError(f"unsupported managed entry type: {path}")
            add_manifest_entry(
                result,
                folded,
                path.relative_to(workspace).as_posix(),
                {
                    "type": "file",
                    "size": path.stat().st_size,
                    "sha256": sha256(path),
                },
            )


def add_file_manifest(
    workspace: Path,
    relative: Path,
    result: Dict[str, Dict[str, Any]],
    folded: Dict[str, str],
) -> None:
    path = workspace / relative
    if not path_exists(path):
        return
    reject_reparse(path, "managed file")
    if not path.is_file():
        raise SyncError(f"managed path is not a file: {path}")
    add_manifest_entry(
        result,
        folded,
        relative.as_posix(),
        {
            "type": "file",
            "size": path.stat().st_size,
            "sha256": sha256(path),
        },
    )


def add_any_manifest(
    workspace: Path,
    relative: Path,
    result: Dict[str, Dict[str, Any]],
    folded: Dict[str, str],
) -> None:
    path = workspace / relative
    if not path_exists(path):
        return
    if path.is_dir():
        add_tree_manifest(workspace, relative, result, folded)
    else:
        add_file_manifest(workspace, relative, result, folded)


def selected_entries(workspace: Path, parent_relative: Path) -> Dict[str, Path]:
    parent = workspace / parent_relative
    if not path_exists(parent):
        return {}
    reject_reparse(parent, "managed selection directory")
    if not parent.is_dir():
        raise SyncError(f"managed selection path is not a directory: {parent}")

    entries: Dict[str, Path] = {}
    folded: Dict[str, str] = {}
    for child in sorted(parent.iterdir(), key=lambda item: item.name.casefold()):
        if not child.name.casefold().startswith(NEST_PREFIX):
            continue
        reject_reparse(child, "managed selected entry")
        relative = child.relative_to(workspace)
        key = relative.as_posix()
        folded_key = key.casefold()
        previous = folded.get(folded_key)
        if previous is not None and previous != key:
            raise SyncError(f"case-insensitive path collision: {previous} / {key}")
        folded[folded_key] = key
        entries[key] = child
    return entries


def read_json_document(path: Path) -> Dict[str, Any] | None:
    if not path_exists(path):
        return None
    reject_reparse(path, "managed JSON file")
    if not path.is_file():
        raise SyncError(f"managed JSON path is not a file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SyncError(f"cannot read managed JSON file: {path}: {error}") from error
    if not isinstance(value, dict):
        raise SyncError(f"managed JSON root must be an object: {path}")
    return value


def is_managed_hook(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("command") == CODEX_SESSION_START_COMMAND
    )


def managed_hook_groups(document: Dict[str, Any]) -> list[Dict[str, Any]]:
    hooks = document.get("hooks")
    if hooks is None:
        return []
    if not isinstance(hooks, dict):
        raise SyncError("Codex hooks.json field 'hooks' must be an object")
    groups = hooks.get("SessionStart")
    if groups is None:
        return []
    if not isinstance(groups, list):
        raise SyncError("Codex hooks.json field 'SessionStart' must be an array")

    result: list[Dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, dict):
            raise SyncError("Codex SessionStart entries must be objects")
        nested = group.get("hooks")
        if nested is None:
            continue
        if not isinstance(nested, list):
            raise SyncError("Codex SessionStart 'hooks' fields must be arrays")
        for hook in nested:
            if not isinstance(hook, dict):
                raise SyncError("Codex hook entries must be objects")
        managed = [copy.deepcopy(hook) for hook in nested if is_managed_hook(hook)]
        if managed:
            managed_group = copy.deepcopy(group)
            managed_group["hooks"] = managed
            result.append(managed_group)
    return result


def remove_managed_hooks(document: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(document)
    hooks = result.get("hooks")
    if hooks is None:
        return result
    if not isinstance(hooks, dict):
        raise SyncError("Codex hooks.json field 'hooks' must be an object")
    groups = hooks.get("SessionStart")
    if groups is None:
        return result
    if not isinstance(groups, list):
        raise SyncError("Codex hooks.json field 'SessionStart' must be an array")

    remaining_groups: list[Dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, dict):
            raise SyncError("Codex SessionStart entries must be objects")
        nested = group.get("hooks")
        if nested is None:
            remaining_groups.append(group)
            continue
        if not isinstance(nested, list):
            raise SyncError("Codex SessionStart 'hooks' fields must be arrays")
        remaining_hooks = []
        for hook in nested:
            if not isinstance(hook, dict):
                raise SyncError("Codex hook entries must be objects")
            if not is_managed_hook(hook):
                remaining_hooks.append(hook)
        if remaining_hooks:
            kept_group = copy.deepcopy(group)
            kept_group["hooks"] = remaining_hooks
            remaining_groups.append(kept_group)
        elif not nested:
            remaining_groups.append(group)

    if remaining_groups:
        hooks["SessionStart"] = remaining_groups
    else:
        hooks.pop("SessionStart", None)
    if not hooks:
        result.pop("hooks", None)
    return result


def merge_managed_hooks(
    target_document: Dict[str, Any] | None,
    source_groups: list[Dict[str, Any]],
) -> Dict[str, Any] | None:
    result = remove_managed_hooks(target_document or {})
    if source_groups:
        hooks = result.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            raise SyncError("Codex hooks.json field 'hooks' must be an object")
        groups = hooks.setdefault("SessionStart", [])
        if not isinstance(groups, list):
            raise SyncError("Codex hooks.json field 'SessionStart' must be an array")
        groups.extend(copy.deepcopy(source_groups))
    return result or None


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def manifest_fingerprint(manifest: Dict[str, Dict[str, Any]]) -> str:
    release_key = RELEASE_MANIFEST.as_posix()
    fingerprint_manifest = {
        key: value
        for key, value in manifest.items()
        if key != release_key
    }
    return hashlib.sha256(
        canonical_json(fingerprint_manifest).encode("utf-8")
    ).hexdigest()


def release_state(workspace: Path) -> Dict[str, Any]:
    path = workspace / RELEASE_MANIFEST
    if not path_exists(path):
        return {"present": False, "valid": False, "value": None, "error": None}
    try:
        value = read_json_document(path)
        if value is None:
            raise SyncError(f"release manifest is missing: {path}")
        if value.get("schemaVersion") != 1:
            raise SyncError(f"unsupported release manifest schema: {path}")
        release_id = value.get("releaseId")
        released_at = value.get("releasedAt")
        fingerprint = value.get("baselineFingerprint")
        if not isinstance(release_id, str) or not release_id.strip():
            raise SyncError(f"release manifest releaseId is invalid: {path}")
        if not isinstance(released_at, str) or not released_at.strip():
            raise SyncError(f"release manifest releasedAt is invalid: {path}")
        if (
            not isinstance(fingerprint, str)
            or len(fingerprint) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in fingerprint)
        ):
            raise SyncError(f"release manifest baselineFingerprint is invalid: {path}")
        return {"present": True, "valid": True, "value": value, "error": None}
    except SyncError as error:
        return {
            "present": True,
            "valid": False,
            "value": None,
            "error": str(error),
        }


def collect_state(workspace: Path) -> Dict[str, Any]:
    agent_entries = selected_entries(workspace, AGENT_SKILLS)
    claude_entries = selected_entries(workspace, CLAUDE_COMMANDS)
    hooks_document = read_json_document(workspace / CODEX_HOOKS)
    hook_groups = managed_hook_groups(hooks_document or {})

    manifest: Dict[str, Dict[str, Any]] = {}
    folded: Dict[str, str] = {}
    add_tree_manifest(workspace, FOUNDATION, manifest, folded)
    for key in sorted(agent_entries):
        add_any_manifest(workspace, Path(key), manifest, folded)
    for key in sorted(claude_entries):
        add_any_manifest(workspace, Path(key), manifest, folded)
    add_file_manifest(workspace, CODEX_RULE, manifest, folded)
    if hook_groups:
        add_manifest_entry(
            manifest,
            folded,
            HOOK_MANIFEST_KEY,
            {
                "type": "json-fragment",
                "value": canonical_json(hook_groups),
            },
        )

    return {
        "manifest": manifest,
        "fingerprint": manifest_fingerprint(manifest),
        "release": release_state(workspace),
        "agentEntries": agent_entries,
        "claudeEntries": claude_entries,
        "hooks": hooks_document,
        "hookGroups": hook_groups,
        "hookFull": canonical_json(hooks_document) if hooks_document is not None else None,
        "hookUnmanaged": canonical_json(remove_managed_hooks(hooks_document or {})),
    }


def diff(
    source: Dict[str, Dict[str, Any]],
    target: Dict[str, Dict[str, Any]],
) -> Dict[str, int]:
    source_paths = set(source)
    target_paths = set(target)
    return {
        "added": len(source_paths - target_paths),
        "changed": sum(source[path] != target[path] for path in source_paths & target_paths),
        "deleted": len(target_paths - source_paths),
        "sourceFiles": sum(value["type"] == "file" for value in source.values()),
        "targetFilesBefore": sum(value["type"] == "file" for value in target.values()),
        "sourceDirectories": sum(
            value["type"] == "directory" for value in source.values()
        ),
        "targetDirectoriesBefore": sum(
            value["type"] == "directory" for value in target.values()
        ),
    }


def diff_details(
    source: Dict[str, Dict[str, Any]],
    target: Dict[str, Dict[str, Any]],
) -> Dict[str, list[str]]:
    source_paths = set(source)
    target_paths = set(target)
    return {
        "missing": sorted(source_paths - target_paths),
        "different": sorted(
            path
            for path in source_paths & target_paths
            if source[path] != target[path]
        ),
        "extra": sorted(target_paths - source_paths),
    }


def validate_source_release(source_state: Dict[str, Any]) -> Dict[str, Any]:
    release = source_state["release"]
    if not release["present"]:
        raise SyncError(
            f"source release manifest is missing: {RELEASE_MANIFEST.as_posix()}"
        )
    if not release["valid"]:
        raise SyncError(release["error"])
    value = release["value"]
    if value["baselineFingerprint"].casefold() != source_state["fingerprint"].casefold():
        raise SyncError(
            "source release manifest fingerprint differs from the current managed "
            "assets; update releaseId, releasedAt, and baselineFingerprint before "
            "auditing or synchronizing"
        )
    return value


def classify_sync_status(
    source_state: Dict[str, Any],
    target_state: Dict[str, Any],
) -> str:
    if source_state["manifest"] == target_state["manifest"]:
        return "CURRENT"
    if not target_state["manifest"]:
        return "NOT_ADOPTED"

    target_release = target_state["release"]
    if target_release["present"]:
        if not target_release["valid"]:
            return "LOCALLY_MODIFIED"
        source_release_id = source_state["release"]["value"]["releaseId"]
        target_release_id = target_release["value"]["releaseId"]
        if source_release_id == target_release_id:
            return "LOCALLY_MODIFIED"
        return "OUTDATED"
    return "PARTIAL"


def inspect_workspace(source: Path, target: Path) -> Dict[str, Any]:
    validation_paths = (
        FOUNDATION,
        AGENT_SKILLS,
        CLAUDE_COMMANDS,
        CODEX_RULE,
        CODEX_HOOKS,
    )
    for relative in validation_paths:
        validate_path_chain(source, relative, "managed source path")
        validate_path_chain(target, relative, "managed target path")

    source_state = collect_state(source)
    target_state = collect_state(target)
    source_release = validate_source_release(source_state)
    target_release = target_state["release"]
    return {
        "status": "checked",
        "syncStatus": classify_sync_status(source_state, target_state),
        "source": str(source),
        "target": str(target),
        "scope": list(MANAGED_SCOPE),
        "sourceRelease": source_release,
        "targetRelease": target_release["value"] if target_release["valid"] else None,
        "targetReleaseError": target_release["error"],
        "sourceFingerprint": source_state["fingerprint"],
        "targetFingerprint": target_state["fingerprint"],
        "changes": diff(source_state["manifest"], target_state["manifest"]),
        "differences": diff_details(
            source_state["manifest"],
            target_state["manifest"],
        ),
    }


def copy_entry(source: Path, destination: Path) -> None:
    if not path_exists(source):
        raise SyncError(f"cannot copy missing managed path: {source}")
    reject_reparse(source, "managed source path")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(
            source,
            destination,
            copy_function=shutil.copy2,
            ignore=shutil.ignore_patterns(
                *IGNORED_DIRECTORY_NAMES,
                *(f"*{suffix}" for suffix in IGNORED_FILE_SUFFIXES),
            ),
        )
    elif source.is_file():
        shutil.copy2(source, destination)
    else:
        raise SyncError(f"unsupported managed entry type: {source}")


def remove_managed_path(path: Path, target: Path) -> None:
    try:
        path.relative_to(target)
    except ValueError as error:
        raise SyncError(f"refusing to remove path outside target: {path}") from error
    if not path_exists(path):
        return
    reject_reparse(path, "managed target path")
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def operation_paths(
    source_state: Dict[str, Any],
    target_state: Dict[str, Any],
    hook_changed: bool,
) -> list[Path]:
    paths = {FOUNDATION, CODEX_RULE}
    paths.update(Path(key) for key in source_state["agentEntries"])
    paths.update(Path(key) for key in target_state["agentEntries"])
    paths.update(Path(key) for key in source_state["claudeEntries"])
    paths.update(Path(key) for key in target_state["claudeEntries"])
    if hook_changed:
        paths.add(CODEX_HOOKS)
    return sorted(paths, key=lambda path: (len(path.parts), path.as_posix().casefold()))


def snapshot_manifest(
    workspace: Path,
    paths: Iterable[Path],
) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    folded: Dict[str, str] = {}
    for relative in paths:
        add_any_manifest(workspace, relative, result, folded)
    return result


def snapshot_target(
    target: Path,
    paths: Iterable[Path],
    backup: Path,
) -> Dict[str, bool]:
    existed: Dict[str, bool] = {}
    for relative in paths:
        source = target / relative
        key = relative.as_posix()
        existed[key] = path_exists(source)
        if existed[key]:
            copy_entry(source, backup / relative)
    return existed


def restore_target(
    target: Path,
    backup: Path,
    paths: Iterable[Path],
    existed: Dict[str, bool],
) -> list[str]:
    errors: list[str] = []
    for relative in sorted(
        paths,
        key=lambda path: (-len(path.parts), path.as_posix().casefold()),
    ):
        destination = target / relative
        key = relative.as_posix()
        try:
            if path_exists(destination):
                remove_managed_path(destination, target)
            if existed.get(key):
                copy_entry(backup / relative, destination)
        except (OSError, SyncError) as error:
            errors.append(f"{destination}: {error}")
    return errors


def stage_source_assets(
    source: Path,
    source_state: Dict[str, Any],
    target_state: Dict[str, Any],
    staging: Path,
    hook_changed: bool,
) -> None:
    if path_exists(source / FOUNDATION):
        copy_entry(source / FOUNDATION, staging / FOUNDATION)
    for key in sorted(source_state["agentEntries"]):
        copy_entry(source / key, staging / key)
    for key in sorted(source_state["claudeEntries"]):
        copy_entry(source / key, staging / key)
    if path_exists(source / CODEX_RULE):
        copy_entry(source / CODEX_RULE, staging / CODEX_RULE)
    if hook_changed:
        desired_hooks = merge_managed_hooks(
            target_state["hooks"],
            source_state["hookGroups"],
        )
        if desired_hooks is not None:
            write_json(staging / CODEX_HOOKS, desired_hooks)


def replace_from_stage(target: Path, staging: Path, relative: Path) -> None:
    destination = target / relative
    if path_exists(destination):
        remove_managed_path(destination, target)
    staged = staging / relative
    if path_exists(staged):
        copy_entry(staged, destination)


def apply_sync(
    target: Path,
    staging: Path,
    source_state: Dict[str, Any],
    target_state: Dict[str, Any],
    hook_changed: bool,
) -> None:
    replace_from_stage(target, staging, FOUNDATION)

    for key in sorted(target_state["agentEntries"]):
        destination = target / key
        if path_exists(destination):
            remove_managed_path(destination, target)
    for key in sorted(source_state["agentEntries"]):
        copy_entry(staging / key, target / key)

    for key in sorted(target_state["claudeEntries"]):
        destination = target / key
        if path_exists(destination):
            remove_managed_path(destination, target)
    for key in sorted(source_state["claudeEntries"]):
        copy_entry(staging / key, target / key)

    replace_from_stage(target, staging, CODEX_RULE)
    if hook_changed:
        replace_from_stage(target, staging, CODEX_HOOKS)


def synchronize(source: Path, target: Path, backup_root: Path) -> Dict[str, Any]:
    validation_paths = (
        FOUNDATION,
        AGENT_SKILLS,
        CLAUDE_COMMANDS,
        CODEX_RULE,
        CODEX_HOOKS,
    )
    for relative in validation_paths:
        validate_path_chain(source, relative, "managed source path")
        validate_path_chain(target, relative, "managed target path")

    source_state = collect_state(source)
    target_state = collect_state(target)
    source_release = validate_source_release(source_state)
    source_manifest = source_state["manifest"]
    target_manifest = target_state["manifest"]
    changes = diff(source_manifest, target_manifest)
    hook_changed = source_state["hookGroups"] != target_state["hookGroups"]
    if not any(changes[name] for name in ("added", "changed", "deleted")):
        return {
            "status": "unchanged",
            "source": str(source),
            "target": str(target),
            "scope": list(MANAGED_SCOPE),
            "syncStatus": "CURRENT",
            "sourceRelease": source_release,
            "sourceFingerprint": source_state["fingerprint"],
            "changes": changes,
            "backup": None,
            "verification": {"missing": 0, "extra": 0, "different": 0},
        }

    run_id = datetime.now().strftime("nest-workspace-sync-%Y%m%d-%H%M%S-%f-") + uuid4().hex[:8]
    run_root = backup_root / run_id
    if run_root.exists():
        raise SyncError(f"generated backup directory already exists: {run_root}")
    staging = run_root / "staging"
    backup = run_root / "backup"
    run_root.mkdir(parents=True)

    paths = operation_paths(source_state, target_state, hook_changed)
    target_snapshot = snapshot_manifest(target, paths)
    plan = {
        "source": str(source),
        "target": str(target),
        "scope": list(MANAGED_SCOPE),
        "sourceRelease": source_release,
        "sourceFingerprint": source_state["fingerprint"],
        "changes": changes,
        "differences": diff_details(source_manifest, target_manifest),
    }
    write_json(run_root / "plan.json", plan)

    mutation_started = False
    existed: Dict[str, bool] = {}
    try:
        stage_source_assets(
            source,
            source_state,
            target_state,
            staging,
            hook_changed,
        )

        backup.mkdir()
        existed = snapshot_target(target, paths, backup)
        if snapshot_manifest(backup, paths) != target_snapshot:
            raise SyncError("backup manifest differs from the frozen target manifest")
        if collect_state(source)["manifest"] != source_manifest:
            raise SyncError("source changed during staging; target was not modified")
        current_target = collect_state(target)
        if current_target["manifest"] != target_manifest:
            raise SyncError("target changed before synchronization; target was not modified")
        if current_target["hookFull"] != target_state["hookFull"]:
            raise SyncError(
                "target Codex hooks changed before synchronization; target was not modified"
            )

        mutation_started = True
        apply_sync(
            target,
            staging,
            source_state,
            target_state,
            hook_changed,
        )

        source_after = collect_state(source)
        target_after = collect_state(target)
        if source_after["manifest"] != source_manifest:
            raise SyncError("source changed during synchronization")
        if target_after["manifest"] != source_manifest:
            raise SyncError("target managed assets differ from source")
        if target_after["hookUnmanaged"] != target_state["hookUnmanaged"]:
            raise SyncError("target unrelated Codex hooks changed during synchronization")
    except (OSError, SyncError, KeyboardInterrupt) as error:
        rollback_errors = (
            restore_target(target, backup, paths, existed) if mutation_started else []
        )
        if mutation_started and not rollback_errors:
            try:
                if snapshot_manifest(target, paths) != target_snapshot:
                    rollback_errors.append(
                        "restored target manifest differs from its original state"
                    )
            except (OSError, SyncError) as verification_error:
                rollback_errors.append(f"cannot verify restored target: {verification_error}")
        failure = {
            "status": "failed",
            **plan,
            "backup": str(backup),
            "error": str(error),
            "rollback": (
                "failed" if rollback_errors else "restored" if mutation_started else "not-needed"
            ),
            "rollbackErrors": rollback_errors,
        }
        record_error = None
        try:
            write_json(run_root / "result.json", failure)
        except OSError as write_error:
            record_error = str(write_error)
        raise SyncError(
            f"{error}; backup={backup}; rollback={failure['rollback']}"
            + (f"; result-record-error={record_error}" if record_error else "")
        ) from error

    staging_cleanup_error = None
    try:
        shutil.rmtree(staging)
    except OSError as error:
        staging_cleanup_error = str(error)
    result = {
        "status": "synchronized",
        "syncStatus": "CURRENT",
        **plan,
        "backup": str(backup),
        "verification": {"missing": 0, "extra": 0, "different": 0},
        "stagingCleanupError": staging_cleanup_error,
    }
    try:
        write_json(run_root / "result.json", result)
    except OSError as error:
        result["status"] = "synchronized_unrecorded"
        result["resultRecordError"] = str(error)
    return result


def main() -> int:
    args = parse_args()
    try:
        source = source_root()
        require_current_source_directory(source)
        target = absolute_existing_directory(args.target, "target")
        if args.check:
            reject_overlap(source, target)
            result = inspect_workspace(source, target)
        else:
            if not args.backup_root:
                raise SyncError("backup root is required unless --check is used")
            backup_root = absolute_backup_root(args.backup_root)
            reject_overlap(source, target, backup_root)
            backup_root.mkdir(parents=True, exist_ok=True)
            reject_existing_reparse_chain(backup_root, "backup root")
            result = synchronize(source, target, backup_root)
        emit(result)
        return 0 if result["status"] in {"checked", "synchronized", "unchanged"} else 2
    except (OSError, SyncError, KeyboardInterrupt) as error:
        emit({"status": "failed", "error": str(error)}, stream=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
