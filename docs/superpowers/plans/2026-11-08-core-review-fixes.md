STATUS: IMPLEMENTED; AFFECTED CHECKS PASSED; DELTA REVIEW PENDING
SUMMARY: Fix the three independently confirmed Core523 review findings while preserving replay safety and private Kubernetes defaults.

# Core review fixes

## Goal

Recover real MLflow duplicate-name conflicts, honor selected Retry-After delays, and require backup placement beside the tracker.

## Scope

Start from `5237710d917dc30fcad07e15feb2d6e22c7fcf25` in the existing T329-owned isolated lane. Accept MLflow3.1 HTTP400 only long enough to classify `RESOURCE_ALREADY_EXISTS`; unrelated400 failures remain errors and legacy409 recovery remains supported. Jitter fallback backoff only. Add required hostname pod affinity excluding backup pods and explain backup-volume topology prerequisites.

## Non-goals

No new dependencies, live MLflow/cluster acceptance, deployment, full laptop suite, provider jobs, Mini, push or installation. Preserve all prior non-idempotent write protections and privacy/service policies.

## Files

- Modify `src/griosai/mlflow_client.py` and `tests/test_mlflow_client.py`.
- Modify `deploy/kubernetes/mlflow/backup-cronjob.yaml`, `docs/ops/kubernetes-mlflow.md`, and `tests/test_kubernetes_manifests.py`.
- Create this dated execution record. All other named files exist and were inspected.

## Risks and assumptions

MLflow's official3.1 error mapping uses400 for duplicate names; the HTTP status alone must never classify an unrelated400 as a conflict. Experiment creation is replay safe because its name is unique; run creation and batch metrics remain non-idempotent. RWO allows multiple pods on one node but does not place them. A required affinity term must match the deployed tracker and reject the backup's own labels. Backup PV topology must also support the tracker node: use a compatible bound volume or an appropriate WaitForFirstConsumer storage class. No live topology is assumed.

## Steps

1. Preserve523 and export its committed source externally for a pristine affected baseline.
2. Add real400/legacy409, unrelated400, commit-then-conflict and exact sleep regressions. Use local-only `kubectl patch --local=true` to parse the backup/tracker YAML into JSON for placement assertions; skip only this optional ops check when kubectl is absent.
3. Obtain root's single serial execution allocation before any checks. Run the two existing affected files on pristine523, overlay only the new test files on that export, and retain expected red results.
4. Apply narrow fixes, run those same two affected files on the candidate, inspect committed membership, and commit using ordinary hooks and individually staged paths.
5. Submit the pinned delta and logs for independent fresh review. Final current-main/release gates remain root-owned.

## Validation

Use the existing Python interpreter, bytecode disabled, with explicit `PYTHONPATH=src:tests`. Run only `python3 -m unittest test_mlflow_client test_kubernetes_manifests`. Record pristine source pin, test hashes, commands, exit codes and counts. The pristine source plus new tests must fail the realistic400, Retry-After and affinity cases; the candidate must pass including previous write-replay negatives. Local fixture HTTP servers and local YAML transformation are not remote acceptance.

Root allocated one serial window. Pristine523 passed34 tests in11.071s (exit0); the same source plus only the two new test files ran38 in12.411s and failed the expected two400 recoveries, two delay assertions and missing affinity (exit1). The fixed candidate passed38 in11.745s (exit0), including the local kubectl placement test with no skips. Exact logs and hashes are retained outside the checkout in the portfolio release evidence directory. All three processes closed; independent review of the resulting committed delta remains required.
