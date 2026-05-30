# Agent Harness

The agent harness gives GriosAI a provider-neutral control plane for model
experiments. It does not call Claude, OpenAI, Ollama, or any other provider by
itself. Instead it selects a model variant, writes a metadata-only run manifest,
then lets the operator or an external runner call the selected adapter and log
the outcome.

This keeps the local CLI useful without making cloud providers required.

## Experiment Config

An experiment config lists model variants, traffic weights, a primary metric,
a scoring rubric, and promotion guardrails:

```bash
griosai agent-run \
  --vault ~/GriosAI-vault \
  --config-file examples/agent-experiment.json \
  --subject thread-2026-05-30 \
  --prompt-file ./private-prompt.md \
  --json
```

`--subject` is the stable A/B assignment key. The raw subject value is hashed
before it is written to the vault. `--prompt-file` is optional; when present,
GriosAI records only the prompt character count, source basename, and SHA-256
hash.

Run manifests live under:

```text
agent-runs/<experiment>/runs/<run-id>.json
```

The selected variant includes `provider`, `model`, `adapter`, `weight`, and safe
settings, so any runner can decide which backend to call.

## Parallel Agent Plans

Use `agent-plan` when a task should fan out across multiple lanes, such as
scout, builder, reviewer, and adversary:

```bash
griosai agent-plan \
  --vault ~/GriosAI-vault \
  --config-file examples/agent-experiment.json \
  --subject thread-2026-05-30 \
  --prompt-file ./private-prompt.md \
  --json
```

The plan writes one child run manifest per lane and replica. Each child run has
its own deterministic model assignment and includes `parallel.plan_id`,
`parallel.lane_id`, role metadata, and replica number. External runners can
execute those child runs concurrently.

Plan artifacts live under:

```text
agent-runs/<experiment>/plans/<plan-id>.json
agent-runs/<experiment>/plans/<plan-id>.md
```

Override lanes at the CLI when you want a tighter fanout:

```bash
griosai agent-plan \
  --vault ~/GriosAI-vault \
  --config-file examples/agent-experiment.json \
  --subject thread-2026-05-30 \
  --lanes scout,builder,reviewer \
  --replicas 2
```

## Cross-Model Matrix Plans

Use `agent-matrix` when you need a controlled benchmark rather than weighted
traffic assignment. It creates every `variant x lane x replica` run cell, so
Claude, OpenAI, Ollama, and any custom variant all receive the same lane
coverage:

```bash
griosai agent-matrix \
  --vault ~/GriosAI-vault \
  --config-file examples/agent-experiment.json \
  --subject benchmark-2026-05-30 \
  --lanes scout,builder,reviewer \
  --replicas 2 \
  --json
```

Matrix child runs use `assignment.strategy=variant-matrix` and record a
`forced_variant_id`, while still hashing the subject and prompt metadata. The
same claim, work-packet, outcome, scorecard, merge, gate, adjudication, audit,
timeline, status, promotion, and improvement commands apply to matrix plans.

## Evaluation Suites

Use `agent-suite` when a model contest needs repeatable coverage across many
cases rather than one subject. By default it creates one matrix plan per case,
so each case gets the same `variant x lane x replica` treatment:

```bash
griosai agent-suite \
  --vault ~/GriosAI-vault \
  --config-file examples/agent-experiment.json \
  --suite-file examples/agent-suite.json \
  --subject-prefix regression-loop-001 \
  --lanes scout,reviewer \
  --json
```

Suite case prompts are hashed into child run manifests; raw prompt text,
expected answers, transcripts, and outputs are not written to the vault. Suite
artifacts link each case to its generated plan and run ids:

```text
agent-runs/<experiment>/suites/<suite-id>.json
agent-runs/<experiment>/suites/<suite-id>.md
```

After logging outcomes for the suite runs, use `agent-suite-report` for paired
case evidence. This compares each candidate to the baseline on the same cases,
which is more useful than a plain average when case difficulty varies:

```bash
griosai agent-suite-report \
  --vault ~/GriosAI-vault \
  --suite-id suite-20260530T120000Z-abcdef12 \
  --baseline-variant claude-primary \
  --json
```

Suite reports summarize completed cases, per-variant case means, paired deltas,
token/latency/cost usage, Pareto-efficient variants, missing coverage, and
recommendations:

```text
agent-runs/<experiment>/suite-reports/<report-id>.json
agent-runs/<experiment>/suite-reports/<report-id>.md
```

## Dependency-Aware Pipelines

Use `agent-pipeline` when a task should move through stage gates instead of
running every lane at once. A pipeline stage can use weighted routing or a full
variant matrix, depend on earlier stages, and require a minimum success ratio
before later stages can be scheduled:

```bash
griosai agent-pipeline \
  --vault ~/GriosAI-vault \
  --config-file examples/agent-experiment.json \
  --pipeline-file examples/agent-pipeline.json \
  --subject-prefix ship-loop-001 \
  --json
```

Only dependency-free stages are scheduled initially. After workers log outcomes
for the current stage plans, advance the pipeline:

```bash
griosai agent-pipeline-advance \
  --vault ~/GriosAI-vault \
  --pipeline-id <pipeline-id> \
  --json
```

`agent-pipeline-advance` creates ordinary claimable stage plans only for stages
whose dependencies have completed and passed their gates. If a dependency stage
fails its configured `min_success_ratio`, later stages are marked blocked until
the operator retries or recovers the failed work. Pipeline ledgers store stage
ids, plan ids, dependency state, prompt fingerprints, and success metadata, not
raw prompts or outputs.

```text
agent-runs/<experiment>/pipelines/<pipeline-id>.json
agent-runs/<experiment>/pipelines/<pipeline-id>.md
agent-runs/<experiment>/pipeline-advances/<advance-id>.json
agent-runs/<experiment>/pipeline-advances/<advance-id>.md
```

## Round-Robin Arenas

Use `agent-arena` when every model variant should face every other variant in
balanced head-to-head blocks. The command creates a normal claimable plan with
two forced-variant runs per match and stores only prompt fingerprints, run ids,
variant ids, lanes, and match metadata:

```bash
griosai agent-arena \
  --vault ~/GriosAI-vault \
  --config-file examples/agent-experiment.json \
  --subject model-arena-001 \
  --lanes reviewer \
  --replicas 2 \
  --max-runs 128 \
  --json
```

After workers log outcomes, summarize the arena:

```bash
griosai agent-arena-report \
  --vault ~/GriosAI-vault \
  --arena-id <arena-id> \
  --min-completed-ratio 1 \
  --json
```

The arena report ranks variants by head-to-head wins, losses, ties, win rate,
mean metric, and an operator-friendly arena rating. Leaderboards fold the
latest arena report into cross-evidence scoring.

```text
agent-runs/<experiment>/arenas/<arena-id>.json
agent-runs/<experiment>/arenas/<arena-id>.md
agent-runs/<experiment>/arena-reports/<report-id>.json
agent-runs/<experiment>/arena-reports/<report-id>.md
```

## Judge Panels

Use `agent-judge-panel` when completed source plan outputs need independent
model review. The command creates a normal claimable judge plan, one judge run
per target output, judge variant, and replica. By default, a variant does not
judge its own output. The panel stores target run ids, variant ids, outcome ids,
and output fingerprints, not raw target output or judge rationale:

```bash
griosai agent-judge-panel \
  --vault ~/GriosAI-vault \
  --config-file examples/agent-experiment.json \
  --plan-id <source-plan-id> \
  --judge-variants claude-primary,openai-backup \
  --metric judge_score \
  --max-runs 128 \
  --json
```

Workers complete the judge runs and log the configured metric, typically
`judge_score`. Then aggregate the panel:

```bash
griosai agent-judge-report \
  --vault ~/GriosAI-vault \
  --panel-id <panel-id> \
  --min-completed-ratio 1 \
  --json
```

The judge report ranks target runs and target variants by mean judge score, and
leaderboards fold the latest judge-panel report into cross-evidence scoring.

```text
agent-runs/<experiment>/judge-panels/<panel-id>.json
agent-runs/<experiment>/judge-panels/<panel-id>.md
agent-runs/<experiment>/judge-panel-reports/<report-id>.json
agent-runs/<experiment>/judge-panel-reports/<report-id>.md
```

## Work Claims

Use `agent-preflight` before a large worker wave to fail fast when the pending
scope is not actually cross-model, has stale active claims, is missing lanes or
variants, or is skewed before dispatch:

```bash
griosai agent-preflight \
  --vault ~/GriosAI-vault \
  --suite-id <suite-id> \
  --require-cross-model \
  --require-lane-coverage \
  --require-variant-coverage \
  --max-pending-skew 0 \
  --json
```

Preflight artifacts are metadata-only launch gates. They live under:

```text
agent-runs/_reports/<preflight-id>.json
agent-runs/_reports/<preflight-id>.md
```

Use `agent-hold` as an append-only kill switch before launching or continuing a
worker wave or before changing the winning model policy. Hold scopes are:
`dispatch`, `promotion`, `rollout`, `evolve`, and `all`.

A `dispatch` hold blocks `agent-claim`, `agent-dispatch`, and
`agent-orchestrate`; `agent-preflight` fails while the hold is active. A
`promotion` hold blocks `agent-promote`. A `rollout` hold blocks
`agent-rollout` and `agent-rollout-check`. An `evolve` hold blocks top-level
`agent-evolve` loops before they write new improvement artifacts. `all` matches
every hold-aware control-plane gate.

```bash
griosai agent-hold \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --scopes dispatch \
  --reason "pause worker wave" \
  --json
```

Release either one hold id or all holds that match a scope:

```bash
griosai agent-release \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --hold-id <hold-id> \
  --reason "resume worker wave" \
  --json
```

Hold artifacts are metadata-only and show up in status, timeline, and preflight
evidence:

```text
agent-runs/<experiment>/holds/<hold-id>.json
agent-runs/<experiment>/holds/<hold-id>.md
```

Use `agent-quarantine` when a specific provider, variant, or lane should stop
receiving new worker claims while the rest of the experiment keeps moving. This
is the circuit breaker for provider incidents, model regressions, or bad lane
instructions:

```bash
griosai agent-quarantine \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --providers openai \
  --reason "provider incident" \
  --json
```

Quarantines filter `agent-claim`, `agent-dispatch`, and orchestration-driven
dispatches by leaving matching pending runs unclaimed. `agent-preflight` reports
active quarantines and quarantined pending runs, while status and timeline show
the append-only quarantine ledger.

Release by id, or by matching target filters:

```bash
griosai agent-unquarantine \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --quarantine-id <quarantine-id> \
  --reason "provider recovered" \
  --json
```

Quarantine artifacts are metadata-only:

```text
agent-runs/<experiment>/quarantines/<quarantine-id>.json
agent-runs/<experiment>/quarantines/<quarantine-id>.md
```

Use `agent-circuit` to evaluate automated circuit breakers from recent outcome
metadata. It can group by provider, variant, or lane and trip on failure rate,
mean latency, mean cost, or a direction-aware primary metric floor. With
`--quarantine-on-trip`, tripped slices write matching quarantine artifacts:

```bash
griosai agent-circuit \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --group-by provider \
  --min-outcomes 3 \
  --max-failure-rate 0.25 \
  --max-mean-latency-ms 3000 \
  --quarantine-on-trip \
  --json
```

The command exits nonzero when a circuit trips, so use passing thresholds for CI
smoke runs and stricter thresholds in operator loops that should stop a worker
wave. Circuit reports are metadata-only:

```text
agent-runs/<experiment>/circuits/<circuit-id>.json
agent-runs/<experiment>/circuits/<circuit-id>.md
```

Use `agent-claim` when multiple workers need to pull from the same plan without
duplicating work:

```bash
griosai agent-claim \
  --vault ~/GriosAI-vault \
  --plan-id plan-20260530T120000Z-abcdef123456 \
  --client-id worker-1 \
  --lane scout \
  --ttl-seconds 3600 \
  --claim-strategy lane-balanced \
  --json
```

The claim writes a short lease for the next uncompleted and unclaimed child run.
Expired claims can be reclaimed. Completed runs are skipped even if an old claim
still exists.

The default claim strategy is `fifo` for strict plan order. Larger matrix or
suite runs can use `lane-balanced`, `variant-balanced`, or
`lane-variant-balanced` so the first wave of workers covers different lanes and
models instead of draining one lane or variant before the others start.

Claim artifacts live under:

```text
agent-runs/<experiment>/claims/<claim-id>.json
```

Long-running workers should heartbeat before the lease expires:

```bash
griosai agent-heartbeat \
  --vault ~/GriosAI-vault \
  --claim-id claim-20260530T120000Z-abcdef1234 \
  --client-id worker-1 \
  --ttl-seconds 3600 \
  --json
```

Heartbeat artifacts extend the effective claim expiry without rewriting the
original claim:

```text
agent-runs/<experiment>/heartbeats/<heartbeat-id>.json
```

Use `agent-dispatch` when you want to lease a batch of pending plan runs and
write their handoff packets in one step:

```bash
griosai agent-dispatch \
  --vault ~/GriosAI-vault \
  --plan-id plan-20260530T120000Z-abcdef123456 \
  --client-prefix worker \
  --count 8 \
  --ttl-seconds 3600 \
  --claim-strategy lane-variant-balanced \
  --json
```

The dispatch manifest records one worker id, claim, work packet, run, lane,
variant, provider, model, and adapter per entry. It does not call providers or
store raw work. Dispatch artifacts live under:

```text
agent-runs/<experiment>/dispatches/<dispatch-id>.json
agent-runs/<experiment>/dispatches/<dispatch-id>.md
```

## Capacity Orchestration

Use `agent-orchestrate` when a suite or plan has many pending runs and you want
the harness to fill worker capacity without over-claiming:

```bash
griosai agent-orchestrate \
  --vault ~/GriosAI-vault \
  --suite-id suite-20260530T120000Z-abcdef12 \
  --client-prefix worker \
  --max-concurrency 12 \
  --batch-size 4 \
  --ttl-seconds 3600 \
  --claim-strategy lane-variant-balanced \
  --json
```

The scheduler reads active claims, heartbeats, outcomes, expired claims, and
pending runs, then dispatches only up to `--max-concurrency`. It can target one
plan with `--plan-id` or every plan in a suite with `--suite-id`; `--lane` can
limit dispatch to a role such as reviewer. The claim strategy is applied inside
each dispatch batch, so `agent-orchestrate` can keep early worker capacity
spread across lanes and model variants while still respecting the global
concurrency cap.

Orchestration reports live under:

```text
agent-runs/_reports/<orchestration-id>.json
agent-runs/_reports/<orchestration-id>.md
```

## Operator Cycle

Use `agent-cycle` as the local-first control loop for a plan or suite. It can
recover failed or stale work, fill dispatch capacity, then write watchdog,
status, timeline, and dashboard artifacts in one metadata-only pass:

```bash
griosai agent-cycle \
  --vault ~/GriosAI-vault \
  --suite-id suite-20260530T120000Z-abcdef12 \
  --client-prefix worker \
  --max-concurrency 12 \
  --batch-size 4 \
  --stale-after-seconds 1800 \
  --max-retries 8 \
  --dashboard-limit 80 \
  --json
```

Use `--plan-id` instead of `--suite-id` for one plan. Use
`--skip-recovery` when the cycle should only schedule and observe work, or
`--skip-orchestration` when it should only recover and refresh operator
reports. The cycle never calls model providers and does not store raw prompts,
transcripts, outputs, or errors.

Cycle reports live under:

```text
agent-runs/_reports/<cycle-id>.json
agent-runs/_reports/<cycle-id>.md
```

## Bounded Agent Loop

Use `agent-loop` when you want repeated cycle passes without creating an
unbounded daemon. It runs `agent-cycle` up to `--max-cycles`, stops early after
`--stop-after-idle-cycles` consecutive cycles that recover or dispatch no work,
and writes one loop ledger that points at every cycle artifact:

```bash
griosai agent-loop \
  --vault ~/GriosAI-vault \
  --suite-id suite-20260530T120000Z-abcdef12 \
  --client-prefix worker \
  --max-concurrency 12 \
  --batch-size 4 \
  --max-cycles 3 \
  --stop-after-idle-cycles 1 \
  --json
```

The command is intentionally bounded: `--max-cycles` is capped, and the default
idle stop prevents busy-looping while external workers are still running. Like
the lower-level cycle, it only records metadata and never calls model providers
or stores raw prompts, transcripts, outputs, or errors.

Loop reports live under:

```text
agent-runs/_reports/<loop-id>.json
agent-runs/_reports/<loop-id>.md
```

## Capacity Planner

Use `agent-capacity` before a large dispatch wave when you want the harness to
recommend how many claims to launch from the current backlog. It reads pending
runs, active claims, stale claims, holds, quarantines, lane/variant skew, and
recent latency metadata, then recommends a batch size, claim strategy, claim
TTL, and heartbeat interval:

```bash
griosai agent-capacity \
  --vault ~/GriosAI-vault \
  --suite-id suite-20260530T120000Z-abcdef12 \
  --max-concurrency 12 \
  --target-utilization 0.85 \
  --json
```

The report does not claim work by itself. Use its `batch_size` and
`claim_strategy` recommendation with `agent-orchestrate`, `agent-dispatch`, or
the next bounded `agent-loop` pass.

Capacity reports live under:

```text
agent-runs/_reports/<capacity-id>.json
agent-runs/_reports/<capacity-id>.md
```

## SLO Gate

Use `agent-slo` before promotion, rollout, or another large worker wave when
parallel-agent fleet health should be a hard gate. It evaluates scheduled
completion, failure rate, stale and expired claims, active holds, quarantines,
and optional mean latency from metadata-only outcomes:

```bash
griosai agent-slo \
  --vault ~/GriosAI-vault \
  --suite-id suite-20260530T120000Z-abcdef12 \
  --min-completion-rate 0.95 \
  --max-failure-rate 0.05 \
  --max-mean-latency-ms 5000 \
  --json
```

The command exits nonzero when the SLO fails. Use relaxed thresholds for smoke
tests and strict thresholds for launch, promotion, and rollout gates.

SLO reports live under:

```text
agent-runs/_reports/<slo-id>.json
agent-runs/_reports/<slo-id>.md
```

## Model Mix Gate

Use `agent-mix` when an experiment must prove it is actually cross-model before
you trust A/B evidence, promotion, or rollout. It checks configured providers,
variants, adapters, local-provider presence, scheduled run concentration, and
completed outcome concentration:

```bash
griosai agent-mix \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --min-provider-count 2 \
  --max-provider-weight-share 0.8 \
  --require-local-provider \
  --json
```

The command exits nonzero when the experiment collapses to one provider or one
dominant provider share. It stores provider/model/adapter metadata, counts, and
findings only; subjects, prompts, transcripts, outputs, and raw errors remain
omitted.

Model mix reports live under:

```text
agent-runs/<experiment>/mix/<mix-id>.json
agent-runs/<experiment>/mix/<mix-id>.md
```

## Worker Handoff Packets

Use `agent-work` after claiming a run to write a durable packet for the external
worker:

```bash
griosai agent-work \
  --vault ~/GriosAI-vault \
  --claim-id claim-20260530T120000Z-abcdef1234 \
  --json
```

The packet includes provider/model/adapter metadata, lane role and objective,
guardrails, rubric criteria, prompt fingerprint metadata, and suggested next
commands. It does not store the raw prompt, raw transcript, raw output, or raw
errors.

Work packets live under:

```text
agent-runs/<experiment>/work-packets/<packet-id>.json
agent-runs/<experiment>/work-packets/<packet-id>.md
```

## Retry And Requeue

Use `agent-retry` when a run failed, a worker went stale, or an operator wants a
clean replacement run without rewriting history:

```bash
griosai agent-retry \
  --vault ~/GriosAI-vault \
  --run-id run-20260530T120000Z-abcdef123456 \
  --reason adapter_timeout \
  --json
```

The retry writes a replacement run and a retry provenance record. For plan runs,
merge, gate, adjudication, status, and watchdog treat the replacement as
superseding the original run, while audit and timeline keep both artifacts
visible:

```text
agent-runs/<experiment>/retries/<retry-id>.json
agent-runs/<experiment>/retries/<retry-id>.md
```

Use `agent-recover` to batch-create bounded replacement runs for failed
outcomes, stale active claims, and expired claims:

```bash
griosai agent-recover \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --max-retries 8 \
  --stale-after-seconds 1800 \
  --json
```

Recovery writes a metadata-only report under:

```text
agent-runs/_reports/<recovery-id>.json
agent-runs/_reports/<recovery-id>.md
```

## Outcome Logs

After the selected adapter finishes, either score it with the experiment rubric
or log already-computed metrics directly. `agent-score` writes a scorecard and
also logs an outcome using the rubric's aggregate metric:

```bash
griosai agent-score \
  --vault ~/GriosAI-vault \
  --run-id run-20260530T120000-abcdef123456 \
  --scores-json '{"correctness": 0.9, "safety": 1, "efficiency": 0.7}' \
  --usage-json '{"prompt_tokens": 1200, "completion_tokens": 400, "latency_ms": 2100, "cost_usd": 0.03}' \
  --output-file ./private-answer.md \
  --json
```

Direct metric logging remains available for external evaluators:

```bash
griosai agent-outcome \
  --vault ~/GriosAI-vault \
  --run-id run-20260530T120000-abcdef123456 \
  --status succeeded \
  --metrics-json '{"quality": 0.87, "latency_ms": 2400}' \
  --usage-json '{"total_tokens": 1600, "latency_ms": 2400, "cost_usd": 0.04}' \
  --output-file ./private-answer.md \
  --json
```

Outcome logs store numeric metrics, status, selected variant metadata, and an
optional output hash. They also accept separate usage metadata for token counts,
latency, tool-call counts, and estimated cost so score comparisons can include
price and speed evidence. They do not store raw prompt text, raw output text,
transcripts, or error bodies.

Scorecards live under:

```text
agent-runs/<experiment>/scorecards/<scorecard-id>.json
agent-runs/<experiment>/scorecards/<scorecard-id>.md
```

Outcome manifests live under:

```text
agent-runs/<experiment>/outcomes/<outcome-id>.json
```

## Batch Result Ingest

Use `agent-ingest` when external workers return a batch of result metadata:

```bash
griosai agent-ingest \
  --vault ~/GriosAI-vault \
  --results-file ./worker-results.json \
  --json
```

The results file must contain a `results` or `outcomes` array. Each item needs
a `run_id`, `status`, and either `metrics` or rubric `scores`; optional `usage`,
`failure_code`, and output fingerprint metadata are accepted. Raw prompts,
transcripts, outputs, and error bodies are rejected:

```json
{
  "results": [
    {
      "run_id": "run-20260530T120000-abcdef123456",
      "status": "succeeded",
      "metrics": {"quality": 0.87},
      "usage": {"total_tokens": 1600, "latency_ms": 2400, "cost_usd": 0.04},
      "output": {"present": true, "chars": 1200, "sha256": "<sha256>", "source_name": "answer.md"}
    }
  ]
}
```

Ingest reports live under:

```text
agent-runs/_reports/<ingest-id>.json
agent-runs/_reports/<ingest-id>.md
```

## Statistical Comparisons

Use `agent-compare` after logging outcomes to produce model evidence that is
stronger than a plain average:

```bash
griosai agent-compare \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --baseline-variant claude-primary \
  --min-samples-per-variant 3 \
  --json
```

The comparison report ranks eligible variants, computes 95% normal-approximate
confidence intervals, compares each challenger against the baseline with
direction-aware deltas and lift, and flags under-sampled or unbalanced
coverage. When usage metadata is present, it also reports the Pareto frontier:
variants not dominated on primary metric, average cost, average latency, and
average tokens. It stores numeric metadata only.

Comparison artifacts live under:

```text
agent-runs/<experiment>/comparisons/<comparison-id>.json
agent-runs/<experiment>/comparisons/<comparison-id>.md
```

## Sample Balance

Use `agent-balance` before promoting a benchmark or trusting a sequential A/B
decision. It verifies completed outcome counts across variant, lane, and case
cells so one model does not look better merely because it received easier or
more complete coverage:

```bash
griosai agent-balance \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --suite-id <suite-id> \
  --dimensions variant,lane,case \
  --min-count-per-cell 1 \
  --max-skew 0 \
  --json
```

The report stores scheduled run ids, completed run ids, counts, completion
ratios, findings, and recommendations. Use `--require-balance` on
`agent-promote` or `agent-readiness` when promotion and rollout gates must stop
until the latest balance report is `balanced`. It does not store raw prompts,
transcripts, outputs, or errors.

```text
agent-runs/<experiment>/balances/<balance-id>.json
agent-runs/<experiment>/balances/<balance-id>.md
```

## Sequential A/B Decisions

Use `agent-decision` when the operator needs a stop/continue call from the
latest cross-model evidence:

```bash
griosai agent-decision \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --baseline-variant claude-primary \
  --candidate-variant openai-backup \
  --min-samples-per-variant 3 \
  --min-delta 0.05 \
  --confidence-threshold 0.8 \
  --max-cost-usd 10 \
  --max-total-tokens 100000 \
  --json
```

The decision uses a one-sided normal approximation over primary-metric
outcomes and writes one of `stop-promote`, `stop-baseline`, `continue`, or
`blocked`. Optional cost, token, and candidate metric guardrails prevent a
statistical win from skipping budget or quality review. The artifact stores
only numeric evidence, variant ids, usage aggregates, and recommendations.

Decision artifacts live under:

```text
agent-runs/<experiment>/decisions/<decision-id>.json
agent-runs/<experiment>/decisions/<decision-id>.md
```

## Drift Monitoring

Use `agent-drift` before promotion or rollout when recent outcomes might no
longer match the evidence that picked a winner. It compares the newest outcomes
for each variant and lane/variant window against the prior window, then fails
when quality regresses beyond the configured metric threshold or usage
regresses beyond configured cost or latency ratios:

```bash
griosai agent-drift \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --baseline-window 5 \
  --recent-window 5 \
  --max-metric-drop 0.05 \
  --max-cost-increase-ratio 0.5 \
  --max-latency-increase-ratio 0.5 \
  --json
```

The artifact stores only metric means, usage aggregates, direction-aware
regression amounts, findings, and recommendations. Use `--require-drift` on
`agent-promote` or `agent-readiness` when promotion and rollout gates must stop
until the latest drift report is `stable`.

```text
agent-runs/<experiment>/drift/<drift-id>.json
agent-runs/<experiment>/drift/<drift-id>.md
```

## Experiment Power

Use `agent-power` before launching the next expensive matrix or suite run. It
uses observed primary-metric variance, a minimum detectable effect, and optional
budget limits to estimate how many additional baseline and challenger samples
are needed for each cross-model comparison:

```bash
griosai agent-power \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --baseline-variant claude-primary \
  --min-detectable-effect 0.05 \
  --alpha 0.05 \
  --power 0.8 \
  --max-cost-usd 10 \
  --max-total-tokens 100000 \
  --json
```

If pilot data is too small to estimate variance, pass `--fallback-stddev` from
a prior experiment or run a small matrix first. Power artifacts live under:

```text
agent-runs/<experiment>/power/<power-id>.json
agent-runs/<experiment>/power/<power-id>.md
```

## Scheduled Batches

Use `agent-schedule` after `agent-power` to turn the latest sampling gap into a
normal claimable plan. By default it schedules paired baseline/challenger
blocks in the same lane, then creates a `power-schedule` plan that works with
`agent-claim`, `agent-dispatch`, `agent-work`, and `agent-ingest`:

```bash
griosai agent-schedule \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --subject benchmark-next-batch-001 \
  --lanes scout,reviewer \
  --max-runs 24 \
  --json
```

The private subject is hashed, and the schedule ledger links the power report
to the generated plan. Use `--unpaired` only when quota coverage matters more
than paired comparison quality:

```text
agent-runs/<experiment>/schedules/<schedule-id>.json
agent-runs/<experiment>/schedules/<schedule-id>.md
agent-runs/<experiment>/plans/<plan-id>.json
```

After scheduled workers log outcomes, summarize paired blocks with
`agent-schedule-report`. The report compares each candidate against the
baseline inside the same lane/block, then writes a metadata-only paired delta
ledger:

```bash
griosai agent-schedule-report \
  --vault ~/GriosAI-vault \
  --schedule-id <schedule-id> \
  --min-completed-blocks-ratio 1 \
  --json
```

```text
agent-runs/<experiment>/schedule-reports/<report-id>.json
agent-runs/<experiment>/schedule-reports/<report-id>.md
```

## Cross-Evidence Leaderboards

Use `agent-leaderboard` when an experiment has several evidence artifacts and
the operator needs one decision surface. The leaderboard ranks every variant
using outcome metrics plus latest comparison, suite-report, arena-report,
judge-panel-report, schedule-report, allocation, route, and promotion metadata:

```bash
griosai agent-leaderboard \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --baseline-variant claude-primary \
  --min-samples-per-variant 3 \
  --json
```

It writes a metadata-only report with rank, evidence score, metric coverage,
pairwise statuses, lane wins, recommended allocation share, source artifact
references, and next actions:

```text
agent-runs/<experiment>/leaderboards/<leaderboard-id>.json
agent-runs/<experiment>/leaderboards/<leaderboard-id>.md
```

## Reviewable Config Proposals

Use `agent-config` after leaderboard, allocation, route, promotion, or
improvement evidence exists. It converts the latest metadata-only evidence into
a next experiment config file plus a review report. The command never rewrites
the active experiment spec; it writes a proposed `.experiment.json` that an
operator can inspect before using in the next batch:

```bash
griosai agent-config \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --source auto \
  --exploration-floor 0.05 \
  --max-share 0.85 \
  --json
```

`--source auto` prefers ready promotion evidence, then leaderboard evidence,
allocation, lane routing, and improvement proposals. Explicit sources
(`promotion`, `leaderboard`, `allocation`, `route`, or `improvement`) are
available when the operator wants to compare a specific handoff path. The JSON
report includes the selected source, patch operations, changed variant weights,
recommendations, and a metadata-only privacy marker:

```text
agent-runs/<experiment>/config-proposals/<config-id>.json
agent-runs/<experiment>/config-proposals/<config-id>.md
agent-runs/<experiment>/config-proposals/<config-id>.experiment.json
```

## Merge Reports

After logging outcomes for child runs, merge the plan:

```bash
griosai agent-merge \
  --vault ~/GriosAI-vault \
  --plan-id plan-20260530T120000Z-abcdef123456 \
  --json
```

The merge report summarizes completion by lane, success rates, best metric per
lane, and a recommended run id when metrics are available. It still stores only
metadata and output fingerprints.

Merge artifacts live under:

```text
agent-runs/<experiment>/merges/<merge-id>.json
agent-runs/<experiment>/merges/<merge-id>.md
```

## Quality Gates

Use `agent-gate` before trusting or promoting a merged plan:

```bash
griosai agent-gate \
  --vault ~/GriosAI-vault \
  --plan-id plan-20260530T120000Z-abcdef123456 \
  --min-completed-ratio 1 \
  --max-failures 0 \
  --metric-threshold 0.85 \
  --require-lane scout \
  --require-lane reviewer \
  --json
```

The gate writes pass/fail evidence and returns a nonzero exit code when the plan
fails completion, failure-count, required-lane, or metric-threshold checks. The
metric threshold follows the experiment's primary metric direction.

Gate artifacts live under:

```text
agent-runs/<experiment>/gates/<gate-id>.json
agent-runs/<experiment>/gates/<gate-id>.md
```

## Quorum Reports

Use `agent-quorum` after a parallel plan has outcomes when you need to detect
split-brain lane votes before accepting a merge:

```bash
griosai agent-quorum \
  --vault ~/GriosAI-vault \
  --plan-id plan-20260530T120000Z-abcdef123456 \
  --min-completed-ratio 1 \
  --min-agreement-ratio 0.75 \
  --json
```

The quorum report records each lane's metric-backed vote, leading and minority
variants, agreement ratio, split-brain ties, and recommendations. It is
metadata-only and returns a nonzero exit code when completion or agreement
policy fails.

```text
agent-runs/<experiment>/quorums/<quorum-id>.json
agent-runs/<experiment>/quorums/<quorum-id>.md
```

## Adjudication

Use `agent-adjudicate` after merge and gate to create a decision ledger for the
parallel plan:

```bash
griosai agent-adjudicate \
  --vault ~/GriosAI-vault \
  --plan-id plan-20260530T120000Z-abcdef123456 \
  --min-completed-ratio 1 \
  --min-consensus-ratio 0.5 \
  --json
```

The adjudication records the recommended run, lane-by-lane decisions, variant
agreement ratio, latest merge and gate references, and pass/fail findings. It
returns a nonzero exit code when completion or consensus policy is not met.

Adjudication artifacts live under:

```text
agent-runs/<experiment>/adjudications/<adjudication-id>.json
agent-runs/<experiment>/adjudications/<adjudication-id>.md
```

## Integrity Audit

Use `agent-audit` before promotion or cleanup to verify the artifact graph:

```bash
griosai agent-audit \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --json
```

The audit checks missing run, plan, claim, scorecard, outcome, merge, gate, and
adjudication references; expired claims; privacy markers; secret-like or private
path patterns; and ready promotions without accepted adjudication. It exits
nonzero when fail-severity findings are present.

Audit artifacts live under:

```text
agent-runs/_reports/<audit-id>.json
agent-runs/_reports/<audit-id>.md
```

## Artifact Manifests

Use `agent-manifest` when an experiment needs a reproducible checkpoint before
cleanup, promotion, rollout, or handoff. The manifest records only metadata:
relative paths, byte counts, artifact types, schemas, timestamps, and SHA-256
hashes.

```bash
griosai agent-manifest \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --json
```

Use `agent-verify-manifest` later to detect missing, changed, or newly-created
artifacts. Extra artifacts are warnings by default, or failures with
`--fail-on-extra`:

```bash
griosai agent-verify-manifest \
  --vault ~/GriosAI-vault \
  --manifest-id <manifest-id> \
  --fail-on-extra \
  --json
```

Manifest artifacts live under:

```text
agent-runs/_reports/<manifest-id>.json
agent-runs/_reports/<manifest-id>.md
agent-runs/_reports/<verification-id>.json
agent-runs/_reports/<verification-id>.md
```

## Experiment Snapshots

Use `agent-snapshot` when you need a reproducibility checkpoint for experiment
state, not only file hashes. The snapshot fingerprints model variants, metric
and rubric settings, plan/run/outcome/control artifacts, and scoped reports
without embedding raw subjects, prompts, lane objectives, guardrail text,
outputs, transcripts, or errors:

```bash
griosai agent-snapshot \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --fail-on-change \
  --json
```

By default the command diffs against the latest prior snapshot for the
experiment. Use `--baseline-snapshot-id` to compare against a specific checkpoint.
`--fail-on-change` exits nonzero when any fingerprinted section changes, which
makes it useful in a release, rollout, or benchmark gate.

Snapshot artifacts live under:

```text
agent-runs/<experiment>/snapshots/<snapshot-id>.json
agent-runs/<experiment>/snapshots/<snapshot-id>.md
```

## Timeline Reports

Use `agent-timeline` when you need a chronological view of a harness run:

```bash
griosai agent-timeline \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --limit 200 \
  --json
```

The timeline combines run creation, plan fanout, pipelines, arenas, judge panels, worker claims, work packets,
holds, dispatches, orchestrations, cycles, loops, heartbeats, retries, outcomes,
scorecards, comparisons, decisions, drift reports, pipeline advances, arena reports, judge reports, schedule reports, leaderboards, config proposals, memories, curricula,
allocations, routes, merges, gates, quorums, adjudications, promotions,
improvements, audits, manifests, model mix reports, snapshots, budgets, dashboards, watchdogs, and prior
status/timeline reports into a metadata-only event list.
It uses timestamps and artifact ids, not raw prompts, transcripts, outputs, or
errors.

Timeline artifacts live under:

```text
agent-runs/_reports/<timeline-id>.json
agent-runs/_reports/<timeline-id>.md
```

## Worker Watchdog

Use `agent-watchdog` to find stale workers, expired claims, unclaimed plan
runs, and failed outcomes:

```bash
griosai agent-watchdog \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --stale-after-seconds 1800 \
  --json
```

The watchdog writes a metadata-only report under:

```text
agent-runs/_reports/<watchdog-id>.json
agent-runs/_reports/<watchdog-id>.md
```

## Status Scoreboard

Use `agent-status` to get an operator view across experiments:

```bash
griosai agent-status --vault ~/GriosAI-vault --json
```

The status report inventories run counts, plans, pipelines, arenas, judge panels, claims, holds, work packets,
dispatches, orchestrations, capacity reports, SLO reports, model mix reports, cycles, loops, leaderboards, config proposals, snapshots, decisions, memories, curricula,
allocations, routes, scorecards, outcomes, ingests, merges, gates, quorums,
adjudications, budget reports, dashboard reports, promotions, failed
outcomes, queued plan runs, claimed plan runs, expired claims, variant
summaries, and recommended next actions. Scope it to one experiment when
needed:

```bash
griosai agent-status \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent
```

Status artifacts live under:

```text
agent-runs/_reports/<status-id>.json
agent-runs/_reports/<status-id>.md
```

## Budget Gates

Use `agent-budget` after logging outcomes with usage metadata to cap experiment
cost, token use, and latency before large fanouts or promotions:

```bash
griosai agent-budget \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --max-cost-usd 10 \
  --max-total-tokens 100000 \
  --max-mean-latency-ms 2000 \
  --max-run-tokens 4000 \
  --json
```

The report is metadata-only. It totals cost, tokens, tool calls, and latency
from outcome usage records; warns when outcomes lack usage metadata; and exits
nonzero when an aggregate or per-run cap is exceeded. Budget artifacts live
under:

```text
agent-runs/_reports/<budget-id>.json
agent-runs/_reports/<budget-id>.md
```

Promotion can require the latest matching budget report to be within budget:

```bash
griosai agent-promote \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --require-budget
```

## Readiness Gates

Use `agent-readiness` when an experiment needs one operator gate before
increasing traffic, worker count, or model weights. The gate rolls up outcome
counts, failed outcomes, latest comparison evidence, latest budget status, lane
routing, latest drift status, metadata-only memory, lane quorum, and promotion
status:

```bash
griosai agent-readiness \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --min-outcomes 12 \
  --max-failed-outcomes 0 \
  --require-comparison \
  --require-budget \
  --require-route \
  --require-memory \
  --require-quorum \
  --require-promotion \
  --require-balance \
  --require-drift \
  --json
```

The command exits nonzero when a required control is missing, not passing, or
over configured limits. Warnings still produce a ready result when the strict
policy passes, but they are written into the report for review. Readiness
artifacts are metadata-only and live under:

```text
agent-runs/<experiment>/readiness/<readiness-id>.json
agent-runs/<experiment>/readiness/<readiness-id>.md
```

## Rollout Plans

Use `agent-rollout` after readiness and promotion when a challenger should be
rolled out in stages instead of applied as a single jump. The command writes a
metadata-only staged traffic plan, required checks between stages, and rollback
conditions:

```bash
griosai agent-rollout \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --stages 0.05,0.25,0.5,1 \
  --min-observation-runs 5 \
  --max-stage-failed-outcomes 0 \
  --require-readiness \
  --require-promotion \
  --require-budget \
  --require-drift \
  --json
```

If no `--candidate-variant` is provided, the command uses the latest promotion
candidate, then the latest comparison winner, then the latest allocation
winner. A rollout is blocked when required readiness, promotion, budget, or
drift evidence is missing or not passing. Rollout artifacts live under:

```text
agent-runs/<experiment>/rollouts/<rollout-id>.json
agent-runs/<experiment>/rollouts/<rollout-id>.md
```

After a stage has produced outcomes, use `agent-rollout-check` to decide
whether to advance, hold, or rollback:

```bash
griosai agent-rollout-check \
  --vault ~/GriosAI-vault \
  --rollout-id rollout-20260530T120000Z-abcdef12 \
  --stage-index 1 \
  --min-stage-outcomes 5 \
  --max-stage-failed-outcomes 0 \
  --min-metric-delta 0.02 \
  --require-budget \
  --require-readiness \
  --require-drift \
  --json
```

The check uses only metadata outcomes logged after the rollout was planned, or
after the prior stage check advanced. With `--require-drift`, a detected latest
drift report rolls the stage back before the challenger is scaled further. It
writes the decision and report under:

```text
agent-runs/<experiment>/rollout-checks/<check-id>.json
agent-runs/<experiment>/rollout-checks/<check-id>.md
```

## Evolution Passes

Use `agent-evolve` when an experiment has outcome evidence and you want one
metadata-only pass to write the next comparison, improvement proposal, memory,
allocation, lane route, budget gate, drift check, promotion, readiness gate,
and optional rollout plan:

```bash
griosai agent-evolve \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --min-trials-per-variant 1 \
  --min-samples-per-variant 1 \
  --max-cost-usd 10 \
  --max-total-tokens 100000 \
  --require-budget \
  --require-route \
  --require-drift \
  --champion-variant claude-primary \
  --min-delta 0.05 \
  --plan-rollout \
  --json
```

The command records each child artifact path and step status in a single ledger.
It catches step failures as sanitized metadata so the operator can see which
part of the loop needs more evidence without storing raw prompts, transcripts,
outputs, or error strings:

```text
agent-runs/<experiment>/evolutions/<evolve-id>.json
agent-runs/<experiment>/evolutions/<evolve-id>.md
```

## Agent Dashboard

Use `agent-dashboard` when a parallel run needs a local operator view instead
of raw JSON inspection:

```bash
griosai agent-dashboard \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --limit 80 \
  --json
```

The command writes a self-contained HTML dashboard under `dashboards/` and a
metadata report under `agent-runs/_reports/`. The dashboard shows control-plane
counts, experiment queues, model mix counts, snapshot counts, variant scoreboards, recommendations, and recent
timeline events. It has no remote assets and does not embed raw prompts,
transcripts, outputs, or errors:

```text
dashboards/<dashboard-id>.html
agent-runs/_reports/<dashboard-id>.json
```

## Self-Improvement Loop

Generate an improvement proposal from accumulated outcomes:

```bash
griosai agent-improve \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --json
```

The proposal summarizes trial counts, success rates, primary metric means, a
winner when enough evidence exists, and a next-loop config with adjusted
variant weights. It also writes a markdown report:

```text
agent-runs/<experiment>/improvements/<loop-id>.json
agent-runs/<experiment>/improvements/<loop-id>.md
```

## Agent Memory

Use `agent-memory` to persist metadata-only lessons from outcomes, failure
codes, usage metadata, and the latest harness evidence. This gives future loops
a durable learning record without storing raw prompts, transcripts, outputs, or
errors:

```bash
griosai agent-memory \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --min-trials-per-variant 3 \
  --max-lessons 12 \
  --json
```

The memory artifact records variant summaries, failure mode counts, lesson
priorities, recommendations, and references to latest comparison, allocation,
improvement, promotion, or budget reports when present.

```text
agent-runs/<experiment>/memories/<memory-id>.json
agent-runs/<experiment>/memories/<memory-id>.md
```

## Hard-Case Curriculum

Use `agent-curriculum` to mine failed, missing-metric, or weak primary-metric
outcomes into a private hard-case backlog for the next focused suite or matrix
wave:

```bash
griosai agent-curriculum \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --metric-threshold 0.8 \
  --max-cases 12 \
  --json
```

The curriculum stores run ids, outcome ids, variant ids, lane ids, case hashes,
metric values, failure codes, and usage aggregates. It does not store raw
prompts or outputs. Operators map the case hashes back to private vault prompts,
then rerun a focused suite or matrix over the weak lanes and variants.

```text
agent-runs/<experiment>/curricula/<curriculum-id>.json
agent-runs/<experiment>/curricula/<curriculum-id>.md
```

Use `agent-curriculum-plan` once the private suite file contains cases matching
the curriculum case ids or hashes. The command filters that suite to hard cases,
includes the baseline plus weak variants, and schedules a focused matrix rerun:

```bash
griosai agent-curriculum-plan \
  --vault ~/GriosAI-vault \
  --config-file examples/agent-experiment.json \
  --suite-file ~/GriosAI-vault/private/hard-cases.json \
  --subject-prefix hardcase-rerun-001 \
  --baseline-variant claude-primary \
  --max-cases 8 \
  --json
```

The resulting suite artifact includes a `curriculum` source block and standard
suite plans. The private suite file can contain prompts; the vault artifacts
only keep prompt hashes and safe metadata.

## Adaptive Allocation

Use `agent-allocate` when outcome evidence should become an auditable traffic
proposal before any config is changed:

```bash
griosai agent-allocate \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --strategy ucb1 \
  --exploration-floor 0.05 \
  --max-share 0.85 \
  --json
```

The allocator supports `ucb1`, `epsilon-greedy`, and `equalize`. It preserves a
minimum exploration share for every variant, can cap a winner's maximum share,
and can apply a cost penalty when usage metadata is present. The output includes
recommended shares, next-loop variant weights, and reasons such as
`explore-under-sampled` or `exploit-measured-reward`.

```text
agent-runs/<experiment>/allocations/<allocation-id>.json
agent-runs/<experiment>/allocations/<allocation-id>.md
```

## Lane-Aware Routing

Use `agent-route` when parallel lanes need different model/provider choices.
The command joins outcome records back to sanitized run metadata, scores each
variant per lane, and writes a route policy overlay without storing raw prompts,
transcripts, outputs, or errors:

```bash
griosai agent-route \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --strategy ucb1 \
  --min-trials-per-lane-variant 3 \
  --json
```

The route artifact records lane policies, per-lane variant shares, winners, and
under-sampled lane/variant cells. Use it after matrix or suite runs when scouts,
builders, reviewers, and adversarial lanes show different model strengths.

```text
agent-runs/<experiment>/routes/<route-id>.json
agent-runs/<experiment>/routes/<route-id>.md
```

## Promotion Proposals

Use `agent-promote` when the improvement loop has enough evidence to decide
whether a challenger should replace the current champion:

```bash
griosai agent-promote \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --champion-variant claude-primary \
  --min-trials-per-variant 3 \
  --min-delta 0.05 \
  --require-passing-gate \
  --require-suite-report \
  --require-pareto \
  --require-budget \
  --require-balance \
  --require-drift \
  --json
```

Promotion proposals are strict review artifacts. They do not rewrite the
experiment config. A proposal can be `ready`, `keep-champion`,
`collect-more-data`, `hold`, `blocked-by-gate`, `blocked-by-suite-report`,
`blocked-by-pareto`, `blocked-by-budget`, `blocked-by-balance`, or
`blocked-by-drift`; ready
proposals include a JSON Patch over traffic weights and traffic salt. Use
`--require-suite-report`, `--require-pareto`, `--require-budget`,
`--require-balance`, and `--require-drift` when a challenger must match the
latest paired suite winner, remain efficient on quality, cost, latency, and
tokens, stay under the latest budget gate, have balanced variant/lane/case
coverage, and avoid recent regression:

```text
agent-runs/<experiment>/promotions/<promotion-id>.json
agent-runs/<experiment>/promotions/<promotion-id>.md
```

GriosAI does not automatically rewrite prompts or promote providers. The loop
produces a reviewable local artifact so the operator can decide what to run
next.

## Privacy Defaults

- Provider credentials are not accepted in experiment settings.
- Subject keys, prompts, lane objectives, guardrail text, outputs, transcripts,
  and raw errors are omitted from manifests and snapshots.
- Prompt and output files are hashed locally; only basenames are stored.
- All artifacts stay in the selected vault and are included in normal vault
  audit and backup workflows.
- Remote provider calls remain an explicit adapter decision outside the core
  harness.
