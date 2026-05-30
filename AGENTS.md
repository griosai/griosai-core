# GriosAI Codex Instructions

## Purpose

GriosAI is a local-first personal AI brain and dashboard runner. The default
architecture keeps private data on the user's machine, uses local models before
cloud providers, and exposes dashboards only through localhost unless the user
explicitly opts into LAN, VPN, or Tailscale access.

## Core Rules

- Never commit real credentials, tokens, vault contents, customer data, or raw
  private screenshots.
- Bind services to `127.0.0.1` by default. Public exposure must be an explicit
  user decision.
- Prefer plain files in a user-selected vault over hidden databases for notes,
  generated dashboards, and handoff artifacts.
- Treat Ollama, Tailscale, Obsidian, and cloud APIs as optional adapters. The
  core should run without them.
- Keep generated HTML self-contained and avoid remote assets by default.
- Add tests for path safety, escaping, and any new filesystem writes.

## Phase 0 Shape

- `src/griosai/brain.py`: vault layout, markdown notes, safe paths.
- `src/griosai/dashboard.py`: static dashboard rendering.
- `src/griosai/ollama_client.py`: optional local vision model calls.
- `src/griosai/server.py`: local REST/dashboard server.
- `src/griosai/cli.py`: operator entrypoints.

