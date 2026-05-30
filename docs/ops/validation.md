# Validation

`scripts/validate.sh` is the canonical local quality gate. CI runs the same
entrypoint across supported Python versions.

## What It Checks

- Python unit tests.
- Local Markdown links in README and docs.
- Python bytecode compilation for `src/griosai/`.
- Git whitespace errors through `git diff --check`.
- OpenAPI contract generation through `griosai openapi`.
- Analysis input schema generation and sample payload validation.
- CLI expected-error coverage for concise nonzero failures without tracebacks.
- Vault audit smoke test.
- Lineage manifest verification smoke test.
- Agent harness run, scorecard, outcome, usage metadata, comparison,
  sequential A/B decisioning, experiment power sizing, scheduled next-batch planning, paired schedule
  reporting, dependency-aware pipeline planning/advance, round-robin arena planning/reporting, independent judge-panel
  planning/reporting, cross-evidence leaderboard, reviewable config proposal,
  Pareto frontier evidence, parallel-plan, matrix-plan, suite-plan, paired
  suite-report, pre-dispatch preflight, operator hold/release, provider quarantine/unquarantine, automated circuit-breaker reporting, capacity planning, SLO gating, model-mix gating, sample-balance reporting, balanced claim selection, batch dispatch, capacity orchestration, operator cycle,
  bounded operator loop, batch ingest, heartbeat, retry, batch recovery,
  work-packet, merge, gate, quorum, adjudication, audit, reproducibility snapshot, artifact manifest,
  manifest verification, timeline, watchdog,
  budget, drift monitoring, readiness gate, drift-gated staged rollout plan,
  drift-gated rollout stage check,
  self-contained agent dashboard, metadata-only evolution loop, metadata-only agent memory, adaptive
  hard-case curriculum and focused rerun planning, allocation, lane-aware routing,
  suite/Pareto/budget/balance/drift-gated promotion/readiness/rollout/evolution, status,
  and improvement-loop smoke test.
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
