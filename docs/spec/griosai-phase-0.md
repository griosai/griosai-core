# GriosAI Phase 0 Spec

## Goal

Build the smallest useful GriosAI project first: a safe local brain that can
turn an image or manual analysis into a markdown note and a phone-readable HTML
dashboard without sending private data to a server.

## Default Architecture

- Brain: a plain-file vault, compatible with Obsidian and easy to back up.
- Eyes: optional local Ollama vision model, starting with `qwen2.5vl:7b`.
- Glue: Python package and CLI that a notebook connector can import.
- Notebook packets: sanitized Markdown, CSV, HTML, and manifest sources for
  NotebookLM-style import without exposing raw logs, local paths, or secrets.
- Dashboard: self-contained HTML written into the vault.
- Backup/restore: manifest-backed zip archives for the plain-file vault,
  with symlink skipping, digest verification, path validation, and
  non-clobbering restore by default.
- Vault audit: read-only inventory with relative paths, sizes, SHA-256 hashes,
  layout findings, and secret-looking text warnings.
- Obsidian sync: optional Local REST API adapter, localhost-only and
  token-authenticated.
- MLflow tracking: optional REST adapter that logs privacy-preserving metadata
  only, localhost-only unless remote tracking is explicitly allowed.
- Kubernetes: optional deployment manifests and container image definitions for
  private ClusterIP operation, PVC-backed vault storage, and NetworkPolicy
  guardrails.
- Validation: one local script and CI workflow run tests, compile checks,
  doctor smoke, manifest rendering, whitespace checks, and secret scanning.
- Safety doctor: local readiness checks for config, vault layout, packet
  privacy, and placeholder-only examples.
- Credential leases: runtime-only scoped lease scaffold before any cloud
  provider support.
- Access: local HTTP server bound to `127.0.0.1`; phone access through
  Tailscale or trusted LAN only when explicitly requested.
- API contract: OpenAPI document served at `/api/openapi.json` and printed by
  `griosai openapi`.
- Mutation APIs: bearer-token protected, JSON-only, and constrained to vault
  image paths for server-triggered analysis.

## Non-Goals For Phase 0

- No cloud model provider defaults.
- No persistent credential broker or cloud token store yet.
- No public tunnel.
- No Obsidian plugin dependency.
- No Kubernetes or MLflow dependency for the core local CLI.
- No raw-content, screenshot, or artifact uploads to MLflow by default.
- No automatic backup upload or cloud sync.
- No hardware-specific optimization.

## Later Tracks

- Notebook connector wrapper for existing notebook workflows.
- Tailscale setup guide/script.
- Private phone companion flow over Tailscale.
- Production MLflow backed by external database/object storage if shared
  tracking becomes required.
- Hardware tiers: phone-sized companion first, base-station compute later.
- Persistent credential broker before adding any cloud APIs.

## Safety Principles

- Local before cloud.
- Plain files before hidden stores.
- Short-lived scoped credentials before long-lived tokens.
- Localhost before LAN.
- Tailscale private serve before public exposure.
