# GriosAI

Local-first AI brain and dashboard runner for private image-to-insight workflows.

GriosAI keeps the brain in a plain-file vault, calls local Ollama models when
available, generates self-contained HTML dashboards, and serves them from
`127.0.0.1` by default so private phone access can be layered through Tailscale
or another trusted private network later.

## Project Status

GriosAI is pre-1.0 local-first infrastructure. The core CLI, vault layout,
dashboard renderer, REST contract, backup/restore, lineage manifests, vault
audit, and privacy-preserving optional adapters are in place. Public exposure,
cloud providers, and raw-content tracking are intentionally opt-in and must be
reviewed before use.

## Safety Model

- Vaults stay in user-selected plain directories, not hidden service databases.
- Services bind to `127.0.0.1` unless the operator explicitly chooses another
  host.
- Mutation APIs require bearer-token authorization.
- Notebook packets, MLflow runs, and lineage manifests avoid raw private
  content by default.
- Ollama, Obsidian, MLflow, Kubernetes, and Tailscale are optional adapters; the
  local CLI and tests run without them.

## Documentation Map

- [REST API contract](docs/api/rest-api.md)
- [Analysis input schema](docs/spec/analysis-input-schema.md)
- [Backup and restore](docs/ops/backup-restore.md)
- [Vault audit](docs/ops/vault-audit.md)
- [Lineage manifests](docs/ops/lineage.md)
- [Agent harness](docs/ops/agent-harness.md)
- [Private phone access](docs/ops/private-phone-access.md)
- [Validation gate](docs/ops/validation.md)
- [Release checklist](docs/ops/release-checklist.md)
- [Full docs index](docs/README.md)

## Quickstart

```bash
git clone https://github.com/gustavorios/griosai.git
cd griosai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

griosai init --vault ~/GriosAI-vault
griosai sample --vault ~/GriosAI-vault
griosai add-analysis --vault ~/GriosAI-vault --json-file ./examples/sample-analysis.json
griosai serve --vault ~/GriosAI-vault
```

Open `http://127.0.0.1:8765` on the same machine.

## Optional Local Vision

If Ollama is installed and running locally, pull a vision model and analyze an
image without sending it to a cloud provider:

```bash
ollama pull qwen2.5vl:7b
cp /path/to/private-image.png ~/GriosAI-vault/images/
griosai analyze-image ~/GriosAI-vault/images/private-image.png \
  --vault ~/GriosAI-vault \
  --model qwen2.5vl:7b
```

The command writes a markdown note and HTML dashboard into the vault. If Ollama
is unavailable, the rest of the project still works.

## Manual Analysis

You can import a structured JSON payload without any model:

```bash
griosai validate-analysis --json-file ./examples/sample-analysis.json
griosai add-analysis --vault ~/GriosAI-vault --json-file ./examples/sample-analysis.json
```

Print the accepted payload contract:

```bash
griosai analysis-schema
```

## Cross-Model Agent Harness

Use the agent harness to A/B test Claude, OpenAI, Ollama, or custom runner
variants without making any provider required by the core CLI:

```bash
griosai agent-run \
  --vault ~/GriosAI-vault \
  --config-file ./examples/agent-experiment.json \
  --subject local-thread-001 \
  --prompt-file ./private-prompt.md \
  --json
```

Call the selected adapter outside the core harness, then log metrics without
raw transcripts:

```bash
griosai agent-score \
  --vault ~/GriosAI-vault \
  --run-id <run-id> \
  --scores-json '{"correctness": 0.9, "safety": 1, "efficiency": 0.7}' \
  --usage-json '{"prompt_tokens": 1200, "completion_tokens": 400, "latency_ms": 2100, "cost_usd": 0.03}'

griosai agent-outcome \
  --vault ~/GriosAI-vault \
  --run-id <run-id> \
  --status succeeded \
  --metrics-json '{"quality": 0.86}' \
  --usage-json '{"total_tokens": 1600, "latency_ms": 2100, "cost_usd": 0.03}'

griosai agent-ingest --vault ~/GriosAI-vault --results-file ./worker-results.json

griosai agent-compare --vault ~/GriosAI-vault --experiment cross-model-agent
griosai agent-balance --vault ~/GriosAI-vault --experiment cross-model-agent --suite-id <suite-id> --dimensions variant,lane,case
griosai agent-decision --vault ~/GriosAI-vault --experiment cross-model-agent --baseline-variant claude-primary
griosai agent-drift --vault ~/GriosAI-vault --experiment cross-model-agent --baseline-window 5 --recent-window 5
griosai agent-power --vault ~/GriosAI-vault --experiment cross-model-agent --min-detectable-effect 0.05
griosai agent-pipeline --vault ~/GriosAI-vault --config-file ./examples/agent-experiment.json --pipeline-file ./examples/agent-pipeline.json --subject-prefix ship-loop-001
griosai agent-pipeline-advance --vault ~/GriosAI-vault --pipeline-id <pipeline-id>
griosai agent-arena --vault ~/GriosAI-vault --config-file ./examples/agent-experiment.json --subject model-arena-001
griosai agent-arena-report --vault ~/GriosAI-vault --arena-id <arena-id>
griosai agent-judge-panel --vault ~/GriosAI-vault --config-file ./examples/agent-experiment.json --plan-id <plan-id>
griosai agent-judge-report --vault ~/GriosAI-vault --panel-id <panel-id>
griosai agent-schedule --vault ~/GriosAI-vault --experiment cross-model-agent --subject next-batch-001 --max-runs 24
griosai agent-schedule-report --vault ~/GriosAI-vault --schedule-id <schedule-id>
griosai agent-leaderboard --vault ~/GriosAI-vault --experiment cross-model-agent
griosai agent-config --vault ~/GriosAI-vault --experiment cross-model-agent --source auto
griosai agent-improve --vault ~/GriosAI-vault --experiment cross-model-agent
griosai agent-memory --vault ~/GriosAI-vault --experiment cross-model-agent
griosai agent-curriculum --vault ~/GriosAI-vault --experiment cross-model-agent --metric-threshold 0.8
griosai agent-curriculum-plan --vault ~/GriosAI-vault --config-file ./examples/agent-experiment.json --suite-file ./private-hard-cases.json --subject-prefix hardcase-rerun-001
griosai agent-allocate --vault ~/GriosAI-vault --experiment cross-model-agent --strategy ucb1
griosai agent-route --vault ~/GriosAI-vault --experiment cross-model-agent --strategy ucb1
griosai agent-evolve --vault ~/GriosAI-vault --experiment cross-model-agent --require-budget --require-drift
griosai agent-readiness --vault ~/GriosAI-vault --experiment cross-model-agent --require-comparison --require-balance --require-drift
griosai agent-rollout --vault ~/GriosAI-vault --experiment cross-model-agent --require-readiness --require-drift
griosai agent-rollout-check --vault ~/GriosAI-vault --rollout-id <rollout-id> --stage-index 1 --require-drift
```

For parallel lanes, create a fanout plan and merge the resulting outcomes:

```bash
griosai agent-plan \
  --vault ~/GriosAI-vault \
  --config-file ./examples/agent-experiment.json \
  --subject local-thread-001 \
  --lanes scout,builder,reviewer,adversary \
  --json

griosai agent-matrix \
  --vault ~/GriosAI-vault \
  --config-file ./examples/agent-experiment.json \
  --subject benchmark-thread-001 \
  --lanes scout,builder,reviewer \
  --json
griosai agent-arena \
  --vault ~/GriosAI-vault \
  --config-file ./examples/agent-experiment.json \
  --subject model-arena-001 \
  --lanes reviewer \
  --json

griosai agent-suite \
  --vault ~/GriosAI-vault \
  --config-file ./examples/agent-experiment.json \
  --suite-file ./examples/agent-suite.json \
  --subject-prefix regression-loop-001 \
  --lanes scout,reviewer \
  --json

griosai agent-suite-report --vault ~/GriosAI-vault --suite-id <suite-id>
griosai agent-pipeline --vault ~/GriosAI-vault --config-file ./examples/agent-experiment.json --pipeline-file ./examples/agent-pipeline.json --subject-prefix ship-loop-001
griosai agent-pipeline-advance --vault ~/GriosAI-vault --pipeline-id <pipeline-id>
griosai agent-arena-report --vault ~/GriosAI-vault --arena-id <arena-id>
griosai agent-judge-panel --vault ~/GriosAI-vault --config-file ./examples/agent-experiment.json --plan-id <plan-id>
griosai agent-judge-report --vault ~/GriosAI-vault --panel-id <panel-id>
griosai agent-preflight --vault ~/GriosAI-vault --suite-id <suite-id> --require-cross-model --require-lane-coverage --require-variant-coverage
griosai agent-hold --vault ~/GriosAI-vault --experiment cross-model-agent --scopes dispatch --reason "pause worker wave"
griosai agent-hold --vault ~/GriosAI-vault --experiment cross-model-agent --scopes all --reason "pause dispatch and model gates"
griosai agent-release --vault ~/GriosAI-vault --experiment cross-model-agent --hold-id <hold-id> --reason "resume worker wave"
griosai agent-quarantine --vault ~/GriosAI-vault --experiment cross-model-agent --providers openai --reason "provider incident"
griosai agent-circuit --vault ~/GriosAI-vault --experiment cross-model-agent --group-by provider --max-failure-rate 0.25 --quarantine-on-trip
griosai agent-unquarantine --vault ~/GriosAI-vault --experiment cross-model-agent --quarantine-id <quarantine-id> --reason "provider recovered"
griosai agent-claim --vault ~/GriosAI-vault --plan-id <plan-id> --client-id worker-1 --claim-strategy lane-balanced
griosai agent-dispatch --vault ~/GriosAI-vault --plan-id <plan-id> --client-prefix worker --count 8 --claim-strategy lane-variant-balanced
griosai agent-orchestrate --vault ~/GriosAI-vault --suite-id <suite-id> --client-prefix worker --max-concurrency 12 --batch-size 4 --claim-strategy lane-variant-balanced
griosai agent-cycle --vault ~/GriosAI-vault --suite-id <suite-id> --client-prefix worker --max-concurrency 12 --claim-strategy lane-variant-balanced
griosai agent-loop --vault ~/GriosAI-vault --suite-id <suite-id> --client-prefix worker --max-cycles 3 --claim-strategy lane-variant-balanced
griosai agent-capacity --vault ~/GriosAI-vault --suite-id <suite-id> --max-concurrency 12
griosai agent-slo --vault ~/GriosAI-vault --suite-id <suite-id> --min-completion-rate 0.95 --max-failure-rate 0.05
griosai agent-mix --vault ~/GriosAI-vault --experiment cross-model-agent --require-local-provider
griosai agent-work --vault ~/GriosAI-vault --claim-id <claim-id>
griosai agent-heartbeat --vault ~/GriosAI-vault --claim-id <claim-id> --client-id worker-1
griosai agent-retry --vault ~/GriosAI-vault --run-id <run-id> --reason adapter_timeout
griosai agent-recover --vault ~/GriosAI-vault --experiment cross-model-agent --max-retries 8
griosai agent-merge --vault ~/GriosAI-vault --plan-id <plan-id>
griosai agent-gate --vault ~/GriosAI-vault --plan-id <plan-id> --metric-threshold 0.85
griosai agent-quorum --vault ~/GriosAI-vault --plan-id <plan-id> --min-agreement-ratio 0.75
griosai agent-adjudicate --vault ~/GriosAI-vault --plan-id <plan-id>
griosai agent-audit --vault ~/GriosAI-vault
griosai agent-manifest --vault ~/GriosAI-vault --experiment cross-model-agent
griosai agent-verify-manifest --vault ~/GriosAI-vault --manifest-id <manifest-id>
griosai agent-snapshot --vault ~/GriosAI-vault --experiment cross-model-agent --fail-on-change
griosai agent-compare --vault ~/GriosAI-vault --experiment cross-model-agent
griosai agent-drift --vault ~/GriosAI-vault --experiment cross-model-agent --max-metric-drop 0.05
griosai agent-decision \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --baseline-variant claude-primary \
  --candidate-variant openai-backup \
  --min-samples-per-variant 3 \
  --min-delta 0.05 \
  --confidence-threshold 0.8
griosai agent-power \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --baseline-variant claude-primary \
  --min-detectable-effect 0.05 \
  --max-cost-usd 10 \
  --max-total-tokens 100000
griosai agent-schedule \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --subject benchmark-next-batch-001 \
  --lanes scout,reviewer \
  --max-runs 24
griosai agent-schedule-report \
  --vault ~/GriosAI-vault \
  --schedule-id schedule-20260530T120000Z-example
griosai agent-leaderboard --vault ~/GriosAI-vault --experiment cross-model-agent
griosai agent-config --vault ~/GriosAI-vault --experiment cross-model-agent --source auto
griosai agent-timeline --vault ~/GriosAI-vault
griosai agent-watchdog --vault ~/GriosAI-vault
griosai agent-budget \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --max-cost-usd 10 \
  --max-total-tokens 100000 \
  --max-mean-latency-ms 2000
griosai agent-dashboard --vault ~/GriosAI-vault --experiment cross-model-agent
griosai agent-promote \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --require-suite-report \
  --require-pareto \
  --require-budget \
  --require-balance \
  --require-drift
griosai agent-readiness \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --require-comparison \
  --require-budget \
  --require-route \
  --require-memory \
  --require-quorum \
  --require-promotion \
  --require-balance \
  --require-drift
griosai agent-rollout \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --stages 0.05,0.25,0.5,1 \
  --require-readiness \
  --require-promotion \
  --require-budget \
  --require-drift
griosai agent-rollout-check \
  --vault ~/GriosAI-vault \
  --rollout-id <rollout-id> \
  --stage-index 1 \
  --min-stage-outcomes 5 \
  --require-budget \
  --require-readiness \
  --require-drift
griosai agent-evolve \
  --vault ~/GriosAI-vault \
  --experiment cross-model-agent \
  --require-budget \
  --require-route \
  --require-drift \
  --plan-rollout
griosai agent-status --vault ~/GriosAI-vault
```

Run, plan, matrix-plan, pipeline, pipeline-advance, arena, arena-report, judge-panel, judge-report, suite, suite-report, preflight, hold, release, quarantine, circuit, unquarantine, claim, heartbeat, retry,
dispatch, orchestration cycle, bounded loop, capacity plan, SLO gate, model-mix gate, work-packet, scorecard, outcome,
compare, balance, decision, drift, power, schedule, leaderboard, config proposal, memory, curriculum, curriculum-plan, lane route, merge, gate, quorum, adjudication, ingest, audit, manifest, manifest verification, snapshot, timeline,
watchdog, budget, readiness, rollout, rollout check, dashboard, promotion, evolve, status, and improvement-loop artifacts live under
`agent-runs/`, with HTML dashboards under `dashboards/`. See
[docs/ops/agent-harness.md](docs/ops/agent-harness.md).

## Notebook Packets

NotebookLM and notebook workflows should receive sanitized source packets, not
raw logs or private dashboard state. Generate a packet from any analysis JSON:

```bash
griosai notebook-packet --vault ~/GriosAI-vault --json-file ./examples/sample-analysis.json
```

This writes `index.md`, `tables.csv`, `report.html`, and `manifest.json` under
`~/GriosAI-vault/notebook-packets/`. The packet contract is available from
Python too:

```python
from griosai.notebook import NotebookConnectorAdapter

adapter = NotebookConnectorAdapter("~/GriosAI-vault")
packet = adapter.write_packet({"title": "Notebook Source", "summary": "Local first"})
packet.connector_payload()
```

## Backup And Restore

Create a private zip backup of the local vault:

```bash
griosai backup --vault ~/GriosAI-vault --output ~/Backups
```

Restore into a new vault without clobbering existing files:

```bash
griosai restore ~/Backups/griosai-vault-20260530T120000Z.zip \
  --vault ~/GriosAI-vault-restored
```

Backups include a manifest with file sizes and SHA-256 digests. Restore rejects
unsafe paths, symlinks, unexpected entries, digest mismatches, and existing
files unless `--overwrite` is set.

```bash
griosai verify-backup ~/Backups/griosai-vault-20260530T120000Z.zip
```

See [docs/ops/backup-restore.md](docs/ops/backup-restore.md).

## Vault Audit

Inventory the vault without printing raw note, dashboard, image, or packet
content:

```bash
griosai vault-audit --vault ~/GriosAI-vault --json
```

The audit reports file counts, byte totals, SHA-256 hashes, layout findings,
symlinks, oversized files, and secret-looking text warnings.

See [docs/ops/vault-audit.md](docs/ops/vault-audit.md).

## Analysis Lineage

Generated notes and dashboards also get a privacy-preserving lineage manifest:

```bash
griosai lineage-verify --vault ~/GriosAI-vault --json
```

Lineage manifests bind local artifacts to a stable `analysis_id`, byte sizes,
and SHA-256 hashes without storing raw summaries, observations, actions, source
paths, or raw JSON in tracking metadata.

See [docs/ops/lineage.md](docs/ops/lineage.md).

## Optional Obsidian Sync

If the Obsidian Local REST API plugin is running, write the same markdown note
through localhost only:

```bash
read -rsp "Obsidian API key: " GRIOSAI_OBSIDIAN_API_KEY; echo
export GRIOSAI_OBSIDIAN_API_KEY
griosai obsidian-sync --json-file ./examples/sample-analysis.json
```

The default URL is `https://127.0.0.1:27124`. If your local plugin certificate is
self-signed and not trusted by macOS, add `--insecure-skip-tls-verify`; the
adapter still rejects non-localhost URLs.

See [docs/integrations/obsidian-local-rest.md](docs/integrations/obsidian-local-rest.md).

## Optional MLflow Tracking

MLflow support is metadata-only by default: it logs counts, model labels, slug,
stable `analysis_id`, timestamps, and safe image basenames, not raw summaries,
observations, actions, or raw JSON.

Run a local MLflow Tracking server, then log an analysis:

```bash
python -m pip install "mlflow>=3.1"
mlflow server --host 127.0.0.1 --port 5000

griosai mlflow-log --json-file ./examples/sample-analysis.json
```

The default tracking URI is `http://127.0.0.1:5000`. Non-local tracking URIs
are rejected unless `GRIOSAI_MLFLOW_ALLOW_REMOTE=true` or
`--allow-remote-tracking` is set.

## Phone Access

The server intentionally binds to localhost by default. For phone viewing, keep
the app local and expose it privately:

```bash
griosai serve --vault ~/GriosAI-vault --host 127.0.0.1 --port 8765
tailscale serve https / http://127.0.0.1:8765
```

Use `tailscale serve`, not a public tunnel, when the goal is private access from
your own devices.

The server prints a generated per-run bearer token for mutation APIs when no
token is configured. Pass `Authorization: Bearer <token>` when calling
`POST /api/analyze-image`. If a private proxy changes the `Host` header, start
the server with
`--allow-host your-device.your-tailnet.ts.net`.

See [docs/ops/private-phone-access.md](docs/ops/private-phone-access.md).

## Kubernetes And Open Source Ops

The repo includes a container image definition and Kustomize manifests for a
private Kubernetes deployment:

```bash
docker build -f Containerfile -t ghcr.io/gustavorios/griosai:0.1.0 .
kubectl apply -k deploy/kubernetes/base
kubectl -n griosai rollout status deployment/griosai
kubectl -n griosai port-forward svc/griosai 8765:8765
```

The container image prints CLI help by default rather than starting a broadly
bound server. For a local Docker smoke test, publish the host port on loopback
and make the in-container broad bind explicit:

```bash
docker run --rm \
  -p 127.0.0.1:8765:8765 \
  -v "$HOME/GriosAI-vault:/data/vault" \
  ghcr.io/gustavorios/griosai:0.1.0 \
  serve --vault /data/vault --host 0.0.0.0 --allow-host 127.0.0.1
```

The service is `ClusterIP`, not public. The pod runs as non-root, uses a
read-only root filesystem, mounts a PVC-backed vault, disables service-account
token mounting, probes `/api/health` with an allowed local Host header, and
ships NetworkPolicies for clusters whose CNI enforces them.

An optional OSS MLflow tracking server manifest is available under
`deploy/kubernetes/mlflow/`. It is intentionally cluster-private and suitable
for a private lab; move production MLflow to a real database and object store
before treating it as HA infrastructure.

See [docs/ops/kubernetes-mlflow.md](docs/ops/kubernetes-mlflow.md).

## Validation

Run the same gate locally that CI runs:

```bash
./scripts/validate.sh
```

This covers unit tests, bytecode compilation, whitespace checks, a doctor smoke
test, analysis schema validation, Kubernetes manifest rendering when `kubectl`
is available, and a secret-pattern scan.

See [docs/ops/validation.md](docs/ops/validation.md) and
[docs/ops/release-checklist.md](docs/ops/release-checklist.md).

Expected operator errors, such as invalid JSON, missing files, unsafe paths, or
unreachable local adapters, return nonzero exit codes with concise stderr
messages instead of Python tracebacks.

## Contributing And Support

Start with [CONTRIBUTING.md](CONTRIBUTING.md), [SUPPORT.md](SUPPORT.md),
[SECURITY.md](SECURITY.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and
[GOVERNANCE.md](GOVERNANCE.md). The pull request template and issue templates
ask for validation evidence and privacy-boundary notes because this project
handles local personal data.

## Safety Doctor And Credential Leases

Run the local readiness checker before exposing a dashboard or syncing through
an adapter:

```bash
griosai doctor --vault ~/GriosAI-vault --repo .
```

For runtime credentials, validate a scoped lease without printing or persisting
the secret:

```bash
read -rsp "Obsidian API key: " GRIOSAI_OBSIDIAN_API_KEY; echo
export GRIOSAI_OBSIDIAN_API_KEY
griosai credential-lease \
  --secret-name obsidian-local-rest \
  --env-var GRIOSAI_OBSIDIAN_API_KEY \
  --scope obsidian:write \
  --client-id local-operator
```

## Endpoints

- `GET /`: local dashboard index.
- `GET /api/health`: server and vault status.
- `GET /api/notes`: generated markdown note summaries.
- `GET /api/dashboards`: generated dashboard files.
- `GET /api/openapi.json`: machine-readable REST contract.
- `GET /dashboards/<file.html>`: dashboard HTML from the vault.
- `POST /api/analyze-image`: JSON body with `image_path`, optional `prompt`,
  and optional `model`; runs the local Ollama adapter and returns note,
  dashboard, and lineage paths.

Print the same contract from the CLI:

```bash
griosai openapi
```

Print the analysis import contract:

```bash
griosai analysis-schema
```

See [docs/api/rest-api.md](docs/api/rest-api.md).

## Safety Defaults

- No secrets are required or stored.
- No cloud provider is configured by default.
- Analysis imports are validated against a documented local schema before
  writing vault artifacts or handoff packets.
- HTML dashboards use escaped content and no remote assets.
- Notebook packets redact local paths and likely secrets before writing.
- Lineage manifests preserve artifact hashes and MLflow correlation IDs without
  exporting raw analysis content.
- Agent harness logs hash prompts and outputs, compares model variants by
  metadata, tracks usage and cost, reports Pareto-efficient variants, writes
  sequential A/B stop/continue decisions, mines metadata-only hard-case
  curricula, writes rubric scorecards, and produces reviewable improvement and
  promotion proposals into the vault.
- Vault backups verify file hashes, skip symlinks, and restore without
  clobbering by default.
- `griosai vault-audit` inventories file hashes and risky vault metadata without
  printing raw content.
- Obsidian sync is optional, token-based, and restricted to localhost URLs.
- MLflow tracking is optional, metadata-only, and localhost-only unless
  explicitly allowed.
- Kubernetes manifests default to private ClusterIP services and non-root pods.
- Kubernetes NetworkPolicies restrict app and MLflow traffic when supported by
  the cluster CNI.
- HTTP responses include no-store, nosniff, referrer, and CSP safety headers.
- Credential leases are runtime-only, scoped, short-lived, and redacted in logs.
- CLI commands return concise nonzero errors for expected operator failures
  without printing stack traces.
- `griosai doctor` checks local config, vault layout, packets, and placeholders.
- Vault writes are constrained to the selected vault directory.
- Local services default to `127.0.0.1`.
- Mutation APIs require bearer-token auth and `application/json`.
