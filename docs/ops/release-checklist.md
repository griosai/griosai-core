# Release Checklist

Use this checklist before tagging, pushing, or demoing a release.

## Local Gate

```bash
./scripts/validate.sh
```

Required evidence:

- Unit tests pass.
- `compileall` passes.
- `git diff --check` passes.
- Backup/verify/restore CLI smoke passes.
- `griosai doctor` reports zero failures against a fresh vault.
- Kubernetes Kustomize renders pass when `kubectl` is available.
- Secret-pattern scan returns no findings.

## Manual Smoke

```bash
TMPDIR="$(mktemp -d)"
griosai init --vault "$TMPDIR/vault"
griosai sample --vault "$TMPDIR/vault"
griosai add-analysis --vault "$TMPDIR/vault" --json-file ./examples/sample-analysis.json
griosai notebook-packet --vault "$TMPDIR/vault" --json-file ./examples/sample-analysis.json
BACKUP_JSON="$(griosai backup --vault "$TMPDIR/vault" --output "$TMPDIR")"
ARCHIVE="$(printf '%s' "$BACKUP_JSON" | python3 -c 'import json, sys; print(json.load(sys.stdin)["archive_path"])')"
griosai verify-backup "$ARCHIVE"
griosai doctor --vault "$TMPDIR/vault" --repo .
```

Optional smoke tests:

- Start local Ollama and run `griosai analyze-image` on a vault image.
- Start Obsidian Local REST and run `griosai obsidian-sync`.
- Start local MLflow and run `griosai mlflow-log`.
- Build `Containerfile` and render Kubernetes manifests.

## Privacy Gate

- No `.env`, vault, `private/`, `mlruns/`, `mlflow.db`, token, or secret files
  are staged.
- No vault backup archives are staged.
- Notebook packets contain sanitized source files only.
- MLflow runs contain metadata only unless a separate raw-artifact decision is
  approved.
- Configured mutation tokens are not printed in logs.
- No public `NodePort`, `LoadBalancer`, or public Ingress is present unless the
  release explicitly adds reviewed public exposure.
- Kubernetes NetworkPolicies render and still match the intended private app,
  MLflow, DNS, and optional Ollama paths.

## Git Gate

```bash
git status --short
git log --oneline -5
```

Release commits should be intentional, small enough to review, and backed by
the validation output above.
