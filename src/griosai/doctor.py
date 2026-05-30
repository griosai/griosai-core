from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .brain import VAULT_DIRS
from .config import DEFAULT_HOST, GriosConfig
from .mlflow_client import (
    DEFAULT_MLFLOW_TRACKING_URI,
    bool_env,
    is_loopback_tracking_uri,
    validate_tracking_uri,
)
from .notebook import validate_notebook_packet
from .obsidian import DEFAULT_OBSIDIAN_URL, _validate_loopback_url


SECRET_VALUE_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[a-z0-9._~+/=-]{20,}"
)
OPENAI_STYLE_KEY_RE = re.compile(r"\bsk-[a-zA-Z0-9]{16,}\b")


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "message": self.message}


def run_doctor(
    *,
    vault_dir: Path | None = None,
    repo_dir: Path | None = None,
    environ: dict[str, str] | None = None,
) -> list[DoctorCheck]:
    env = environ if environ is not None else dict(os.environ)
    checks: list[DoctorCheck] = []
    checks.extend(_config_checks(vault_dir=vault_dir, environ=env))
    if repo_dir is not None:
        checks.extend(_repo_checks(repo_dir))
    if vault_dir is not None:
        checks.extend(_vault_checks(vault_dir))
    return checks


def doctor_exit_code(checks: Iterable[DoctorCheck]) -> int:
    return 1 if any(check.status == "fail" for check in checks) else 0


def format_doctor_text(checks: Iterable[DoctorCheck]) -> str:
    return "\n".join(
        f"[{check.status.upper()}] {check.name}: {check.message}" for check in checks
    )


def format_doctor_json(checks: Iterable[DoctorCheck]) -> str:
    items = [check.as_dict() for check in checks]
    summary = {
        "pass": sum(1 for item in items if item["status"] == "pass"),
        "warn": sum(1 for item in items if item["status"] == "warn"),
        "fail": sum(1 for item in items if item["status"] == "fail"),
    }
    return json.dumps({"summary": summary, "checks": items}, indent=2, sort_keys=True)


def _config_checks(*, vault_dir: Path | None, environ: dict[str, str]) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    config = GriosConfig.from_env(vault_dir=vault_dir, host=environ.get("GRIOSAI_HOST"))
    if config.host == DEFAULT_HOST:
        checks.append(DoctorCheck("host-default", "pass", "server host defaults to 127.0.0.1"))
    else:
        checks.append(
            DoctorCheck(
                "host-default",
                "warn",
                f"server host is {config.host}; confirm non-local exposure is intentional",
            )
        )

    api_token = environ.get("GRIOSAI_API_TOKEN", "").strip()
    if not api_token:
        checks.append(DoctorCheck("mutation-token", "pass", "server will generate a per-run token"))
    elif len(api_token) >= 24:
        checks.append(DoctorCheck("mutation-token", "pass", "configured mutation token length is acceptable"))
    else:
        checks.append(DoctorCheck("mutation-token", "fail", "configured mutation token is too short"))

    obsidian_url = environ.get("GRIOSAI_OBSIDIAN_URL", DEFAULT_OBSIDIAN_URL)
    try:
        _validate_loopback_url(obsidian_url)
    except ValueError as exc:
        checks.append(DoctorCheck("obsidian-url", "fail", str(exc)))
    else:
        checks.append(DoctorCheck("obsidian-url", "pass", "Obsidian URL is localhost-only"))

    tracking_uri = environ.get("GRIOSAI_MLFLOW_TRACKING_URI", DEFAULT_MLFLOW_TRACKING_URI)
    allow_remote_tracking = bool_env(environ.get("GRIOSAI_MLFLOW_ALLOW_REMOTE"), False)
    try:
        validate_tracking_uri(tracking_uri, allow_remote=allow_remote_tracking)
    except ValueError as exc:
        checks.append(DoctorCheck("mlflow-tracking-uri", "fail", str(exc)))
    else:
        if is_loopback_tracking_uri(tracking_uri):
            checks.append(DoctorCheck("mlflow-tracking-uri", "pass", "MLflow tracking defaults to localhost"))
        else:
            checks.append(
                DoctorCheck(
                    "mlflow-tracking-uri",
                    "warn",
                    "MLflow tracking is non-local and explicitly allowed",
                )
            )
    return checks


def _repo_checks(repo_dir: Path) -> list[DoctorCheck]:
    repo = repo_dir.expanduser().resolve()
    checks: list[DoctorCheck] = []
    gitignore = repo / ".gitignore"
    if gitignore.exists():
        text = gitignore.read_text(encoding="utf-8")
        missing = [item for item in ("GriosAI-vault/", "private/", "*.token") if item not in text]
        if missing:
            checks.append(DoctorCheck("gitignore", "warn", f"missing private patterns: {', '.join(missing)}"))
        else:
            checks.append(DoctorCheck("gitignore", "pass", "private vault and token patterns are ignored"))
    else:
        checks.append(DoctorCheck("gitignore", "fail", ".gitignore is missing"))

    env_example = repo / ".env.example"
    if not env_example.exists():
        checks.append(DoctorCheck("env-example", "warn", ".env.example is missing"))
    else:
        findings = _secret_findings(env_example.read_text(encoding="utf-8"))
        if findings:
            checks.append(DoctorCheck("env-example", "fail", "example env appears to contain a secret"))
        else:
            checks.append(DoctorCheck("env-example", "pass", ".env.example contains placeholders only"))
    return checks


def _vault_checks(vault_dir: Path) -> list[DoctorCheck]:
    vault = vault_dir.expanduser().resolve()
    checks: list[DoctorCheck] = []
    if not vault.exists():
        return [DoctorCheck("vault", "warn", f"vault does not exist yet: {vault}")]
    if not vault.is_dir():
        return [DoctorCheck("vault", "fail", f"vault path is not a directory: {vault}")]

    bad_dirs = []
    for name in VAULT_DIRS:
        path = vault / name
        if path.is_symlink():
            bad_dirs.append(f"{name} is a symlink")
        elif not path.is_dir():
            bad_dirs.append(f"{name} is missing")
    if bad_dirs:
        checks.append(DoctorCheck("vault-layout", "fail", "; ".join(bad_dirs)))
    else:
        checks.append(DoctorCheck("vault-layout", "pass", "expected vault directories exist"))

    packet_root = vault / "notebook-packets"
    packet_findings: list[str] = []
    if packet_root.is_dir():
        for packet_dir in sorted(item for item in packet_root.iterdir() if item.is_dir()):
            packet_findings.extend(
                f"{packet_dir.name}: {finding}" for finding in validate_notebook_packet(packet_dir)
            )
    if packet_findings:
        checks.append(DoctorCheck("notebook-packets", "fail", "; ".join(packet_findings[:5])))
    else:
        checks.append(DoctorCheck("notebook-packets", "pass", "notebook packets passed privacy validation"))
    return checks


def _secret_findings(text: str) -> list[str]:
    findings: list[str] = []
    if SECRET_VALUE_RE.search(text):
        findings.append("likely assignment secret")
    if OPENAI_STYLE_KEY_RE.search(text):
        findings.append("OpenAI-style key")
    return findings
