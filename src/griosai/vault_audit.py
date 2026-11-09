from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .brain import VAULT_DIRS
from .privacy import OPENAI_STYLE_KEY_RE, SECRET_VALUE_RE
from .vault_archive import MAX_BACKUP_FILE_BYTES


TEXT_SUFFIXES = {
    ".csv",
    ".html",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
}
MAX_SECRET_SCAN_BYTES = 1_000_000


@dataclass(frozen=True)
class VaultFinding:
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
class VaultFile:
    path: str
    directory: str
    size: int
    sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "directory": self.directory,
            "size": self.size,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class VaultAudit:
    vault_dir: Path
    generated_at: str
    files: tuple[VaultFile, ...]
    findings: tuple[VaultFinding, ...]

    def as_dict(self) -> dict[str, object]:
        by_dir = {
            directory: {
                "files": sum(1 for item in self.files if item.directory == directory),
                "bytes": sum(item.size for item in self.files if item.directory == directory),
            }
            for directory in VAULT_DIRS
        }
        finding_counts = {
            "fail": sum(1 for item in self.findings if item.severity == "fail"),
            "warn": sum(1 for item in self.findings if item.severity == "warn"),
            "info": sum(1 for item in self.findings if item.severity == "info"),
        }
        return {
            "vault_dir": str(self.vault_dir),
            "generated_at": self.generated_at,
            "summary": {
                "files": len(self.files),
                "bytes": sum(item.size for item in self.files),
                "directories": by_dir,
                "findings": finding_counts,
            },
            "files": [item.as_dict() for item in self.files],
            "findings": [item.as_dict() for item in self.findings],
        }


def audit_vault(vault_dir: Path) -> VaultAudit:
    vault = vault_dir.expanduser().resolve()
    findings: list[VaultFinding] = []
    files: list[VaultFile] = []

    if not vault.exists():
        return VaultAudit(
            vault_dir=vault,
            generated_at=_now(),
            files=(),
            findings=(
                VaultFinding("fail", "vault-missing", ".", f"vault does not exist: {vault}"),
            ),
        )
    if not vault.is_dir():
        return VaultAudit(
            vault_dir=vault,
            generated_at=_now(),
            files=(),
            findings=(
                VaultFinding("fail", "vault-not-directory", ".", f"vault is not a directory: {vault}"),
            ),
        )

    for directory in VAULT_DIRS:
        root = vault / directory
        if root.is_symlink():
            findings.append(
                VaultFinding("fail", "layout-symlink", directory, "vault directory is a symlink")
            )
            continue
        if not root.exists():
            findings.append(
                VaultFinding("fail", "layout-missing", directory, "expected vault directory is missing")
            )
            continue
        if not root.is_dir():
            findings.append(
                VaultFinding("fail", "layout-not-directory", directory, "expected vault path is not a directory")
            )
            continue

        for path in sorted(root.rglob("*")):
            relative = path.relative_to(vault).as_posix()
            if path.is_symlink():
                findings.append(
                    VaultFinding("fail", "file-symlink", relative, "vault file is a symlink")
                )
                continue
            if path.is_dir():
                continue
            if not path.is_file():
                findings.append(
                    VaultFinding("warn", "file-special", relative, "vault path is not a regular file")
                )
                continue
            size = path.stat().st_size
            if size > MAX_BACKUP_FILE_BYTES:
                findings.append(
                    VaultFinding(
                        "warn",
                        "file-too-large",
                        relative,
                        "file exceeds built-in backup single-file guardrail",
                    )
                )
            findings.extend(_secret_findings(path, relative, size))
            files.append(
                VaultFile(
                    path=relative,
                    directory=directory,
                    size=size,
                    sha256=_sha256_file(path),
                )
            )

    return VaultAudit(
        vault_dir=vault,
        generated_at=_now(),
        files=tuple(files),
        findings=tuple(findings),
    )


def audit_exit_code(audit: VaultAudit) -> int:
    return 1 if any(item.severity == "fail" for item in audit.findings) else 0


def format_audit_json(audit: VaultAudit) -> str:
    return json.dumps(audit.as_dict(), indent=2, sort_keys=True)


def format_audit_text(audit: VaultAudit) -> str:
    data = audit.as_dict()
    summary = data["summary"]
    lines = [
        f"Vault: {data['vault_dir']}",
        f"Files: {summary['files']}",
        f"Bytes: {summary['bytes']}",
    ]
    findings = audit.findings
    if findings:
        lines.append("Findings:")
        lines.extend(
            f"[{finding.severity.upper()}] {finding.code} {finding.path}: {finding.message}"
            for finding in findings
        )
    else:
        lines.append("Findings: none")
    return "\n".join(lines)


def _secret_findings(path: Path, relative: str, size: int) -> list[VaultFinding]:
    if path.suffix.lower() not in TEXT_SUFFIXES or size > MAX_SECRET_SCAN_BYTES:
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings: list[VaultFinding] = []
    if SECRET_VALUE_RE.search(text):
        findings.append(
            VaultFinding("warn", "secret-looking-assignment", relative, "text contains a secret-looking assignment")
        )
    if OPENAI_STYLE_KEY_RE.search(text):
        findings.append(
            VaultFinding("warn", "secret-looking-key", relative, "text contains an OpenAI-style key pattern")
        )
    return findings


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
