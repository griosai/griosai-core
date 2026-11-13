STATUS: active
SUMMARY: Local-first personal AI brain and dashboards; preserve private vault data, optional adapters and localhost defaults.

# GriosAI — project instructions

Release: pushed main

## Purpose

GriosAI is a local-first personal AI brain and dashboard runner. The default
architecture keeps private data on the user's machine, uses local models before
cloud providers, and exposes dashboards only through localhost unless the user
explicitly opts into LAN, VPN, or Tailscale access.

## Core Rules

- Never commit real credentials, tokens, vault contents, customer data, or raw
  private screenshots.
- Never commit vault backup archives; they can contain private notes, images,
  dashboards, and notebook packets.
- Bind services to `127.0.0.1` by default. Public exposure must be an explicit
  user decision.
- Prefer plain files in a user-selected vault over hidden databases for notes,
  generated dashboards, and handoff artifacts.
- Treat Ollama, Tailscale, Obsidian, and cloud APIs as optional adapters. The
  core should run without them.
- Treat MLflow and Kubernetes as optional ops adapters. They must not become
  required for the local CLI, tests, or vault workflow.
- Keep generated HTML self-contained and avoid remote assets by default.
- Add tests for path safety, escaping, and any new filesystem writes.
- Run affected checks while developing; docs-only instruction changes use link and diff checks. Keep `./scripts/validate.sh` as the authoritative full release gate, run once on the Mac mini before release to main. Never run the full suite on the laptop.
- Keep Kubernetes services private by default. Public ingress, LoadBalancer, or
  NodePort exposure requires an explicit review and user decision.
- Keep Kubernetes NetworkPolicies aligned with app labels and documented
  service dependencies.
- Log only privacy-preserving metadata to MLflow unless the user explicitly
  approves artifact or raw-content tracking.

## Phase 0 Shape

- `src/griosai/analysis_schema.py`: analysis JSON contract and validator.
- `src/griosai/brain.py`: vault layout, markdown notes, safe paths.
- `src/griosai/broker.py`: runtime-only scoped credential lease scaffold.
- `src/griosai/dashboard.py`: static dashboard rendering.
- `src/griosai/doctor.py`: local safety/readiness checks.
- `src/griosai/mlflow_client.py`: optional metadata-only MLflow Tracking REST adapter.
- `src/griosai/notebook.py`: sanitized NotebookLM/notebook packet adapter.
- `src/griosai/obsidian.py`: optional localhost-only Obsidian Local REST adapter.
- `src/griosai/ollama_client.py`: optional local vision model calls.
- `src/griosai/openapi.py`: machine-readable local REST API contract.
- `src/griosai/lineage.py`: privacy-preserving artifact provenance manifests.
- `src/griosai/server.py`: local REST/dashboard server.
- `src/griosai/vault_archive.py`: safe vault backup and restore.
- `src/griosai/vault_audit.py`: read-only vault inventory and integrity report.
- `src/griosai/cli.py`: operator entrypoints.
- `scripts/validate.sh`: canonical local and CI validation gate.
