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
- Access: local HTTP server bound to `127.0.0.1`; phone access through
  Tailscale or trusted LAN only when explicitly requested.
- Mutation APIs: bearer-token protected, JSON-only, and constrained to vault
  image paths for server-triggered analysis.

## Non-Goals For Phase 0

- No cloud model provider defaults.
- No credential broker yet.
- No public tunnel.
- No Obsidian plugin dependency.
- No hardware-specific optimization.

## Later Tracks

- Notebook connector wrapper for existing notebook workflows.
- Obsidian Local REST API adapter, kept optional and localhost-only.
- Private phone companion flow over Tailscale.
- Hardware tiers: phone-sized companion first, base-station compute later.
- Scoped token broker before adding any cloud APIs.

## Safety Principles

- Local before cloud.
- Plain files before hidden stores.
- Short-lived scoped credentials before long-lived tokens.
- Localhost before LAN.
- Tailscale private serve before public exposure.
