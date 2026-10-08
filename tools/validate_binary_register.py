#!/usr/bin/env python3
"""Validate current binary inventory and unresolved historical records."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any


REGISTER_RELATIVE = Path("docs/third-party-assets.json")
NOTICES_RELATIVE = Path("THIRD_PARTY_NOTICES.md")
ALLOWED_STATUSES = {"pending", "cleared", "private"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_ASSET_FIELDS = {
    "path",
    "role",
    "sha256",
    "observed",
    "status",
    "owner",
    "source",
    "license",
    "redistributionEvidence",
    "notes",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (defaults to the parent of tools/)",
    )
    parser.add_argument(
        "--require-cleared",
        action="store_true",
        help="Fail unless every registered asset has been cleared for redistribution",
    )
    return parser.parse_args()


def normalized_relative_path(raw: Any, field: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{field} must be a non-empty string")
    if "\\" in raw:
        raise ValueError(f"{field} must use forward slashes: {raw}")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{field} must be a normalized relative path: {raw}")
    return path.as_posix()


def read_register(root: Path) -> dict[str, Any]:
    path = root / REGISTER_RELATIVE
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"missing binary register: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"invalid binary register JSON at line {error.lineno}, column {error.colno}"
        ) from error
    if not isinstance(value, dict):
        raise ValueError("binary register root must be an object")
    if value.get("schemaVersion") != 1:
        raise ValueError("binary register schemaVersion must be 1")
    if not isinstance(value.get("releaseBlocked"), bool):
        raise ValueError("binary register releaseBlocked must be a boolean")
    assets = value.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("binary register assets must be a non-empty array")
    return value


def tracked_jars(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
    )
    tracked: set[str] = set()
    for line in result.stdout.splitlines():
        path = line.strip()
        if not path.lower().endswith(".jar"):
            continue
        relative = normalized_relative_path(path, "tracked JAR path")
        # git ls-files still lists files deleted in the working tree but not staged.
        if root.joinpath(*PurePosixPath(relative).parts).is_file():
            tracked.add(relative)
    return tracked


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(root: Path, require_cleared: bool) -> list[str]:
    errors: list[str] = []
    try:
        register = read_register(root)
    except (OSError, ValueError) as error:
        return [str(error)]

    try:
        tracked = tracked_jars(root)
    except (OSError, subprocess.CalledProcessError) as error:
        return [f"could not enumerate tracked JARs: {error}"]

    registered: set[str] = set()
    pending = False
    assets = register["assets"]
    for index, asset in enumerate(assets):
        label = f"assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{label} must be an object")
            continue
        missing = REQUIRED_ASSET_FIELDS - set(asset)
        if missing:
            errors.append(f"{label} missing fields: {', '.join(sorted(missing))}")
            continue

        try:
            relative = normalized_relative_path(asset["path"], f"{label}.path")
        except ValueError as error:
            errors.append(str(error))
            continue
        if relative in registered:
            errors.append(f"duplicate registered path: {relative}")
        registered.add(relative)

        if not relative.lower().endswith(".jar"):
            errors.append(f"{label}.path is not a JAR: {relative}")
        artifact = root.joinpath(*PurePosixPath(relative).parts)
        expected_hash = asset["sha256"]
        if not isinstance(expected_hash, str) or SHA256.fullmatch(expected_hash) is None:
            errors.append(f"{label}.sha256 must be a lowercase SHA-256 value")
        present = asset.get("present", True)
        if not isinstance(present, bool):
            errors.append(f"{label}.present must be a boolean")
        elif present and not artifact.is_file():
            errors.append(f"registered binary is missing: {relative}")
        elif not present and artifact.exists():
            errors.append(f"historical binary is still present: {relative}")
        elif present and isinstance(expected_hash, str) and SHA256.fullmatch(expected_hash):
            if sha256(artifact) != expected_hash:
                errors.append(f"SHA-256 mismatch: {relative}")

        status = asset["status"]
        if not isinstance(status, str) or status not in ALLOWED_STATUSES:
            errors.append(f"{label}.status is invalid: {status!r}")
        if status != "cleared":
            pending = True
        if require_cleared and status != "cleared":
            errors.append(f"{relative} is not cleared for redistribution")
        if status == "cleared":
            for field in ("owner", "source", "license", "redistributionEvidence"):
                if not non_empty(asset[field]):
                    errors.append(f"{label}.{field} is required when status is cleared")

    missing_from_register = sorted(tracked - registered)
    if missing_from_register:
        errors.append(
            "tracked JARs missing from binary register: "
            + ", ".join(missing_from_register)
        )

    if pending and not register["releaseBlocked"]:
        errors.append("releaseBlocked must be true while any asset is pending or private")
    if require_cleared and register["releaseBlocked"]:
        errors.append("releaseBlocked must be false for a cleared release")
    if not (root / NOTICES_RELATIVE).is_file():
        errors.append(f"missing human-readable notice: {NOTICES_RELATIVE}")
    return errors


def main() -> int:
    options = parse_args()
    root = options.root.expanduser().resolve()
    errors = validate(root, options.require_cleared)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    mode = "cleared-release" if options.require_cleared else "current-tree inventory"
    print(f"PASS: binary register is consistent ({mode}; absent historical artifacts not rehashed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
