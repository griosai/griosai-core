from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any


VAULT_DIRS = ("notes", "dashboards", "images", "inbox", "lineage", "notebook-packets")


@dataclass(frozen=True)
class AnalysisRecord:
    title: str
    summary: str
    observations: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    model: str = "manual"
    source_image: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(
        cls,
        data: dict[str, Any],
        *,
        model: str = "manual",
        source_image: str | None = None,
    ) -> "AnalysisRecord":
        return cls(
            title=str(data.get("title") or data.get("headline") or "GriosAI Analysis"),
            summary=str(data.get("summary") or data.get("description") or ""),
            observations=_string_list(data.get("observations") or data.get("findings") or []),
            actions=_string_list(data.get("actions") or data.get("recommendations") or []),
            model=str(data.get("model") or model),
            source_image=source_image or _optional_string(data.get("source_image")),
            raw=data,
        )


def ensure_vault(vault_dir: Path) -> Path:
    vault = vault_dir.expanduser().resolve()
    vault.mkdir(parents=True, exist_ok=True)
    for directory in VAULT_DIRS:
        (vault / directory).mkdir(exist_ok=True)
    return vault


def safe_child(base: Path, *parts: str) -> Path:
    root = base.expanduser().resolve()
    child = root.joinpath(*parts).resolve()
    if child != root and root not in child.parents:
        raise ValueError(f"Refusing to write outside vault: {child}")
    return child


def slugify(value: str, *, fallback: str = "analysis", max_length: int = 80) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug or fallback)[:max_length].strip("-") or fallback


def write_analysis_note(
    vault_dir: Path,
    record: AnalysisRecord,
    *,
    slug: str | None = None,
) -> Path:
    vault = ensure_vault(vault_dir)
    note_slug = slugify(slug or record.title)
    path = unique_path(safe_child(vault, "notes", f"{note_slug}.md"))
    body = render_markdown(record)
    path.write_text(body, encoding="utf-8")
    return path


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = path.stem
    suffix = path.suffix
    for counter in range(1, 10_000):
        counter_suffix = "" if counter == 1 else f"-{counter}"
        candidate = path.with_name(f"{stem}-{timestamp}{counter_suffix}{suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Could not allocate a unique path for {path}")


def list_notes(vault_dir: Path) -> list[dict[str, str]]:
    notes_dir = safe_child(ensure_vault(vault_dir), "notes")
    notes: list[dict[str, str]] = []
    for path in sorted(notes_dir.glob("*.md"), key=lambda item: item.stat().st_mtime, reverse=True):
        notes.append(
            {
                "name": path.name,
                "title": _title_from_note(path),
                "updated_at": datetime.fromtimestamp(
                    path.stat().st_mtime,
                    tz=timezone.utc,
                ).isoformat(),
            }
        )
    return notes


def render_markdown(record: AnalysisRecord) -> str:
    observations = (
        "\n".join(f"- {escape(_single_line(item))}" for item in record.observations)
        or "- None captured yet."
    )
    actions = (
        "\n".join(f"- {escape(_single_line(item))}" for item in record.actions)
        or "- None captured yet."
    )
    source_image = _single_line(record.source_image or "")
    raw_json = json.dumps(record.raw, indent=2, sort_keys=True)
    raw_fence = _code_fence(raw_json)
    return (
        "---\n"
        f"title: {json.dumps(_single_line(record.title))}\n"
        f"created_at: {json.dumps(_single_line(record.created_at))}\n"
        f"model: {json.dumps(_single_line(record.model))}\n"
        f"source_image: {json.dumps(source_image)}\n"
        "---\n\n"
        f"# {escape(_single_line(record.title))}\n\n"
        f"{escape(record.summary)}\n\n"
        "## Observations\n\n"
        f"{observations}\n\n"
        "## Actions\n\n"
        f"{actions}\n\n"
        "## Raw\n\n"
        f"{raw_fence}json\n"
        f"{raw_json}\n"
        f"{raw_fence}\n"
    )


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _title_from_note(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return path.stem


def _single_line(value: str) -> str:
    return " ".join(str(value).splitlines()).strip()


def _code_fence(content: str) -> str:
    longest = 2
    for match in re.finditer(r"`+", content):
        longest = max(longest, len(match.group(0)))
    return "`" * (longest + 1)
