# Support

GriosAI is pre-1.0 local-first software. Support is best-effort and should not
include raw private vault contents, screenshots, credentials, `.env` files, or
full local paths.

## Where To Ask

- Usage questions: open a GitHub discussion when discussions are enabled, or a
  question issue using the available template.
- Reproducible bugs: open a bug report with command output, Python version,
  platform, and redacted reproduction steps.
- Feature requests: open a feature request and describe the privacy boundary for
  any adapter, network exposure, or data export.
- Security issues: follow [SECURITY.md](SECURITY.md). Do not open a public issue.

## What To Include

- GriosAI version or commit SHA.
- Python version and operating system.
- The exact command that failed, with private paths replaced by placeholders.
- Whether the issue touches a vault, backup archive, notebook packet, dashboard,
  MLflow run, Obsidian sync, Kubernetes deployment, or local server.
- Validation output from `./scripts/validate.sh` when relevant.

## Maintenance Expectations

Maintainers prioritize privacy regressions, data-loss risks, path traversal,
credential leaks, broken validation, and documentation that can cause unsafe
operator behavior. Feature work that introduces cloud services, public exposure,
or raw-content export requires explicit design review before implementation.
