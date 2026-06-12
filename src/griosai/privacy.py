from __future__ import annotations

import re


SECRET_REDACTION = "[redacted-secret]"

SECRET_VALUE_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[a-z0-9._~+/=-]{20,}"
)
BEARER_TOKEN_RE = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{8,}")
OPENAI_STYLE_KEY_RE = re.compile(r"\bsk-[a-zA-Z0-9][a-zA-Z0-9_-]{15,}\b")


def contains_likely_secret(value: object) -> bool:
    text = str(value)
    return bool(
        SECRET_VALUE_RE.search(text)
        or BEARER_TOKEN_RE.search(text)
        or OPENAI_STYLE_KEY_RE.search(text)
    )


def redact_likely_secrets(value: object) -> str:
    text = str(value)
    text = BEARER_TOKEN_RE.sub(f"Bearer {SECRET_REDACTION}", text)
    text = SECRET_VALUE_RE.sub(
        lambda match: f"{match.group(1)}={SECRET_REDACTION}",
        text,
    )
    return OPENAI_STYLE_KEY_RE.sub(SECRET_REDACTION, text)
