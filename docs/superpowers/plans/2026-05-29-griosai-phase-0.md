# GriosAI Phase 0 Plan

## Goal

Create a new standalone Codex-ready git repo for GriosAI with a minimal
local-first brain, dashboard renderer, CLI, and localhost server.

## Scope

- New repo at `/Users/gustavorios/griosai`.
- Python package with stdlib-only core.
- Vault creation and safe writes.
- Static dashboard rendering.
- Optional Ollama vision adapter.
- Manual JSON analysis import.
- Local REST/dashboard server.
- Unit tests for filesystem safety, HTML escaping, non-clobbering writes, image
  validation, and HTTP mutation safety.

## Non-Goals

- No real credentials or secrets.
- No cloud provider implementation.
- No public deployment.
- No hardware automation.
- No migration of existing Obsidian or Claude data.

## Files

- `AGENTS.md`
- `README.md`
- `pyproject.toml`
- `src/griosai/*.py`
- `tests/test_*.py`
- `docs/spec/griosai-phase-0.md`

## Validation

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m griosai.cli sample --vault /tmp/griosai-vault
```

## Next Steps After Phase 0

- Add the notebook connector facade once the existing connector API is known.
- Add optional Obsidian Local REST API sync.
- Add a Tailscale setup guide/script.
- Add a credential broker before any cloud provider support.
