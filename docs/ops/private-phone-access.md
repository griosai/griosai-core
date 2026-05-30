# Private Phone Access

GriosAI serves dashboards on `127.0.0.1` by default. Keep that default unless
you have a concrete private-network reason to do otherwise.

## Local Laptop Preview

```bash
griosai serve --vault ~/GriosAI-vault
```

Open `http://127.0.0.1:8765` on the same machine.

## Tailscale Preview

Use Tailscale private serve, not a public tunnel:

```bash
griosai serve --vault ~/GriosAI-vault --host 127.0.0.1 --port 8765
tailscale serve https / http://127.0.0.1:8765
```

If a private proxy rewrites the `Host` header, allow exactly that tailnet
hostname:

```bash
griosai serve \
  --vault ~/GriosAI-vault \
  --allow-host your-device.your-tailnet.ts.net
```

## Mutation APIs

The server prints a per-run bearer token. Only mutation endpoints require it:

```bash
curl \
  -H "Authorization: Bearer $GRIOSAI_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"image_path":"/absolute/path/to/vault/images/example.png"}' \
  http://127.0.0.1:8765/api/analyze-image
```

`image_path` must be inside the selected vault's `images/` directory and must
use a supported image extension. The server rejects non-JSON mutation bodies,
missing content lengths, disallowed hosts, and disallowed origins.

## Avoid

- Public tunnels for private dashboards.
- Binding to `0.0.0.0` as a convenience shortcut.
- Putting bearer tokens in URLs.
- Exposing raw vault directories or raw logs through a generic static server.
