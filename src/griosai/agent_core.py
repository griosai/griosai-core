from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


def _hash_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _compact_timestamp(value: str) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        timestamp = value.replace("-", "").replace(":", "")
        timestamp = timestamp.split(".", 1)[0]
        return timestamp.replace("+0000", "Z").replace("+00:00", "Z")
    return parsed.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
