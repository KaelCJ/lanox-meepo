from __future__ import annotations

import re
from pathlib import Path


SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:sk|pk|api)[-_][A-Za-z0-9_-]{16,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
)
WINDOWS_PATH = re.compile(r"(?i)(?<![A-Za-z0-9])(?:[A-Z]:\\|\\\\)[^\s\"'<>|]+")
POSIX_PATH = re.compile(r"(?<![A-Za-z0-9._-])/(?:Users|home|var|tmp|opt|srv|mnt|etc)/[^\s\"'<>]+")
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL_QUERY = re.compile(r"(https?://[^\s?#]+)(?:[?#][^\s]*)?", re.IGNORECASE)
LONG_HEX = re.compile(r"\b[a-fA-F0-9]{32,}\b")


def redact_text(value: object, max_chars: int = 2000) -> str:
    if not isinstance(value, str):
        return ""
    text = value.replace("\x00", " ")
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[敏感信息已移除]", text)
    text = WINDOWS_PATH.sub("[本地路径]", text)
    text = POSIX_PATH.sub("[本地路径]", text)
    text = EMAIL.sub("[邮箱]", text)
    text = URL_QUERY.sub(lambda match: match.group(1), text)
    text = LONG_HEX.sub("[长标识符]", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text).strip()
    if len(text) > max_chars:
        text = text[: max_chars - 14].rstrip() + "…[内容已截断]"
    return text


def normalize_tool(name: object) -> str:
    if not isinstance(name, str) or not name:
        return "unknown"
    lowered = name.lower()
    if lowered in {"apply_patch", "patch"}:
        return "patch"
    if lowered in {"exec_command", "write_stdin", "local_shell", "shell"}:
        return "shell"
    if lowered in {"exec", "functions.exec", "functions.wait", "wait"}:
        return "orchestration"
    if lowered.startswith("mcp__"):
        if "browser" in lowered or "chrome" in lowered:
            return "browser"
        return "mcp"
    if lowered.startswith("codex_app__"):
        if "thread" in lowered:
            return "codex-thread"
        return "codex-app"
    if "browser" in lowered or "chrome" in lowered:
        return "browser"
    if "agent" in lowered or "thread" in lowered:
        return "agent"
    if lowered in {"view_image", "imagegen"}:
        return "image"
    if lowered in {"update_plan", "request_user_input"}:
        return "planning"
    return "other"


def safe_extension(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    suffix = Path(value).suffix.lower()
    if 1 < len(suffix) <= 12 and re.fullmatch(r"\.[a-z0-9_+-]+", suffix):
        return suffix
    return None
