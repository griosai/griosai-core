from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .brain import VAULT_DIRS, ensure_vault, safe_child, unique_path


BACKUP_SCHEMA = "griosai.vault-backup.v1"
BACKUP_MANIFEST = "griosai-backup-manifest.json"
MAX_BACKUP_FILES = 100_000
MAX_BACKUP_FILE_BYTES = 100_000_000
MAX_BACKUP_TOTAL_BYTES = 2_000_000_000


class VaultArchiveError(RuntimeError):
    pass


@dataclass(frozen=True)
class BackupResult:
    archive_path: Path
    file_count: int
    skipped_count: int
    total_bytes: int

    def as_dict(self) -> dict[str, object]:
        return {
            "archive_path": str(self.archive_path),
            "file_count": self.file_count,
            "skipped_count": self.skipped_count,
            "total_bytes": self.total_bytes,
        }


@dataclass(frozen=True)
class RestoreResult:
    vault_dir: Path
    file_count: int
    total_bytes: int
    overwritten_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "vault_dir": str(self.vault_dir),
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "overwritten_count": self.overwritten_count,
        }


@dataclass(frozen=True)
class VerifyResult:
    archive_path: Path
    file_count: int
    total_bytes: int
    skipped_count: int
    ok: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "archive_path": str(self.archive_path),
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "skipped_count": self.skipped_count,
            "ok": self.ok,
        }


def backup_vault(
    vault_dir: Path,
    *,
    output_path: Path | None = None,
    overwrite: bool = False,
) -> BackupResult:
    vault = ensure_vault(vault_dir)
    destination = _backup_destination(vault, output_path=output_path, overwrite=overwrite)
    files, skipped = _collect_vault_files(vault)
    manifest = _manifest(vault, files=files, skipped=skipped)

    destination.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite else "x"
    try:
        with zipfile.ZipFile(destination, mode=mode, compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(BACKUP_MANIFEST, json.dumps(manifest, indent=2, sort_keys=True))
            for item in files:
                archive.write(item["path"], arcname=item["archive_path"])
    except FileExistsError:
        raise
    except Exception:
        if not overwrite and destination.exists():
            destination.unlink(missing_ok=True)
        raise

    return BackupResult(
        archive_path=destination,
        file_count=len(files),
        skipped_count=len(skipped),
        total_bytes=sum(int(item["size"]) for item in files),
    )


def verify_backup(archive_path: Path) -> VerifyResult:
    archive_file = archive_path.expanduser().resolve()
    if not archive_file.is_file():
        raise FileNotFoundError(f"Backup archive not found: {archive_file}")

    try:
        with zipfile.ZipFile(archive_file, mode="r") as archive:
            manifest = _read_manifest(archive)
            file_records = _validate_archive(archive, manifest)
            total_bytes = 0
            for record in file_records:
                with archive.open(record["path"], mode="r") as source:
                    data = source.read()
                digest = hashlib.sha256(data).hexdigest()
                if digest != record["sha256"]:
                    raise VaultArchiveError(f"Backup digest mismatch for {record['path']}")
                total_bytes += len(data)
    except zipfile.BadZipFile as exc:
        raise VaultArchiveError("Backup archive is not a valid zip file") from exc

    skipped = manifest.get("skipped", [])
    return VerifyResult(
        archive_path=archive_file,
        file_count=len(file_records),
        total_bytes=total_bytes,
        skipped_count=len(skipped) if isinstance(skipped, list) else 0,
    )


def restore_vault(
    archive_path: Path,
    *,
    vault_dir: Path,
    overwrite: bool = False,
) -> RestoreResult:
    archive_file = archive_path.expanduser().resolve()
    if not archive_file.is_file():
        raise FileNotFoundError(f"Backup archive not found: {archive_file}")

    vault = ensure_vault(vault_dir)
    try:
        with zipfile.ZipFile(archive_file, mode="r") as archive:
            manifest = _read_manifest(archive)
            file_records = _validate_archive(archive, manifest)
            _preflight_restore(vault, file_records, overwrite=overwrite)

            overwritten = 0
            total_bytes = 0
            for record in file_records:
                target = safe_child(vault, *_posix_parts(record["path"]))
                if target.exists():
                    overwritten += 1
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(record["path"], mode="r") as source:
                    data = source.read()
                digest = hashlib.sha256(data).hexdigest()
                if digest != record["sha256"]:
                    raise VaultArchiveError(f"Backup digest mismatch for {record['path']}")
                _atomic_write(target, data)
                total_bytes += len(data)
    except zipfile.BadZipFile as exc:
        raise VaultArchiveError("Backup archive is not a valid zip file") from exc

    return RestoreResult(
        vault_dir=vault,
        file_count=len(file_records),
        total_bytes=total_bytes,
        overwritten_count=overwritten,
    )


def _backup_destination(vault: Path, *, output_path: Path | None, overwrite: bool) -> Path:
    if output_path is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        candidate = vault.parent / f"griosai-vault-{timestamp}.zip"
    else:
        candidate = output_path.expanduser()
        if candidate.exists() and candidate.is_dir():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            candidate = candidate / f"griosai-vault-{timestamp}.zip"
        elif candidate.suffix.lower() != ".zip":
            candidate = candidate.with_suffix(".zip")
    destination = candidate.resolve()
    if destination == vault or vault in destination.parents:
        raise VaultArchiveError("Backup output must not be inside the selected vault")
    if overwrite:
        return destination
    return unique_path(destination)


def _collect_vault_files(vault: Path) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    files: list[dict[str, object]] = []
    skipped: list[dict[str, str]] = []
    total_bytes = 0

    for directory in VAULT_DIRS:
        root = safe_child(vault, directory)
        if root.is_symlink():
            skipped.append({"path": directory, "reason": "symlink"})
            continue
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(vault).as_posix()
            if path.is_symlink():
                skipped.append({"path": relative, "reason": "symlink"})
                continue
            if not path.is_file():
                continue
            size = path.stat().st_size
            if size > MAX_BACKUP_FILE_BYTES:
                skipped.append({"path": relative, "reason": "file-too-large"})
                continue
            total_bytes += size
            if len(files) >= MAX_BACKUP_FILES or total_bytes > MAX_BACKUP_TOTAL_BYTES:
                raise VaultArchiveError("Vault is too large for the built-in backup guardrails")
            files.append(
                {
                    "path": path,
                    "archive_path": relative,
                    "size": size,
                    "sha256": _sha256_file(path),
                }
            )
    return files, skipped


def _manifest(
    vault: Path,
    *,
    files: list[dict[str, object]],
    skipped: list[dict[str, str]],
) -> dict[str, object]:
    return {
        "schema": BACKUP_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_vault_name": vault.name,
        "vault_dirs": list(VAULT_DIRS),
        "files": [
            {
                "path": item["archive_path"],
                "size": item["size"],
                "sha256": item["sha256"],
            }
            for item in files
        ],
        "skipped": skipped,
    }


def _read_manifest(archive: zipfile.ZipFile) -> dict[str, Any]:
    try:
        with archive.open(BACKUP_MANIFEST, mode="r") as handle:
            parsed = json.loads(handle.read().decode("utf-8"))
    except KeyError as exc:
        raise VaultArchiveError("Backup archive is missing the GriosAI manifest") from exc
    except json.JSONDecodeError as exc:
        raise VaultArchiveError("Backup manifest is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise VaultArchiveError("Backup manifest must be a JSON object")
    if parsed.get("schema") != BACKUP_SCHEMA:
        raise VaultArchiveError("Backup manifest schema is not supported")
    return parsed


def _validate_archive(
    archive: zipfile.ZipFile,
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    raw_files = manifest.get("files")
    if not isinstance(raw_files, list):
        raise VaultArchiveError("Backup manifest files must be a list")
    if len(raw_files) > MAX_BACKUP_FILES:
        raise VaultArchiveError("Backup archive contains too many files")

    records: list[dict[str, Any]] = []
    expected_paths: set[str] = set()
    total_bytes = 0
    infos = {info.filename: info for info in archive.infolist()}

    for info in archive.infolist():
        name = info.filename.rstrip("/")
        if name == BACKUP_MANIFEST:
            continue
        _validate_archive_path(name)
        if _zipinfo_is_symlink(info):
            raise VaultArchiveError(f"Backup archive contains a symlink entry: {name}")

    for raw in raw_files:
        if not isinstance(raw, dict):
            raise VaultArchiveError("Backup manifest file records must be objects")
        path = str(raw.get("path") or "")
        _validate_archive_path(path)
        if path in expected_paths:
            raise VaultArchiveError(f"Backup manifest contains duplicate path: {path}")
        expected_paths.add(path)

        info = infos.get(path)
        if info is None:
            raise VaultArchiveError(f"Backup archive is missing file listed in manifest: {path}")
        if _zipinfo_is_symlink(info):
            raise VaultArchiveError(f"Backup archive contains a symlink entry: {path}")
        size = _required_int(raw, "size", path)
        if size != info.file_size:
            raise VaultArchiveError(f"Backup size mismatch for {path}")
        if size > MAX_BACKUP_FILE_BYTES:
            raise VaultArchiveError(f"Backup file is too large: {path}")
        total_bytes += size
        if total_bytes > MAX_BACKUP_TOTAL_BYTES:
            raise VaultArchiveError("Backup archive is too large")

        digest = raw.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise VaultArchiveError(f"Backup digest is invalid for {path}")
        records.append({"path": path, "size": size, "sha256": digest})

    allowed_paths = expected_paths | {BACKUP_MANIFEST}
    unexpected = [
        info.filename
        for info in archive.infolist()
        if not info.is_dir() and info.filename not in allowed_paths
    ]
    if unexpected:
        raise VaultArchiveError(f"Backup archive contains unexpected entries: {unexpected[0]}")
    return records


def _preflight_restore(
    vault: Path,
    records: list[dict[str, Any]],
    *,
    overwrite: bool,
) -> None:
    for record in records:
        target = safe_child(vault, *_posix_parts(record["path"]))
        if target.is_symlink():
            raise VaultArchiveError(f"Restore target is a symlink: {target}")
        if target.exists() and not target.is_file():
            raise VaultArchiveError(f"Restore target is not a regular file: {target}")
        if target.exists() and not overwrite:
            raise FileExistsError(f"Restore target already exists: {target}")


def _validate_archive_path(value: str) -> None:
    path = PurePosixPath(value)
    parts = path.parts
    if not value or path.is_absolute() or "\\" in value or ":" in value:
        raise VaultArchiveError(f"Backup path is not relative and portable: {value}")
    if any(part in {"", ".", ".."} for part in parts):
        raise VaultArchiveError(f"Backup path contains unsafe segments: {value}")
    if parts[0] not in VAULT_DIRS:
        raise VaultArchiveError(f"Backup path is outside the vault layout: {value}")


def _posix_parts(value: str) -> tuple[str, ...]:
    _validate_archive_path(value)
    return PurePosixPath(value).parts


def _required_int(raw: dict[str, Any], key: str, path: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or value < 0:
        raise VaultArchiveError(f"Backup {key} is invalid for {path}")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(data)
        os.replace(temp_path, path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def _zipinfo_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0o170000
    return mode == 0o120000
