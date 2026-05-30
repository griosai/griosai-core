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

## Phone Access

The server intentionally binds to localhost by default. For phone viewing, keep
the app local and expose it privately:

```bash
griosai serve --vault ~/GriosAI-vault --host 127.0.0.1 --port 8765
tailscale serve https / http://127.0.0.1:8765
```

Use `tailscale serve`, not a public tunnel, when the goal is private access from
your own devices.

The server prints a per-run bearer token for mutation APIs. Pass
`Authorization: Bearer <token>` when calling `POST /api/analyze-image`. If a
private proxy changes the `Host` header, start the server with
`--allow-host your-device.your-tailnet.ts.net`.

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
- Vault writes are constrained to the selected vault directory.
- Local services default to `127.0.0.1`.
- Mutation APIs require bearer-token auth and `application/json`.
