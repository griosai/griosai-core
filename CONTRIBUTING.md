# Contributing

GriosAI is local-first infrastructure. Preserve the default posture: private
vaults, localhost services, optional adapters, and no raw private data in git.

## Local Setup

```bash
cd /Users/gustavorios/griosai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Required Validation

Run the project gate before committing:

```bash
./scripts/validate.sh
```

This runs unit tests, bytecode compilation, diff whitespace checks, a doctor
smoke test, Kubernetes manifest rendering when `kubectl` is available, and a
secret-pattern scan.

## Engineering Rules

- Keep the core package dependency-light and usable without Ollama, Obsidian,
  MLflow, Kubernetes, Tailscale, or cloud providers.
- Add focused tests for any new filesystem write, network adapter, parser,
  safety check, or public endpoint.
- Keep generated dashboard HTML self-contained and escaped.
- Do not commit real vault contents, API keys, private screenshots, raw logs,
  MLflow run stores, or environment files.
- New remote integrations must be opt-in and documented with their privacy
  boundary.

## Pull Request Checklist

- `./scripts/validate.sh` passes locally.
- Docs describe any new command, environment variable, or operator risk.
- New adapters have fake-server tests where practical.
- Public exposure, cloud usage, or raw-content export is explicitly justified.
