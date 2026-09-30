from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


PARSER_VERSION = "2.0.0"
FACET_SCHEMA_VERSION = "2.1.0"
FACET_PROMPT_VERSION = "2.1.0"
CHUNK_PROMPT_VERSION = "2.1.0"
SECTION_SCHEMA_VERSION = "2.1.0"
SECTION_PROMPT_VERSION = "2.1.0"
TEMPLATE_VERSION = "2.1.0"
REPORT_FILENAME_PREFIX = "nest-insights-report"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    data = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def cache_path(cache_root: Path, layer: str, identity: str) -> Path:
    safe_identity = "".join(ch for ch in identity if ch.isalnum() or ch in "-_")
    return cache_root / layer / f"{safe_identity}.json"
