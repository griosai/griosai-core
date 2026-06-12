# Safety Doctor

`griosai doctor` is a local readiness check. It is intentionally conservative:
it fails on unsafe local URLs, short mutation tokens, invalid notebook packets,
or secret-looking values in `.env.example`.

## Usage

```bash
griosai doctor --vault ~/GriosAI-vault --repo .
griosai doctor --vault ~/GriosAI-vault --repo . --json
```

The command does not mutate the vault. It inspects:

- server host defaults
- mutation token length, if explicitly configured
- Ollama adapter URL syntax and credential-free endpoint safety
- Obsidian URL locality
- MLflow tracking URI locality or explicit remote opt-in
- repo ignore patterns
- `.env.example` placeholder safety
- expected vault directories
- generated notebook packet privacy checks

Exit code is `1` when any check fails. Warnings keep exit code `0` so explicit
non-local choices can remain visible without blocking local work.

## Credential Lease Check

`griosai credential-lease` validates that a runtime secret exists and can be
issued as a scoped, short-lived lease. It prints redacted metadata only.

```bash
read -rsp "Obsidian API key: " GRIOSAI_OBSIDIAN_API_KEY; echo
export GRIOSAI_OBSIDIAN_API_KEY
griosai credential-lease \
  --secret-name obsidian-local-rest \
  --env-var GRIOSAI_OBSIDIAN_API_KEY \
  --scope obsidian:write \
  --client-id local-operator \
  --ttl-seconds 900
```

The broker scaffold does not persist secrets, does not write lease files, and
does not print the leased token.
