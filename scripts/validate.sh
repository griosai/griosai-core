#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"

cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

echo "==> unit tests"
"$PYTHON_BIN" -m unittest discover -s tests

echo "==> compileall"
"$PYTHON_BIN" -m compileall src/griosai

echo "==> whitespace diff check"
git diff --check

echo "==> openapi contract"
"$PYTHON_BIN" -m griosai.cli openapi >/dev/null

echo "==> analysis schema contract"
"$PYTHON_BIN" -m griosai.cli analysis-schema >/dev/null
"$PYTHON_BIN" -m griosai.cli validate-analysis --json-file examples/sample-analysis.json --json >/dev/null

echo "==> temporary vault setup"
TMPDIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

echo "==> cli expected-error smoke"
if "$PYTHON_BIN" -m griosai.cli add-analysis --vault "$TMPDIR/vault" --json-file "$TMPDIR/missing.json" 2>"$TMPDIR/cli-error.log"; then
  echo "Expected missing analysis JSON to fail." >&2
  exit 1
fi
grep -q '^error:' "$TMPDIR/cli-error.log"
if grep -q 'Traceback' "$TMPDIR/cli-error.log"; then
  echo "CLI expected-error path printed a traceback." >&2
  exit 1
fi

"$PYTHON_BIN" -m griosai.cli init --vault "$TMPDIR/vault" >/dev/null
"$PYTHON_BIN" -m griosai.cli sample --vault "$TMPDIR/vault" >/dev/null
"$PYTHON_BIN" -m griosai.cli vault-audit --vault "$TMPDIR/vault" --json >/dev/null
"$PYTHON_BIN" -m griosai.cli lineage-verify --vault "$TMPDIR/vault" --json >/dev/null

echo "==> backup restore smoke"
BACKUP_JSON="$("$PYTHON_BIN" -m griosai.cli backup --vault "$TMPDIR/vault" --output "$TMPDIR")"
printf '%s\n' "$BACKUP_JSON"
ARCHIVE_PATH="$(printf '%s' "$BACKUP_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["archive_path"])')"
"$PYTHON_BIN" -m griosai.cli verify-backup "$ARCHIVE_PATH" >/dev/null
"$PYTHON_BIN" -m griosai.cli restore "$ARCHIVE_PATH" --vault "$TMPDIR/restored" >/dev/null

echo "==> safety doctor smoke"
DOCTOR_JSON="$("$PYTHON_BIN" -m griosai.cli doctor --vault "$TMPDIR/vault" --repo . --json)"
printf '%s\n' "$DOCTOR_JSON"
printf '%s' "$DOCTOR_JSON" | "$PYTHON_BIN" -c 'import json, sys; data=json.load(sys.stdin); raise SystemExit(data["summary"]["fail"] != 0)'

echo "==> kubernetes manifest render"
if command -v kubectl >/dev/null 2>&1; then
  kubectl kustomize deploy/kubernetes/base >/dev/null
  kubectl kustomize deploy/kubernetes/mlflow >/dev/null
else
  echo "WARN: kubectl not found; skipped kustomize render"
fi

echo "==> secret pattern scan"
if command -v rg >/dev/null 2>&1; then
  if rg -n '1f[5]2|BEGIN CERTIFICAT[E]|gh[o]_|sk-[A-Za-z0-9]{16,}|Bearer [A-Za-z0-9._~+/=-]{16,}|super-[s]ecret-token' .; then
    echo "Secret-like pattern detected." >&2
    exit 1
  fi
else
  echo "WARN: rg not found; skipped secret scan"
fi

echo "==> validation complete"
