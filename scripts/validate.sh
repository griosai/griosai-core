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

echo "==> agent harness smoke"
AGENT_RUN_JSON="$("$PYTHON_BIN" -m griosai.cli agent-run --vault "$TMPDIR/vault" --config-file examples/agent-experiment.json --subject validation-smoke --json)"
printf '%s\n' "$AGENT_RUN_JSON"
AGENT_RUN_ID="$(printf '%s' "$AGENT_RUN_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["run_id"])')"
"$PYTHON_BIN" -m griosai.cli agent-score --vault "$TMPDIR/vault" --run-id "$AGENT_RUN_ID" --scores-json '{"correctness": 0.8, "safety": 1, "efficiency": 0.7}' --usage-json '{"prompt_tokens": 100, "completion_tokens": 50, "latency_ms": 750, "cost_usd": 0.01}' --json >/dev/null
AGENT_RESULTS_FILE="$TMPDIR/agent-results.json"
"$PYTHON_BIN" - "$AGENT_RUN_ID" "$AGENT_RESULTS_FILE" <<'PY'
import json
import sys

run_id, path = sys.argv[1], sys.argv[2]
payload = {
    "results": [
        {
            "run_id": run_id,
            "status": "succeeded",
            "metrics": {"quality": 0.82},
            "usage": {"total_tokens": 140, "latency_ms": 700, "cost_usd": 0.01},
        }
    ]
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
PY
"$PYTHON_BIN" -m griosai.cli agent-ingest --vault "$TMPDIR/vault" --results-file "$AGENT_RESULTS_FILE" --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-retry --vault "$TMPDIR/vault" --run-id "$AGENT_RUN_ID" --reason validation_retry --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-circuit --vault "$TMPDIR/vault" --experiment cross-model-agent --group-by provider --min-outcomes 1 --max-failure-rate 1 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-compare --vault "$TMPDIR/vault" --experiment cross-model-agent --min-samples-per-variant 1 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-improve --vault "$TMPDIR/vault" --experiment cross-model-agent --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-memory --vault "$TMPDIR/vault" --experiment cross-model-agent --min-trials-per-variant 1 --max-lessons 8 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-curriculum --vault "$TMPDIR/vault" --experiment cross-model-agent --metric-threshold 0.8 --max-cases 8 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-allocate --vault "$TMPDIR/vault" --experiment cross-model-agent --strategy ucb1 --min-trials-per-variant 1 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-promote --vault "$TMPDIR/vault" --experiment cross-model-agent --min-trials-per-variant 1 --json >/dev/null
AGENT_MATRIX_JSON="$("$PYTHON_BIN" -m griosai.cli agent-matrix --vault "$TMPDIR/vault" --config-file examples/agent-experiment.json --subject validation-matrix --lanes scout,reviewer --json)"
printf '%s\n' "$AGENT_MATRIX_JSON" | "$PYTHON_BIN" -c 'import json, sys; data=json.load(sys.stdin); raise SystemExit(data["run_count"] != 6)'
AGENT_PIPELINE_JSON="$("$PYTHON_BIN" -m griosai.cli agent-pipeline --vault "$TMPDIR/vault" --config-file examples/agent-experiment.json --pipeline-file examples/agent-pipeline.json --subject-prefix validation-pipeline --json)"
AGENT_PIPELINE_ID="$(printf '%s' "$AGENT_PIPELINE_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["pipeline_id"])')"
AGENT_PIPELINE_RUNS="$(printf '%s' "$AGENT_PIPELINE_JSON" | "$PYTHON_BIN" -c 'import json, sys; data=json.load(sys.stdin); print("\n".join(run["run_id"] for plan in data["plans"] for run in plan["runs"]))')"
while read -r RUN_ID; do
  [ -z "$RUN_ID" ] && continue
  "$PYTHON_BIN" -m griosai.cli agent-outcome --vault "$TMPDIR/vault" --run-id "$RUN_ID" --status succeeded --metrics-json '{"quality": 0.8}' --json >/dev/null
done <<< "$AGENT_PIPELINE_RUNS"
"$PYTHON_BIN" -m griosai.cli agent-pipeline-advance --vault "$TMPDIR/vault" --pipeline-id "$AGENT_PIPELINE_ID" --json >/dev/null
AGENT_SUITE_JSON="$("$PYTHON_BIN" -m griosai.cli agent-suite --vault "$TMPDIR/vault" --config-file examples/agent-experiment.json --suite-file examples/agent-suite.json --subject-prefix validation-suite --lanes scout,reviewer --json)"
printf '%s\n' "$AGENT_SUITE_JSON" | "$PYTHON_BIN" -c 'import json, sys; data=json.load(sys.stdin); raise SystemExit(data["case_count"] != 3 or data["run_count"] != 18)'
AGENT_SUITE_ID="$(printf '%s' "$AGENT_SUITE_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["suite_id"])')"
AGENT_HOLD_JSON="$("$PYTHON_BIN" -m griosai.cli agent-hold --vault "$TMPDIR/vault" --experiment cross-model-agent --scopes dispatch --reason validation_hold --json)"
AGENT_HOLD_ID="$(printf '%s' "$AGENT_HOLD_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["hold_id"])')"
if "$PYTHON_BIN" -m griosai.cli agent-preflight --vault "$TMPDIR/vault" --suite-id "$AGENT_SUITE_ID" --require-cross-model --require-lane-coverage --require-variant-coverage --max-pending-skew 0 --json >/dev/null 2>&1; then
  echo "expected agent-preflight to fail while validation hold is active" >&2
  exit 1
fi
"$PYTHON_BIN" -m griosai.cli agent-release --vault "$TMPDIR/vault" --experiment cross-model-agent --hold-id "$AGENT_HOLD_ID" --reason validation_release --json >/dev/null
AGENT_QUARANTINE_JSON="$("$PYTHON_BIN" -m griosai.cli agent-quarantine --vault "$TMPDIR/vault" --experiment cross-model-agent --providers openai --reason validation_quarantine --json)"
AGENT_QUARANTINE_ID="$(printf '%s' "$AGENT_QUARANTINE_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["quarantine_id"])')"
"$PYTHON_BIN" -m griosai.cli agent-unquarantine --vault "$TMPDIR/vault" --experiment cross-model-agent --quarantine-id "$AGENT_QUARANTINE_ID" --reason validation_unquarantine --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-preflight --vault "$TMPDIR/vault" --suite-id "$AGENT_SUITE_ID" --require-cross-model --require-lane-coverage --require-variant-coverage --max-pending-skew 0 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-capacity --vault "$TMPDIR/vault" --suite-id "$AGENT_SUITE_ID" --max-concurrency 4 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-slo --vault "$TMPDIR/vault" --suite-id "$AGENT_SUITE_ID" --min-completion-rate 0 --max-failure-rate 1 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-mix --vault "$TMPDIR/vault" --experiment cross-model-agent --require-local-provider --max-scheduled-provider-share 1 --max-completed-provider-share 1 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-orchestrate --vault "$TMPDIR/vault" --suite-id "$AGENT_SUITE_ID" --client-prefix validation-orchestrate --max-concurrency 3 --batch-size 2 --ttl-seconds 120 --claim-strategy lane-variant-balanced --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-cycle --vault "$TMPDIR/vault" --suite-id "$AGENT_SUITE_ID" --client-prefix validation-cycle --max-concurrency 4 --batch-size 2 --skip-recovery --dashboard-limit 40 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-loop --vault "$TMPDIR/vault" --suite-id "$AGENT_SUITE_ID" --client-prefix validation-loop --max-concurrency 4 --batch-size 2 --max-cycles 1 --stop-after-idle-cycles 1 --skip-recovery --dashboard-limit 40 --json >/dev/null
AGENT_SUITE_RUNS="$(printf '%s' "$AGENT_SUITE_JSON" | "$PYTHON_BIN" -c 'import json, sys; data=json.load(sys.stdin); print("\n".join("{} {}".format(run["run_id"], run["variant_id"]) for plan in data["plans"] for run in plan["runs"]))')"
while read -r RUN_ID VARIANT_ID; do
  [ -z "$RUN_ID" ] && continue
  case "$VARIANT_ID" in
    openai-backup) QUALITY="0.95" ;;
    claude-primary) QUALITY="0.75" ;;
    *) QUALITY="0.65" ;;
  esac
  "$PYTHON_BIN" -m griosai.cli agent-outcome --vault "$TMPDIR/vault" --run-id "$RUN_ID" --status succeeded --metrics-json "{\"quality\": $QUALITY}" --usage-json '{"total_tokens": 120, "latency_ms": 900, "cost_usd": 0.02}' --json >/dev/null
done <<< "$AGENT_SUITE_RUNS"
AGENT_SUITE_FIRST_PLAN_ID="$(printf '%s' "$AGENT_SUITE_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["plans"][0]["plan_id"])')"
"$PYTHON_BIN" -m griosai.cli agent-quorum --vault "$TMPDIR/vault" --plan-id "$AGENT_SUITE_FIRST_PLAN_ID" --min-agreement-ratio 1 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-suite-report --vault "$TMPDIR/vault" --suite-id "$AGENT_SUITE_ID" --min-completed-ratio 1 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-balance --vault "$TMPDIR/vault" --experiment cross-model-agent --suite-id "$AGENT_SUITE_ID" --dimensions variant,lane,case --min-count-per-cell 1 --max-skew 0 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-curriculum --vault "$TMPDIR/vault" --experiment cross-model-agent --metric-threshold 0.85 --max-cases 8 --json >/dev/null
AGENT_JUDGE_PANEL_JSON="$("$PYTHON_BIN" -m griosai.cli agent-judge-panel --vault "$TMPDIR/vault" --config-file examples/agent-experiment.json --plan-id "$AGENT_SUITE_FIRST_PLAN_ID" --judge-variants claude-primary,openai-backup --max-runs 8 --json)"
AGENT_JUDGE_PANEL_ID="$(printf '%s' "$AGENT_JUDGE_PANEL_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["panel_id"])')"
"$PYTHON_BIN" -m griosai.cli agent-judge-report --vault "$TMPDIR/vault" --panel-id "$AGENT_JUDGE_PANEL_ID" --json >/dev/null
AGENT_ARENA_JSON="$("$PYTHON_BIN" -m griosai.cli agent-arena --vault "$TMPDIR/vault" --config-file examples/agent-experiment.json --subject validation-arena --lanes reviewer --max-runs 6 --json)"
AGENT_ARENA_ID="$(printf '%s' "$AGENT_ARENA_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["arena_id"])')"
"$PYTHON_BIN" -m griosai.cli agent-arena-report --vault "$TMPDIR/vault" --arena-id "$AGENT_ARENA_ID" --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-compare --vault "$TMPDIR/vault" --experiment cross-model-agent --min-samples-per-variant 1 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-decision --vault "$TMPDIR/vault" --experiment cross-model-agent --baseline-variant claude-primary --candidate-variant openai-backup --min-samples-per-variant 1 --min-delta 0.01 --confidence-threshold 0.5 --max-cost-usd 10 --max-total-tokens 100000 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-power --vault "$TMPDIR/vault" --experiment cross-model-agent --baseline-variant claude-primary --min-detectable-effect 0.01 --fallback-stddev 0.1 --max-cost-usd 10 --max-total-tokens 100000 --json >/dev/null
AGENT_SCHEDULE_JSON="$("$PYTHON_BIN" -m griosai.cli agent-schedule --vault "$TMPDIR/vault" --experiment cross-model-agent --subject validation-schedule --lanes scout,reviewer --max-runs 4 --json)"
AGENT_SCHEDULE_ID="$(printf '%s' "$AGENT_SCHEDULE_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["schedule_id"])')"
"$PYTHON_BIN" -m griosai.cli agent-schedule-report --vault "$TMPDIR/vault" --schedule-id "$AGENT_SCHEDULE_ID" --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-leaderboard --vault "$TMPDIR/vault" --experiment cross-model-agent --baseline-variant claude-primary --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-config --vault "$TMPDIR/vault" --experiment cross-model-agent --source auto --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-budget --vault "$TMPDIR/vault" --experiment cross-model-agent --max-cost-usd 10 --max-total-tokens 100000 --max-mean-latency-ms 2000 --max-run-tokens 1000 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-drift --vault "$TMPDIR/vault" --experiment cross-model-agent --baseline-window 2 --recent-window 2 --min-samples 1 --max-metric-drop 1 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-dashboard --vault "$TMPDIR/vault" --experiment cross-model-agent --limit 60 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-route --vault "$TMPDIR/vault" --experiment cross-model-agent --min-trials-per-lane-variant 1 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-promote --vault "$TMPDIR/vault" --experiment cross-model-agent --champion-variant claude-primary --min-trials-per-variant 1 --min-delta 0.05 --require-suite-report --require-pareto --require-budget --require-balance --require-drift --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-readiness --vault "$TMPDIR/vault" --experiment cross-model-agent --min-outcomes 6 --max-failed-outcomes 0 --require-comparison --require-budget --require-route --require-memory --require-quorum --require-promotion --require-balance --require-drift --json >/dev/null
AGENT_ROLLOUT_JSON="$("$PYTHON_BIN" -m griosai.cli agent-rollout --vault "$TMPDIR/vault" --experiment cross-model-agent --stages 0.1,0.5,1 --min-observation-runs 2 --max-stage-failed-outcomes 0 --require-readiness --require-promotion --require-budget --require-drift --json)"
AGENT_ROLLOUT_ID="$(printf '%s' "$AGENT_ROLLOUT_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["rollout_id"])')"
while read -r RUN_ID VARIANT_ID; do
  [ -z "$RUN_ID" ] && continue
  case "$VARIANT_ID" in
    openai-backup) QUALITY="0.97" ;;
    claude-primary) QUALITY="0.76" ;;
    *) continue ;;
  esac
  "$PYTHON_BIN" -m griosai.cli agent-outcome --vault "$TMPDIR/vault" --run-id "$RUN_ID" --status succeeded --metrics-json "{\"quality\": $QUALITY}" --usage-json '{"total_tokens": 80, "latency_ms": 650, "cost_usd": 0.01}' --json >/dev/null
done <<< "$AGENT_SUITE_RUNS"
"$PYTHON_BIN" -m griosai.cli agent-budget --vault "$TMPDIR/vault" --experiment cross-model-agent --max-cost-usd 10 --max-total-tokens 200000 --max-mean-latency-ms 2000 --max-run-tokens 1000 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-drift --vault "$TMPDIR/vault" --experiment cross-model-agent --baseline-window 2 --recent-window 2 --min-samples 1 --max-metric-drop 1 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-rollout-check --vault "$TMPDIR/vault" --rollout-id "$AGENT_ROLLOUT_ID" --stage-index 1 --min-stage-outcomes 2 --max-stage-failed-outcomes 0 --min-metric-delta 0.05 --require-budget --require-readiness --require-drift --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-evolve --vault "$TMPDIR/vault" --experiment cross-model-agent --min-trials-per-variant 1 --min-samples-per-variant 1 --max-lessons 8 --max-cost-usd 10 --max-total-tokens 200000 --max-mean-latency-ms 2000 --require-budget --require-route --require-drift --champion-variant claude-primary --min-delta 0.05 --plan-rollout --json >/dev/null
AGENT_CURRICULUM_PLAN_JSON="$("$PYTHON_BIN" -m griosai.cli agent-curriculum-plan --vault "$TMPDIR/vault" --config-file examples/agent-experiment.json --suite-file examples/agent-suite.json --subject-prefix validation-curriculum-rerun --baseline-variant claude-primary --max-cases 2 --json)"
printf '%s\n' "$AGENT_CURRICULUM_PLAN_JSON" | "$PYTHON_BIN" -c 'import json, sys; data=json.load(sys.stdin); raise SystemExit(data["case_count"] != 2 or data["run_count"] == 0 or not data.get("curriculum"))'
AGENT_CURRICULUM_SUITE_ID="$(printf '%s' "$AGENT_CURRICULUM_PLAN_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["suite_id"])')"
AGENT_CURRICULUM_RUNS="$(printf '%s' "$AGENT_CURRICULUM_PLAN_JSON" | "$PYTHON_BIN" -c 'import json, sys; data=json.load(sys.stdin); print("\n".join("{} {}".format(run["run_id"], run["variant_id"]) for plan in data["plans"] for run in plan["runs"]))')"
while read -r RUN_ID VARIANT_ID; do
  [ -z "$RUN_ID" ] && continue
  case "$VARIANT_ID" in
    openai-backup) QUALITY="0.96" ;;
    claude-primary) QUALITY="0.76" ;;
    *) QUALITY="0.70" ;;
  esac
  "$PYTHON_BIN" -m griosai.cli agent-outcome --vault "$TMPDIR/vault" --run-id "$RUN_ID" --status succeeded --metrics-json "{\"quality\": $QUALITY}" --usage-json '{"total_tokens": 100, "latency_ms": 800, "cost_usd": 0.02}' --json >/dev/null
done <<< "$AGENT_CURRICULUM_RUNS"
"$PYTHON_BIN" -m griosai.cli agent-suite-report --vault "$TMPDIR/vault" --suite-id "$AGENT_CURRICULUM_SUITE_ID" --min-completed-ratio 1 --json >/dev/null
if "$PYTHON_BIN" -m griosai.cli agent-budget --vault "$TMPDIR/vault" --experiment cross-model-agent --max-total-tokens 1 --json >/dev/null; then
  echo "Expected agent-budget to fail when token budget is too low." >&2
  exit 1
fi
AGENT_RECOVER_PLAN_JSON="$("$PYTHON_BIN" -m griosai.cli agent-plan --vault "$TMPDIR/vault" --config-file examples/agent-experiment.json --subject validation-recover --lanes scout --json)"
AGENT_RECOVER_RUN_ID="$(printf '%s' "$AGENT_RECOVER_PLAN_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["runs"][0]["run_id"])')"
"$PYTHON_BIN" -m griosai.cli agent-outcome --vault "$TMPDIR/vault" --run-id "$AGENT_RECOVER_RUN_ID" --status failed --metrics-json '{"quality": 0.1}' --failure-code validation_failure --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-recover --vault "$TMPDIR/vault" --experiment cross-model-agent --max-retries 2 --stale-after-seconds 120 --json >/dev/null
AGENT_PLAN_JSON="$("$PYTHON_BIN" -m griosai.cli agent-plan --vault "$TMPDIR/vault" --config-file examples/agent-experiment.json --subject validation-parallel --lanes scout,reviewer --json)"
printf '%s\n' "$AGENT_PLAN_JSON"
AGENT_PLAN_ID="$(printf '%s' "$AGENT_PLAN_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["plan_id"])')"
AGENT_CLAIM_JSON="$("$PYTHON_BIN" -m griosai.cli agent-claim --vault "$TMPDIR/vault" --plan-id "$AGENT_PLAN_ID" --client-id validation-worker --ttl-seconds 120 --claim-strategy lane-balanced --json)"
AGENT_CLAIM_ID="$(printf '%s' "$AGENT_CLAIM_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["claim_id"])')"
"$PYTHON_BIN" -m griosai.cli agent-work --vault "$TMPDIR/vault" --claim-id "$AGENT_CLAIM_ID" --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-heartbeat --vault "$TMPDIR/vault" --claim-id "$AGENT_CLAIM_ID" --client-id validation-worker --ttl-seconds 120 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-dispatch --vault "$TMPDIR/vault" --plan-id "$AGENT_PLAN_ID" --client-prefix validation-dispatch --count 4 --ttl-seconds 120 --claim-strategy variant-balanced --json >/dev/null
AGENT_PLAN_RUNS="$(printf '%s' "$AGENT_PLAN_JSON" | "$PYTHON_BIN" -c 'import json, sys; print("\n".join(item["run_id"] for item in json.load(sys.stdin)["runs"]))')"
while IFS= read -r RUN_ID; do
  [ -z "$RUN_ID" ] && continue
  "$PYTHON_BIN" -m griosai.cli agent-outcome --vault "$TMPDIR/vault" --run-id "$RUN_ID" --status succeeded --metrics-json '{"quality": 0.9}' --usage-json '{"total_tokens": 120, "latency_ms": 900, "cost_usd": 0.02}' --json >/dev/null
done <<< "$AGENT_PLAN_RUNS"
"$PYTHON_BIN" -m griosai.cli agent-merge --vault "$TMPDIR/vault" --plan-id "$AGENT_PLAN_ID" --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-gate --vault "$TMPDIR/vault" --plan-id "$AGENT_PLAN_ID" --metric-threshold 0.8 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-adjudicate --vault "$TMPDIR/vault" --plan-id "$AGENT_PLAN_ID" --min-consensus-ratio 0 --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-audit --vault "$TMPDIR/vault" --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-snapshot --vault "$TMPDIR/vault" --experiment cross-model-agent --json >/dev/null
AGENT_MANIFEST_JSON="$("$PYTHON_BIN" -m griosai.cli agent-manifest --vault "$TMPDIR/vault" --experiment cross-model-agent --json)"
AGENT_MANIFEST_ID="$(printf '%s' "$AGENT_MANIFEST_JSON" | "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin)["manifest_id"])')"
"$PYTHON_BIN" -m griosai.cli agent-verify-manifest --vault "$TMPDIR/vault" --manifest-id "$AGENT_MANIFEST_ID" --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-timeline --vault "$TMPDIR/vault" --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-watchdog --vault "$TMPDIR/vault" --json >/dev/null
"$PYTHON_BIN" -m griosai.cli agent-status --vault "$TMPDIR/vault" --json >/dev/null

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
