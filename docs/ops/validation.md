# Validation

`scripts/validate.sh` is the canonical local quality gate. CI runs the same
entrypoint across supported Python versions.

## What It Checks

- Python unit tests.
- Python bytecode compilation for `src/griosai/`.
- Git whitespace errors through `git diff --check`.
- OpenAPI contract generation through `griosai openapi`.
- Analysis input schema generation and sample payload validation.
- Vault audit smoke test.
- Lineage manifest verification smoke test.
- CLI backup, verify-backup, and restore smoke test.
- `griosai doctor` against a fresh vault and this repo.
- Kubernetes Kustomize rendering when `kubectl` is installed.
- Secret-like patterns with `rg` when ripgrep is installed.

## Usage

```bash
./scripts/validate.sh
```

The script is intentionally dependency-light. Missing `kubectl` or `rg` prints a
warning so the core local Python gate can still run on minimal machines. For a
release-quality run, install both tools and confirm their checks execute.
