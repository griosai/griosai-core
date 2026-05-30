# GriosAI

Local-first AI brain and dashboard runner for private image-to-insight workflows.

This repo starts with the safe default from the Claude spec: keep the brain in a
plain-file vault, call local Ollama models when available, generate self-contained
HTML dashboards, and serve them from `127.0.0.1` so phone access can be layered
through Tailscale or a trusted local network later.

## Quickstart

```bash
cd /Users/gustavorios/griosai
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
griosai analyze-image ./examples/sample.png --vault ~/GriosAI-vault --model qwen2.5vl:7b
```

The command writes a markdown note and HTML dashboard into the vault. If Ollama
is unavailable, the rest of the project still works.

## Manual Analysis

You can import a structured JSON payload without any model:

```bash
griosai add-analysis --vault ~/GriosAI-vault --json-file ./examples/sample-analysis.json
```

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
timestamps, and safe image basenames, not raw summaries, observations, actions,
or raw JSON.

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
test, Kubernetes manifest rendering when `kubectl` is available, and a
secret-pattern scan.

See [docs/ops/validation.md](docs/ops/validation.md) and
[docs/ops/release-checklist.md](docs/ops/release-checklist.md).

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
- `GET /dashboards/<file.html>`: dashboard HTML from the vault.
- `POST /api/analyze-image`: JSON body with `image_path`, optional `prompt`,
  and optional `model`; runs the local Ollama adapter.

## Safety Defaults

- No secrets are required or stored.
- No cloud provider is configured by default.
- HTML dashboards use escaped content and no remote assets.
- Notebook packets redact local paths and likely secrets before writing.
- Vault backups verify file hashes, skip symlinks, and restore without
  clobbering by default.
- Obsidian sync is optional, token-based, and restricted to localhost URLs.
- MLflow tracking is optional, metadata-only, and localhost-only unless
  explicitly allowed.
- Kubernetes manifests default to private ClusterIP services and non-root pods.
- Kubernetes NetworkPolicies restrict app and MLflow traffic when supported by
  the cluster CNI.
- HTTP responses include no-store, nosniff, referrer, and CSP safety headers.
- Credential leases are runtime-only, scoped, short-lived, and redacted in logs.
- `griosai doctor` checks local config, vault layout, packets, and placeholders.
- Vault writes are constrained to the selected vault directory.
- Local services default to `127.0.0.1`.
- Mutation APIs require bearer-token auth and `application/json`.
