# Governance

GriosAI is currently maintained by Gustavo Rios as a pre-1.0 local-first project.
The governance model is intentionally small until there is a broader maintainer
group.

## Maintainer Responsibilities

- Preserve the local-first default architecture.
- Review changes that touch filesystem writes, private data, credential
  handling, localhost binding, backup/restore, notebook packets, MLflow logging,
  Kubernetes exposure, and optional adapters.
- Keep `./scripts/validate.sh` aligned with CI.
- Publish release notes and security advisories for user-visible or safety
  relevant changes.
- Avoid accepting code, docs, screenshots, logs, or examples that contain real
  private data.

## Decision Rules

- Privacy and local safety beat convenience.
- Optional adapters must not become required for core CLI use, tests, or vault
  workflows.
- Public exposure, cloud providers, raw-content export, or credential storage
  require explicit documentation and maintainer review.
- Broken or incomplete feature proposals can be parked when the privacy boundary
  or operator workflow is unclear.

## Maintainer Contact

Use the repository owner contact path on GitHub when available. For private
security reports, prefer GitHub Private Vulnerability Reporting as described in
[SECURITY.md](SECURITY.md).
