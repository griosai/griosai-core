# Security Policy

GriosAI is designed for private local use first. Treat the vault, generated
dashboards, notebook packets, images, and adapter credentials as sensitive.

## Supported Version

This prototype is pre-1.0. Security fixes should target `main` until release
branches exist.

## Reporting Issues

There is no public security mailbox configured yet because the repository has
not been pushed to GitHub. Until one exists, report issues directly to the repo
owner through the private project channel used to create this repo.

Do not include live credentials, raw screenshots, private vault contents, or
full local paths in reports. Use redacted examples and minimal reproduction
steps.

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
