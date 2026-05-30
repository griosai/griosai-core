from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .brain import AnalysisRecord, VAULT_DIRS, ensure_vault, safe_child, slugify, unique_path


LINEAGE_SCHEMA = "griosai.analysis-lineage.v1"
MAX_LINEAGE_MANIFEST_BYTES = 1_000_000
PRIVATE_FIELDS_OMITTED = (
    "title",
    "summary",
    "observations",
    "actions",
    "raw",
    "source_image_path",
)
FORBIDDEN_MANIFEST_KEYS = frozenset((*PRIVATE_FIELDS_OMITTED, "source_image"))


@dataclass(frozen=True)
class LineageFinding:
    severity: str
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }


@dataclass(frozen=True)
class LineageVerification:
    vault_dir: Path
    generated_at: str
    manifest_count: int
    artifact_count: int
    findings: tuple[LineageFinding, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "vault_dir": str(self.vault_dir),
            "generated_at": self.generated_at,
            "summary": {
                "manifests": self.manifest_count,
                "artifacts": self.artifact_count,
                "findings": {
                    "fail": sum(1 for item in self.findings if item.severity == "fail"),
                    "warn": sum(1 for item in self.findings if item.severity == "warn"),
                    "info": sum(1 for item in self.findings if item.severity == "info"),
                },
            },
            "findings": [item.as_dict() for item in self.findings],
        }


def analysis_id(record: AnalysisRecord) -> str:
    encoded = json.dumps(_canonical_record(record), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def lineage_manifest(
    vault_dir: Path,
    record: AnalysisRecord,
    *,
    artifacts: dict[str, Path],
    slug: str | None = None,
) -> dict[str, object]:
    vault = ensure_vault(vault_dir)
    timestamp = _now()
    analysis_slug = slugify(slug or record.title)
    return {
        "schema": LINEAGE_SCHEMA,
        "generated_at": timestamp,
        "analysis_id": analysis_id(record),
        "analysis": {
            "slug": analysis_slug,
            "model": record.model,
            "created_at": record.created_at,
            "source_image_name": _source_image_name(record.source_image),
            "summary_chars": len(record.summary),
            "observation_count": len(record.observations),
            "action_count": len(record.actions),
            "raw_field_count": len(record.raw),
        },
        "privacy": {
            "mode": "metadata-only",
            "omitted_fields": list(PRIVATE_FIELDS_OMITTED),
        },
        "artifacts": [
            _artifact_record(vault, kind=kind, path=path)
            for kind, path in sorted(artifacts.items())
        ],
    }


def write_lineage_manifest(
    vault_dir: Path,
    record: AnalysisRecord,
    *,
    artifacts: dict[str, Path],
    slug: str | None = None,
) -> Path:
    vault = ensure_vault(vault_dir)
    analysis_slug = slugify(slug or record.title)
    manifest = lineage_manifest(vault, record, artifacts=artifacts, slug=analysis_slug)
    path = unique_path(safe_child(vault, "lineage", f"{analysis_slug}.json"))
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def verify_lineage(vault_dir: Path) -> LineageVerification:
    vault = vault_dir.expanduser().resolve()
    findings: list[LineageFinding] = []
    manifest_count = 0
    artifact_count = 0

    if not vault.exists():
        return LineageVerification(
            vault_dir=vault,
            generated_at=_now(),
            manifest_count=0,
            artifact_count=0,
            findings=(
                LineageFinding("fail", "vault-missing", ".", f"vault does not exist: {vault}"),
            ),
        )
    if not vault.is_dir():
        return LineageVerification(
            vault_dir=vault,
            generated_at=_now(),
            manifest_count=0,
            artifact_count=0,
            findings=(
                LineageFinding("fail", "vault-not-directory", ".", f"vault is not a directory: {vault}"),
            ),
        )

    root = vault / "lineage"
    if root.is_symlink():
        findings.append(LineageFinding("fail", "lineage-symlink", "lineage", "lineage directory is a symlink"))
    elif not root.exists():
        findings.append(LineageFinding("warn", "lineage-missing", "lineage", "no lineage directory exists yet"))
    elif not root.is_dir():
        findings.append(LineageFinding("fail", "lineage-not-directory", "lineage", "lineage path is not a directory"))
    else:
        manifests = sorted(root.glob("*.json"))
        if not manifests:
            findings.append(LineageFinding("warn", "lineage-empty", "lineage", "no lineage manifests found"))
        for path in manifests:
            manifest_count += 1
            manifest_findings, artifacts = _verify_manifest(vault, path)
            findings.extend(manifest_findings)
            artifact_count += artifacts

    return LineageVerification(
        vault_dir=vault,
        generated_at=_now(),
        manifest_count=manifest_count,
        artifact_count=artifact_count,
        findings=tuple(findings),
    )


def lineage_exit_code(verification: LineageVerification) -> int:
    return 1 if any(item.severity == "fail" for item in verification.findings) else 0


def format_lineage_json(verification: LineageVerification) -> str:
    return json.dumps(verification.as_dict(), indent=2, sort_keys=True)


def format_lineage_text(verification: LineageVerification) -> str:
    data = verification.as_dict()
    summary = data["summary"]
    lines = [
        f"Vault: {data['vault_dir']}",
        f"Manifests: {summary['manifests']}",
        f"Artifacts: {summary['artifacts']}",
    ]
    if verification.findings:
        lines.append("Findings:")
        lines.extend(
            f"[{finding.severity.upper()}] {finding.code} {finding.path}: {finding.message}"
            for finding in verification.findings
        )
    else:
        lines.append("Findings: none")
    return "\n".join(lines)


def _verify_manifest(vault: Path, path: Path) -> tuple[list[LineageFinding], int]:
    relative = path.relative_to(vault).as_posix()
    findings: list[LineageFinding] = []
    artifact_count = 0
    if path.is_symlink():
        return [LineageFinding("fail", "manifest-symlink", relative, "lineage manifest is a symlink")], 0
    if path.stat().st_size > MAX_LINEAGE_MANIFEST_BYTES:
        return [LineageFinding("fail", "manifest-too-large", relative, "lineage manifest exceeds size limit")], 0
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [LineageFinding("fail", "manifest-invalid-json", relative, str(exc))], 0
    if not isinstance(parsed, dict):
        return [LineageFinding("fail", "manifest-not-object", relative, "lineage manifest must be a JSON object")], 0
    raw_keys = sorted(_forbidden_manifest_keys(parsed))
    if raw_keys:
        findings.append(
            LineageFinding(
                "fail",
                "manifest-raw-field",
                relative,
                f"lineage manifest contains raw private field keys: {', '.join(raw_keys)}",
            )
        )
    if parsed.get("schema") != LINEAGE_SCHEMA:
        findings.append(LineageFinding("fail", "manifest-schema", relative, "unsupported lineage schema"))
    if not isinstance(parsed.get("analysis_id"), str) or not parsed.get("analysis_id"):
        findings.append(LineageFinding("fail", "manifest-analysis-id", relative, "analysis_id is required"))
    privacy = parsed.get("privacy")
    if not isinstance(privacy, dict) or privacy.get("mode") != "metadata-only":
        findings.append(LineageFinding("fail", "manifest-privacy", relative, "privacy mode must be metadata-only"))
    artifacts = parsed.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        findings.append(LineageFinding("fail", "manifest-artifacts", relative, "at least one artifact is required"))
        return findings, 0
    for artifact in artifacts:
        artifact_count += 1
        findings.extend(_verify_artifact(vault, relative, artifact))
    return findings, artifact_count


def _verify_artifact(vault: Path, manifest_path: str, artifact: object) -> list[LineageFinding]:
    findings: list[LineageFinding] = []
    if not isinstance(artifact, dict):
        return [LineageFinding("fail", "artifact-not-object", manifest_path, "artifact entry must be an object")]
    raw_path = artifact.get("path")
    if not isinstance(raw_path, str):
        return [LineageFinding("fail", "artifact-path", manifest_path, "artifact path is required")]
    try:
        relative = _validate_relative_vault_path(raw_path)
    except ValueError as exc:
        return [LineageFinding("fail", "artifact-path", raw_path, str(exc))]
    target = vault.joinpath(*relative.parts)
    if target.is_symlink():
        findings.append(LineageFinding("fail", "artifact-symlink", raw_path, "artifact target is a symlink"))
        return findings
    if not target.is_file():
        findings.append(LineageFinding("fail", "artifact-missing", raw_path, "artifact target is missing"))
        return findings
    expected_size = artifact.get("size")
    if expected_size != target.stat().st_size:
        findings.append(LineageFinding("fail", "artifact-size", raw_path, "artifact size does not match"))
    expected_hash = artifact.get("sha256")
    if expected_hash != _sha256_file(target):
        findings.append(LineageFinding("fail", "artifact-sha256", raw_path, "artifact SHA-256 does not match"))
    return findings


def _artifact_record(vault: Path, *, kind: str, path: Path) -> dict[str, object]:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ValueError(f"Lineage artifact must not be a symlink: {candidate}")
    resolved = candidate.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Lineage artifact does not exist: {resolved}")
    try:
        relative = resolved.relative_to(vault)
    except ValueError as exc:
        raise ValueError(f"Lineage artifact must be inside the vault: {resolved}") from exc
    _validate_relative_vault_path(relative.as_posix())
    return {
        "kind": kind,
        "path": relative.as_posix(),
        "size": resolved.stat().st_size,
        "sha256": _sha256_file(resolved),
    }


def _validate_relative_vault_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("artifact path must be relative and stay inside the vault")
    if path.parts[0] not in VAULT_DIRS:
        raise ValueError("artifact path must start with a known vault directory")
    if path.parts[0] == "lineage":
        raise ValueError("lineage manifests must not claim other lineage manifests as artifacts")
    return path


def _canonical_record(record: AnalysisRecord) -> dict[str, object]:
    return {
        "title": record.title,
        "summary": record.summary,
        "observations": list(record.observations),
        "actions": list(record.actions),
        "model": record.model,
        "source_image": record.source_image,
        "raw": _json_safe(record.raw),
    }


def _json_safe(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return str(value)


def _forbidden_manifest_keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            text = str(key)
            if text in FORBIDDEN_MANIFEST_KEYS:
                found.add(text)
            found.update(_forbidden_manifest_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_forbidden_manifest_keys(item))
    return found


def _source_image_name(value: str | None) -> str | None:
    if not value:
        return None
    name = Path(value.replace("\\", "/")).name
    return name or None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
