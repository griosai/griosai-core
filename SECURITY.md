# Security Policy

GriosAI is designed for private local use first. Treat the vault, generated
dashboards, notebook packets, images, and adapter credentials as sensitive.

## Supported Version

This prototype is pre-1.0. Security fixes should target `main` until release
branches exist.

## Reporting Issues

Do not report vulnerabilities through public GitHub issues, discussions, pull
requests, screenshots, or logs.

Preferred reporting path:

1. Use GitHub Private Vulnerability Reporting on the repository when it is
   available.
2. If private reporting is not enabled for your fork or mirror, contact the
   maintainer listed in [GOVERNANCE.md](GOVERNANCE.md) through a private channel
   and include `SECURITY: GriosAI` in the subject or opening line.

Do not include live credentials, raw screenshots, private vault contents, or
full local paths in reports. Use redacted examples and minimal reproduction
steps.

Expected maintainer response:

- Acknowledge receipt within 3 business days.
- Confirm impact and affected versions before public disclosure.
- Prepare a fix on a private branch or advisory fork when the issue can expose
  private data, credentials, or local files.
- Credit reporters unless they request anonymity.
- Publish release notes and advisories after a fix is available.

## Advisory Scope

Security reports are in scope when they affect default local privacy, localhost
binding, bearer-token mutation protection, path traversal, symlink handling,
vault backup/restore safety, notebook packet redaction, MLflow metadata-only
logging, Obsidian localhost enforcement, Kubernetes private exposure, or secret
handling.

Out of scope for coordinated disclosure:

- Denial-of-service issues requiring local shell access to the same user account.
- Findings that depend on committing private vault contents or credentials.
- Public exposure created by an operator bypassing the documented private
  network defaults without a product defect.

## Security Expectations

- Services bind to `127.0.0.1` by default.
- Mutation APIs require bearer-token authorization.
- Configured server tokens are not printed.
- Optional Obsidian sync rejects non-localhost URLs.
- Optional MLflow tracking logs metadata only and rejects non-local URIs unless
  remote tracking is explicitly allowed.
- Kubernetes manifests use private `ClusterIP` Services, non-root containers,
  read-only root filesystems, and no service-account token automount.
- Credential leases are runtime-only, scoped, short-lived, and redacted.

## Before Public Exposure

Before exposing any service beyond localhost or a private VPN, add and review:

- TLS termination.
- Authentication for every mutation or private-data endpoint.
- Network policy or equivalent perimeter controls.
- Backup and restore plan for the vault and MLflow artifacts.
- Log review proving secrets and raw private content are not emitted.
