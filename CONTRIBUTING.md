# Contributing

GriosAI is local-first infrastructure. Preserve the default posture: private
vaults, localhost services, optional adapters, and no raw private data in git.

## Prerequisites

- Python 3.11 or newer. CI runs 3.11, 3.12, 3.13, and 3.14.
- `rg` is recommended for local searches and is used by the validation script
  when available.
- `kubectl` is optional. When present, validation renders the Kubernetes
  manifests; when absent, that smoke check is skipped with a warning.
- Optional adapter tools such as Ollama, Obsidian Local REST, MLflow, and
  Tailscale are not required for core development.

## Local Setup

```bash
git clone https://github.com/gustavorios/griosai.git
cd griosai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Required Validation

Run the project gate before committing:

```bash
./scripts/validate.sh
```

This runs unit tests, bytecode compilation, diff whitespace checks, a doctor
smoke test, Kubernetes manifest rendering when `kubectl` is available, and a
secret-pattern scan.

Focused checks are useful while iterating:

```bash
make test
make compile
make schema-smoke
make doctor-smoke
```

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
- Treat generated HTML as untrusted output: escape model/user content, keep it
  self-contained, and add regression tests for serving or rendering changes.
- Any new filesystem write needs path-safety tests, symlink behavior tests when
  relevant, and clear non-clobbering behavior unless overwrite is explicit.
- If documentation mentions a command, file, environment variable, or supported
  network posture, update the corresponding docs and tests in the same change.

## Issue Triage

- Bugs should include the command, expected behavior, actual behavior, platform,
  Python version, and whether the failure touches private data.
- Feature requests should state the privacy boundary: what data leaves the vault,
  what service receives it, and whether the adapter remains optional.
- Vulnerabilities must follow [SECURITY.md](SECURITY.md), not public issue
  discussion.
- Support questions belong in the support channels listed in [SUPPORT.md](SUPPORT.md).

## Pull Request Flow

1. Keep changes small enough to review and explain the privacy impact.
2. Add or update tests for changed behavior.
3. Update README/docs for user-visible commands, APIs, adapters, or defaults.
4. Run `./scripts/validate.sh` and paste the relevant output in the PR.
5. Confirm no vault archives, `.env` files, raw screenshots, or credentials are
   staged.

## Pull Request Checklist

- `./scripts/validate.sh` passes locally.
- Docs describe any new command, environment variable, or operator risk.
- New adapters have fake-server tests where practical.
- Public exposure, cloud usage, or raw-content export is explicitly justified.
