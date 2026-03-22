import re


_PATTERNS = [
    re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{16,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.=:/+]{12,}", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(authorization\s*[=:]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(token\s*[=:]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(secret\s*[=:]\s*)([^\s,;]+)"),
]


def redact_sensitive_text(value: str | None) -> str | None:
    if value is None:
        return None

    redacted = value
    for pattern in _PATTERNS:
        redacted = pattern.sub(_replace_match, redacted)
    return redacted


def sanitize_exception_message(exc: Exception) -> str:
    return redact_sensitive_text(str(exc)) or "Request failed."


def _replace_match(match: re.Match[str]) -> str:
    if match.lastindex and match.lastindex > 1:
        prefix = match.group(1)
        return f"{prefix}[redacted]"
    return "[redacted]"
