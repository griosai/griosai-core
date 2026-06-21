# Release Checklist

Use this checklist before tagging, pushing, or demoing a release.

## Version And Changelog

- Choose the semantic version and update `pyproject.toml`.
- Update [CHANGELOG.md](../../CHANGELOG.md) with user-visible changes,
  migrations, security notes, and validation evidence.
- Confirm README, docs, issue templates, support, security, and governance files
  describe the current release posture.
- Confirm any optional adapter changes still leave the core CLI usable without
  Ollama, Obsidian, MLflow, Kubernetes, Tailscale, or cloud providers.

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
- Expected CLI failures return concise stderr output without Python tracebacks.

## Manual Smoke

```bash
TMPDIR="$(mktemp -d)"
griosai init --vault "$TMPDIR/vault"
griosai sample --vault "$TMPDIR/vault"
griosai analysis-schema >/dev/null
griosai validate-analysis --json-file ./examples/sample-analysis.json --json >/dev/null
griosai add-analysis --vault "$TMPDIR/vault" --json-file ./examples/sample-analysis.json
griosai notebook-packet --vault "$TMPDIR/vault" --json-file ./examples/sample-analysis.json
griosai vault-audit --vault "$TMPDIR/vault" --json >/dev/null
griosai lineage-verify --vault "$TMPDIR/vault" --json >/dev/null
griosai openapi >/dev/null
if griosai add-analysis --vault "$TMPDIR/vault" --json-file "$TMPDIR/missing.json" 2>"$TMPDIR/err.log"; then
  echo "expected missing input to fail" >&2
  exit 1
fi
grep -q '^error:' "$TMPDIR/err.log"
! grep -q 'Traceback' "$TMPDIR/err.log"
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

## Package Artifact Gate

```bash
python -m pip install -e ".[dev]"
rm -rf dist build
python -m build
python -m twine check dist/*
TMPDIR="$(mktemp -d)"
python -m venv "$TMPDIR/venv"
"$TMPDIR/venv/bin/python" -m pip install dist/*.whl
"$TMPDIR/venv/bin/griosai" analysis-schema >/dev/null
```

Artifact checks:

- Wheel and source distribution build from a clean tree.
- `twine check` passes.
- Fresh virtual environment can install the wheel.
- Installed CLI can print the analysis schema and run documented read-only
  commands.
- README links and local documentation references pass the test suite.

## Privacy Gate

- No `.env`, vault, `private/`, `mlruns/`, `mlflow.db`, token, or secret files
  are staged.
- No vault backup archives are staged.
- Analysis schema validation passes for every checked-in example payload.
- Vault audit has no fail-level findings before backup/export.
- Lineage verification has no fail-level findings before MLflow logging or
  external handoff.
- Notebook packets contain sanitized source files only.
- MLflow runs contain metadata only unless a separate raw-artifact decision is
  approved.
- Configured mutation tokens are not printed in logs.
- No public `NodePort`, `LoadBalancer`, or public Ingress is present unless the
  release explicitly adds reviewed public exposure.
- Kubernetes NetworkPolicies render and still match the intended private app,
  MLflow, DNS, and optional Ollama paths.
- The bundled MLflow tracker stays no-auth and private: no bearer token is wired
  into the in-cluster dashboard, and its only boundary is the ClusterIP Service
  plus the `mlflow-tracking-private` NetworkPolicy (see
  [kubernetes-mlflow.md](kubernetes-mlflow.md)).
- If the MLflow tracker holds data worth keeping, the opt-in backup CronJob
  (`deploy/kubernetes/mlflow/backup-cronjob.yaml`) or a `VolumeSnapshot`
  schedule is applied and a `mlflow.db` + artifacts restore has been verified
  (see [backup-restore.md](backup-restore.md)).

## Git Gate

```bash
git status --short
git log --oneline -5
```

Release commits should be intentional, small enough to review, and backed by
the validation output above.

## Publication Gate

- Create a signed tag when signing is available.
- Prefer PyPI trusted publishing from GitHub Actions before using long-lived
  upload tokens.
- Attach release notes, built artifacts, and validation evidence to the GitHub
  release.
- Publish any security advisory after the fixed release is available.
- Keep failed or yanked release notes explicit so users know what to avoid.
