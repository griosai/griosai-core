# REST API

GriosAI exposes a small localhost/private-network API from `griosai serve`.
The machine-readable contract is available from both the CLI and server:

```bash
griosai openapi
curl http://127.0.0.1:8765/api/openapi.json
```

## Endpoints

- `GET /api/health`: server and vault readiness.
- `GET /api/notes`: generated markdown note summaries.
- `GET /api/dashboards`: generated dashboard file summaries.
- `GET /api/openapi.json`: OpenAPI contract.
- `GET /dashboards/<file.html>`: generated dashboard HTML.
- `POST /api/analyze-image`: analyze a vault image through the configured
  local Ollama adapter.

Mutation endpoints require `Authorization: Bearer <token>` and
`Content-Type: application/json`. `POST /api/analyze-image` also requires
`image_path` to point inside the selected vault's `images/` directory.

The API is intended for localhost or private-network access. Public exposure
requires a separate review of authentication, TLS, logs, and network policy.
