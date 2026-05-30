# GriosAI Phase 0 Plan

## Goal

Create a new standalone Codex-ready git repo for GriosAI with a minimal
local-first brain, dashboard renderer, CLI, and localhost server.

## Scope

- Standalone Codex-ready repository for the GriosAI package.
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

This plan is archived as historical context. The current maintained roadmap and
operator documentation live in [the docs index](../../README.md), with active
release criteria in [the release checklist](../../ops/release-checklist.md).
