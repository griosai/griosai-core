from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .brain import AnalysisRecord, ensure_vault, slugify, write_analysis_note
from .broker import CredentialBroker
from .config import GriosConfig
from .dashboard import write_dashboard
from .doctor import doctor_exit_code, format_doctor_json, format_doctor_text, run_doctor
from .mlflow_client import MlflowConfig, log_analysis_to_mlflow
from .notebook import NotebookConnectorAdapter
from .obsidian import ObsidianConfig, publish_analysis_to_obsidian
from .ollama_client import DEFAULT_IMAGE_PROMPT, analyze_image
from .openapi import openapi_json
from .server import create_sample, run_server
from .vault_archive import backup_vault, restore_vault, verify_backup
from .vault_audit import audit_exit_code, audit_vault, format_audit_json, format_audit_text


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        vault = ensure_vault(Path(args.vault))
        print(f"Initialized GriosAI vault at {vault}")
        return 0
    if args.command == "sample":
        note, dashboard = create_sample(Path(args.vault))
        print(f"Wrote note: {note}")
        print(f"Wrote dashboard: {dashboard}")
        return 0
    if args.command == "analyze-image":
        config = GriosConfig.from_env(
            vault_dir=args.vault,
            ollama_url=args.ollama_url,
            vision_model=args.model,
        )
        record = analyze_image(
            Path(args.image),
            model=config.vision_model,
            ollama_url=config.ollama_url,
            prompt=args.prompt,
        )
        slug = slugify(args.slug or record.title)
        note = write_analysis_note(config.vault_dir, record, slug=slug)
        dashboard = write_dashboard(config.vault_dir, record, slug=slug)
        print(f"Wrote note: {note}")
        print(f"Wrote dashboard: {dashboard}")
        return 0
    if args.command == "add-analysis":
        payload = _load_json_payload(args.json_file)
        record = AnalysisRecord.from_mapping(payload, model="manual")
        slug = slugify(args.slug or record.title)
        note = write_analysis_note(Path(args.vault), record, slug=slug)
        dashboard = write_dashboard(Path(args.vault), record, slug=slug)
        print(f"Wrote note: {note}")
        print(f"Wrote dashboard: {dashboard}")
        return 0
    if args.command == "notebook-packet":
        payload = _load_json_payload(args.json_file)
        record = AnalysisRecord.from_mapping(payload, model="manual")
        packet_root = Path(args.packet_root) if args.packet_root else None
        adapter = NotebookConnectorAdapter(Path(args.vault), packet_root=packet_root)
        packet = adapter.write_packet(record, slug=args.slug)
        print(f"Wrote notebook packet: {packet.packet_dir}")
        print(json.dumps(packet.connector_payload(), indent=2))
        return 0
    if args.command == "obsidian-sync":
        payload = _load_json_payload(args.json_file)
        record = AnalysisRecord.from_mapping(payload, model="manual")
        verify_tls = False if args.insecure_skip_tls_verify else None
        result = publish_analysis_to_obsidian(
            ObsidianConfig.from_env(
                url=args.obsidian_url,
                api_key=args.obsidian_api_key,
                verify_tls=verify_tls,
            ),
            record,
            folder=args.folder,
            slug=args.slug,
            overwrite=args.overwrite,
        )
        action = "Replaced" if result.replaced else "Wrote"
        print(f"{action} Obsidian note: {result.path}")
        return 0
    if args.command == "mlflow-log":
        payload = _load_json_payload(args.json_file)
        record = AnalysisRecord.from_mapping(payload, model="manual")
        result = log_analysis_to_mlflow(
            MlflowConfig.from_env(
                tracking_uri=args.tracking_uri,
                experiment_name=args.experiment,
                tracking_token=args.tracking_token,
                allow_remote=True if args.allow_remote_tracking else None,
            ),
            record,
            slug=args.slug,
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0
    if args.command == "backup":
        result = backup_vault(
            Path(args.vault),
            output_path=Path(args.output) if args.output else None,
            overwrite=args.overwrite,
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0
    if args.command == "restore":
        result = restore_vault(
            Path(args.archive),
            vault_dir=Path(args.vault),
            overwrite=args.overwrite,
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0
    if args.command == "verify-backup":
        result = verify_backup(Path(args.archive))
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0
    if args.command == "openapi":
        print(openapi_json())
        return 0
    if args.command == "credential-lease":
        lease = CredentialBroker().issue_env_lease(
            secret_name=args.secret_name,
            env_var=args.env_var,
            scopes=tuple(args.scope),
            client_id=args.client_id,
            ttl_seconds=args.ttl_seconds,
        )
        print(json.dumps(lease.audit_record(), indent=2, sort_keys=True))
        return 0
    if args.command == "doctor":
        checks = run_doctor(
            vault_dir=Path(args.vault) if args.vault else None,
            repo_dir=Path(args.repo) if args.repo else None,
        )
        print(format_doctor_json(checks) if args.json else format_doctor_text(checks))
        return doctor_exit_code(checks)
    if args.command == "vault-audit":
        audit = audit_vault(Path(args.vault))
        print(format_audit_json(audit) if args.json else format_audit_text(audit))
        return audit_exit_code(audit)
    if args.command == "serve":
        config = GriosConfig.from_env(
            vault_dir=args.vault,
            host=args.host,
            port=args.port,
            ollama_url=args.ollama_url,
            vision_model=args.model,
            api_token=args.api_token,
            allowed_hosts=tuple(args.allow_host) if args.allow_host else None,
        )
        run_server(config)
        return 0
    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="griosai")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create the local vault layout")
    init.add_argument("--vault", required=True, help="Vault directory")

    sample = subparsers.add_parser("sample", help="Write a sample dashboard")
    sample.add_argument("--vault", required=True, help="Vault directory")

    analyze = subparsers.add_parser("analyze-image", help="Analyze an image through local Ollama")
    analyze.add_argument("image", help="Image path")
    analyze.add_argument("--vault", required=True, help="Vault directory")
    analyze.add_argument("--model", default=None, help="Ollama vision model")
    analyze.add_argument("--ollama-url", default=None, help="Ollama base URL")
    analyze.add_argument("--prompt", default=DEFAULT_IMAGE_PROMPT, help="Vision prompt")
    analyze.add_argument("--slug", default=None, help="Output slug")

    add_analysis = subparsers.add_parser("add-analysis", help="Import manual analysis JSON")
    add_analysis.add_argument("--vault", required=True, help="Vault directory")
    add_analysis.add_argument(
        "--json-file",
        default="-",
        help="JSON file to import, or '-' for stdin",
    )
    add_analysis.add_argument("--slug", default=None, help="Output slug")

    notebook = subparsers.add_parser(
        "notebook-packet",
        help="Create a sanitized NotebookLM-ready source packet",
    )
    notebook.add_argument("--vault", required=True, help="Vault directory")
    notebook.add_argument(
        "--json-file",
        default="-",
        help="Analysis JSON file to packetize, or '-' for stdin",
    )
    notebook.add_argument("--slug", default=None, help="Packet slug")
    notebook.add_argument(
        "--packet-root",
        default=None,
        help="Optional packet root inside the selected vault",
    )

    obsidian = subparsers.add_parser(
        "obsidian-sync",
        help="Write an analysis note through Obsidian Local REST API",
    )
    obsidian.add_argument(
        "--json-file",
        default="-",
        help="Analysis JSON file to sync, or '-' for stdin",
    )
    obsidian.add_argument(
        "--folder",
        default="GriosAI/notes",
        help="Relative Obsidian folder for synced notes",
    )
    obsidian.add_argument("--slug", default=None, help="Output slug")
    obsidian.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the existing Obsidian note instead of allocating a unique path",
    )
    obsidian.add_argument("--obsidian-url", default=None, help="Local Obsidian REST URL")
    obsidian.add_argument("--obsidian-api-key", default=None, help="Local Obsidian REST API key")
    obsidian.add_argument(
        "--insecure-skip-tls-verify",
        action="store_true",
        help="Allow a localhost self-signed Obsidian certificate",
    )

    mlflow = subparsers.add_parser(
        "mlflow-log",
        help="Log privacy-preserving analysis metadata to an MLflow Tracking server",
    )
    mlflow.add_argument(
        "--json-file",
        default="-",
        help="Analysis JSON file to track, or '-' for stdin",
    )
    mlflow.add_argument("--slug", default=None, help="Run slug")
    mlflow.add_argument("--tracking-uri", default=None, help="MLflow Tracking server URI")
    mlflow.add_argument("--experiment", default=None, help="MLflow experiment name")
    mlflow.add_argument(
        "--tracking-token",
        default=None,
        help="Optional bearer token for an authenticated MLflow proxy",
    )
    mlflow.add_argument(
        "--allow-remote-tracking",
        action="store_true",
        help="Allow non-localhost MLflow Tracking URIs",
    )

    backup = subparsers.add_parser(
        "backup",
        help="Create a safe zip backup of the selected vault",
    )
    backup.add_argument("--vault", required=True, help="Vault directory")
    backup.add_argument(
        "--output",
        default=None,
        help="Output zip file or directory; defaults to the vault parent",
    )
    backup.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the exact output archive path instead of allocating a unique path",
    )

    restore = subparsers.add_parser(
        "restore",
        help="Restore a GriosAI vault zip backup",
    )
    restore.add_argument("archive", help="Backup zip archive")
    restore.add_argument("--vault", required=True, help="Restore destination vault directory")
    restore.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing restore targets instead of failing",
    )

    verify_backup_parser = subparsers.add_parser(
        "verify-backup",
        help="Verify a GriosAI vault zip backup without restoring it",
    )
    verify_backup_parser.add_argument("archive", help="Backup zip archive")

    subparsers.add_parser("openapi", help="Print the local REST OpenAPI contract")

    lease = subparsers.add_parser(
        "credential-lease",
        help="Validate a scoped runtime secret lease without printing the secret",
    )
    lease.add_argument("--secret-name", required=True, help="Human-readable secret handle")
    lease.add_argument("--env-var", required=True, help="Environment variable containing the secret")
    lease.add_argument(
        "--scope",
        action="append",
        required=True,
        help="Allowed action scope, for example obsidian:write",
    )
    lease.add_argument("--client-id", default="griosai-cli", help="Lease client identifier")
    lease.add_argument("--ttl-seconds", type=int, default=900, help="Lease TTL, max 3600 seconds")

    doctor = subparsers.add_parser("doctor", help="Run local safety and readiness checks")
    doctor.add_argument("--vault", default=None, help="Optional vault directory to inspect")
    doctor.add_argument("--repo", default=None, help="Optional repository directory to inspect")
    doctor.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    vault_audit = subparsers.add_parser(
        "vault-audit",
        help="Inventory and integrity-check a GriosAI vault without reading raw content into output",
    )
    vault_audit.add_argument("--vault", required=True, help="Vault directory")
    vault_audit.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    serve = subparsers.add_parser("serve", help="Run the local dashboard server")
    serve.add_argument("--vault", required=True, help="Vault directory")
    serve.add_argument("--host", default=None, help="Bind host; defaults to 127.0.0.1")
    serve.add_argument("--port", type=int, default=None, help="Bind port; defaults to 8765")
    serve.add_argument("--model", default=None, help="Ollama vision model")
    serve.add_argument("--ollama-url", default=None, help="Ollama base URL")
    serve.add_argument("--api-token", default=None, help="Bearer token for mutation APIs")
    serve.add_argument(
        "--allow-host",
        action="append",
        default=[],
        help="Additional allowed Host/Origin hostname for private proxies",
    )

    return parser


def _load_json_payload(path: str) -> dict[str, object]:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("analysis JSON must be an object")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
