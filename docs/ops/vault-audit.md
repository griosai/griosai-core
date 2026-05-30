# Vault Audit

`griosai vault-audit` creates a read-only inventory and integrity report for a
GriosAI vault. It does not print note bodies, dashboard HTML, image bytes, raw
notebook packet content, or raw agent transcripts.

## Usage

```bash
griosai vault-audit --vault ~/GriosAI-vault
griosai vault-audit --vault ~/GriosAI-vault --json
```

The JSON output includes:

- vault path
- per-directory file and byte totals
- relative file paths
- file sizes
- SHA-256 hashes
- findings for missing layout directories, symlinks, special files, oversized
  files, and secret-looking text patterns

The command exits with code `1` only for fail-level findings, such as a missing
vault, missing layout directory, or symlink inside the vault. Secret-looking text
patterns are warnings because private notes may intentionally contain sensitive
material; review those findings before exporting, syncing, or sharing a vault.

## When To Run

- Before creating a backup.
- Before moving a vault between machines.
- Before pushing generated artifacts into any external tool.
- During release smoke tests.

Audit output can reveal private filenames and content hashes. Treat audit JSON
as sensitive metadata.
