# Obsidian Local REST Integration

GriosAI can optionally write generated markdown notes through the Obsidian Local
REST API plugin. This is an adapter, not a dependency: the core vault workflow
continues to work with plain files when Obsidian is closed.

## Default Posture

- URL defaults to `https://127.0.0.1:27124`.
- Non-localhost URLs are rejected.
- API keys are read at runtime from an environment variable or CLI flag.
- Existing remote notes are not clobbered unless `--overwrite` is explicit.
- The adapter writes markdown notes only; it does not upload raw logs, images,
  notebook packets, or secrets.

## Runtime Setup

```bash
read -rsp "Obsidian API key: " GRIOSAI_OBSIDIAN_API_KEY; echo
export GRIOSAI_OBSIDIAN_API_KEY
griosai obsidian-sync --json-file ./examples/sample-analysis.json
```

If the plugin uses a self-signed certificate that is not trusted locally:

```bash
griosai obsidian-sync \
  --json-file ./examples/sample-analysis.json \
  --insecure-skip-tls-verify
```

That flag only relaxes TLS verification for the localhost adapter. It does not
permit a remote URL.

## Configuration

```bash
GRIOSAI_OBSIDIAN_URL=https://127.0.0.1:27124
GRIOSAI_OBSIDIAN_API_KEY=
GRIOSAI_OBSIDIAN_VERIFY_TLS=true
GRIOSAI_OBSIDIAN_TIMEOUT=10
```

Keep real API keys out of `.env.example`, shell history, and git.

## Paths

`obsidian-sync` writes to `GriosAI/notes/<slug>.md` by default. Paths are always
relative to the Obsidian vault and must not include absolute paths, parent
segments, hidden segments, Windows drive letters, or non-markdown suffixes.
