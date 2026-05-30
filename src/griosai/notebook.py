from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from fnmatch import fnmatch
from io import StringIO
from pathlib import Path
from typing import Any, Mapping

from .analysis_schema import require_valid_analysis_payload
from .brain import AnalysisRecord, ensure_vault, safe_child, slugify, unique_path
from .dashboard import render_dashboard


REDACTION_POLICY_VERSION = "notebook-packet-v1"
DEFAULT_PACKET_SOURCES = ("index.md", "tables.csv", "report.html", "manifest.json")
DEFAULT_DENY_SOURCES = ("*.jsonl", "*transcript*", "raw-*", ".env*", "*.token", "*.secret")

_ABSOLUTE_PATH_RE = re.compile(
    r"(?<![\w.-])(?:/(?:Users|home|Volumes|private|var/folders|data|mnt|opt|tmp)/[^\s)>\"]+|[A-Za-z]:[\\/][^\s)>\"]+)"
)
_HOME_PATH_RE = re.compile(r"(?<![\w.-])~/[^\s)>\"]+")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{8,}")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?"
    r"(?!\[redacted-secret\])[^'\"\s,;]+"
)
_OPENAI_STYLE_KEY_RE = re.compile(r"\bsk-[a-zA-Z0-9]{16,}\b")


class NotebookPacketError(ValueError):
    pass


@dataclass(frozen=True)
class NotebookPacket:
    dashboard_id: str
    packet_dir: Path
    sources: tuple[str, ...] = DEFAULT_PACKET_SOURCES
    deny_sources: tuple[str, ...] = DEFAULT_DENY_SOURCES

    def connector_payload(self) -> dict[str, object]:
        return {
            "dashboard_id": self.dashboard_id,
            "packet_dir": str(self.packet_dir),
            "sources": list(self.sources),
            "deny_sources": list(self.deny_sources),
        }

    def source_paths(self) -> list[Path]:
        return [self.packet_dir / source for source in self.sources]


class NotebookConnectorAdapter:
    """Small Python-facing facade for notebook and NotebookLM source workflows."""

    def __init__(self, vault_dir: str | Path, *, packet_root: str | Path | None = None) -> None:
        self.vault_dir = Path(vault_dir)
        self.packet_root = Path(packet_root) if packet_root is not None else None

    def write_packet(
        self,
        data: AnalysisRecord | Mapping[str, Any],
        *,
        slug: str | None = None,
    ) -> NotebookPacket:
        record = (
            data
            if isinstance(data, AnalysisRecord)
            else AnalysisRecord.from_mapping(require_valid_analysis_payload(dict(data)))
        )
        return write_notebook_packet(
            self.vault_dir,
            record,
            slug=slug,
            packet_root=self.packet_root,
        )


def write_notebook_packet(
    vault_dir: Path,
    record: AnalysisRecord,
    *,
    slug: str | None = None,
    packet_root: Path | None = None,
) -> NotebookPacket:
    vault = ensure_vault(vault_dir)
    root = _resolve_packet_root(vault, packet_root)
    root.mkdir(parents=True, exist_ok=True)

    dashboard_id = slugify(slug or record.title, fallback="notebook-packet")
    packet_dir = unique_path(root / dashboard_id)
    packet = NotebookPacket(dashboard_id=packet_dir.name, packet_dir=packet_dir)
    sanitized = _sanitize_record(record)
    contents = _packet_contents(packet, sanitized, record)
    _validate_packet_contents(contents)

    packet_dir.mkdir()
    for name, content in contents.items():
        path = packet_dir / name
        path.write_text(content, encoding="utf-8")

    findings = validate_notebook_packet(packet_dir)
    if findings:
        raise NotebookPacketError("; ".join(findings))
    return packet


def validate_notebook_packet(packet_dir: Path) -> list[str]:
    root = packet_dir.expanduser().resolve()
    findings: list[str] = []
    if not root.is_dir():
        return [f"packet directory does not exist: {root}"]

    for path in sorted(root.iterdir()):
        if path.name.startswith("."):
            findings.append(f"hidden file is not allowed: {path.name}")
        if any(fnmatch(path.name, pattern) for pattern in DEFAULT_DENY_SOURCES):
            findings.append(f"denied source file is not allowed: {path.name}")
        if path.is_dir():
            findings.append(f"subdirectory is not allowed: {path.name}")
            continue
        if path.is_symlink():
            findings.append(f"symlink is not allowed: {path.name}")
            continue
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                findings.append(f"non-text packet file requires explicit review: {path.name}")
                continue
            findings.extend(f"{path.name}: {finding}" for finding in _privacy_findings(content))
    return findings


def display_packet(packet: NotebookPacket) -> NotebookPacket | Path:
    try:
        from IPython.display import FileLink, display
    except ImportError:
        return packet.packet_dir

    for path in packet.source_paths():
        display(FileLink(str(path)))
    return packet


def redact_text(value: object) -> str:
    text = str(value)
    text = _ABSOLUTE_PATH_RE.sub("[local-path]", text)
    text = _HOME_PATH_RE.sub("[local-path]", text)
    text = _BEARER_RE.sub("Bearer [redacted-secret]", text)
    text = _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[redacted-secret]", text)
    text = _OPENAI_STYLE_KEY_RE.sub("[redacted-secret]", text)
    return text


def _resolve_packet_root(vault: Path, packet_root: Path | None) -> Path:
    if packet_root is None:
        return safe_child(vault, "notebook-packets")

    root = packet_root.expanduser().resolve()
    if root != vault and vault not in root.parents:
        raise ValueError("Notebook packet root must stay inside the vault")
    return root


def _packet_contents(
    packet: NotebookPacket,
    sanitized: AnalysisRecord,
    original: AnalysisRecord,
) -> dict[str, str]:
    source_contents = {
        "index.md": _index_markdown(sanitized, packet),
        "tables.csv": _tables_csv(sanitized),
        "report.html": render_dashboard(sanitized),
    }
    manifest = _manifest(packet, sanitized, original, _source_hashes(source_contents))
    return {
        **source_contents,
        "manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    }


def _sanitize_record(record: AnalysisRecord) -> AnalysisRecord:
    return replace(
        record,
        title=redact_text(record.title),
        summary=redact_text(record.summary),
        observations=[redact_text(item) for item in record.observations],
        actions=[redact_text(item) for item in record.actions],
        model=redact_text(record.model),
        source_image=_source_basename(record.source_image),
        raw={},
    )


def _source_basename(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).replace("\\", "/").rstrip("/")
    name = normalized.rsplit("/", 1)[-1].strip()
    if not name:
        return None
    safe_name = redact_text(name)
    if safe_name == "[local-path]" or "[redacted-secret]" in safe_name:
        return None
    return safe_name


def _index_markdown(record: AnalysisRecord, packet: NotebookPacket) -> str:
    observations = _markdown_list(record.observations)
    actions = _markdown_list(record.actions)
    source = record.source_image or "Not included"
    return (
        f"# {record.title}\n\n"
        f"{record.summary or 'No summary captured yet.'}\n\n"
        "## Observations\n\n"
        f"{observations}\n\n"
        "## Actions\n\n"
        f"{actions}\n\n"
        "## Packet\n\n"
        f"- Dashboard ID: `{packet.dashboard_id}`\n"
        f"- Model: `{record.model}`\n"
        f"- Created: `{record.created_at}`\n"
        f"- Source image filename: `{source}`\n"
        "- Raw logs, transcripts, absolute paths, and secrets are intentionally excluded.\n\n"
        "## NotebookLM Sources\n\n"
        "- `index.md`\n"
        "- `tables.csv`\n"
        "- `report.html`\n"
        "- `manifest.json`\n"
    )


def _tables_csv(record: AnalysisRecord) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["section", "item", "value"])
    writer.writerow(["meta", "title", record.title])
    writer.writerow(["meta", "summary", record.summary])
    writer.writerow(["meta", "model", record.model])
    writer.writerow(["meta", "source_image", record.source_image or ""])
    for index, item in enumerate(record.observations, start=1):
        writer.writerow(["observation", str(index), item])
    for index, item in enumerate(record.actions, start=1):
        writer.writerow(["action", str(index), item])
    return buffer.getvalue()


def _manifest(
    packet: NotebookPacket,
    sanitized: AnalysisRecord,
    original: AnalysisRecord,
    source_hashes: dict[str, str],
) -> dict[str, object]:
    return {
        "dashboard_id": packet.dashboard_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "redaction_policy_version": REDACTION_POLICY_VERSION,
        "sources": list(packet.sources),
        "source_sha256": source_hashes,
        "deny_sources": list(packet.deny_sources),
        "record": {
            "title": sanitized.title,
            "model": sanitized.model,
            "created_at": sanitized.created_at,
            "source_image_name": sanitized.source_image,
            "observation_count": len(sanitized.observations),
            "action_count": len(sanitized.actions),
            "raw_key_count": len(original.raw),
        },
        "privacy": {
            "raw_logs_included": False,
            "raw_transcripts_included": False,
            "absolute_source_paths_included": False,
            "secret_values_included": False,
        },
    }


def _markdown_list(items: list[str]) -> str:
    if not items:
        return "- None captured yet."
    return "\n".join(f"- {item}" for item in items)


def _source_hashes(contents: Mapping[str, str]) -> dict[str, str]:
    return {
        name: hashlib.sha256(content.encode("utf-8")).hexdigest()
        for name, content in sorted(contents.items())
    }


def _validate_packet_contents(contents: Mapping[str, str]) -> None:
    findings: list[str] = []
    for name in contents:
        if "/" in name or "\\" in name or name.startswith("."):
            findings.append(f"invalid packet file name: {name}")
        if any(fnmatch(name, pattern) for pattern in DEFAULT_DENY_SOURCES):
            findings.append(f"denied packet file name: {name}")
    for name, content in contents.items():
        findings.extend(f"{name}: {finding}" for finding in _privacy_findings(content))
    if findings:
        raise NotebookPacketError("; ".join(findings))


def _privacy_findings(content: str) -> list[str]:
    findings: list[str] = []
    if _ABSOLUTE_PATH_RE.search(content) or _HOME_PATH_RE.search(content):
        findings.append("contains a local absolute path")
    if (
        _BEARER_RE.search(content)
        or _SECRET_ASSIGNMENT_RE.search(content)
        or _OPENAI_STYLE_KEY_RE.search(content)
    ):
        findings.append("contains a likely secret")
    return findings
