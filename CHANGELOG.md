# Changelog

GriosAI follows semantic versioning after the first public release. Before
`1.0.0`, minor versions may change CLI details while preserving the documented
local-first and privacy defaults whenever possible.

## Unreleased

### Added

- Open-source support, governance, code of conduct, and issue template
  documentation.
- Documentation link validation in the local test suite.

### Changed

- README and contributing setup now use public clone paths instead of
  machine-specific local paths.
- Release checklist now includes package build, artifact, and publication
  readiness steps.

### Fixed

- Dashboard serving now rejects symlinked dashboard entries with a structured
  error instead of closing the request with an uncaught path-safety exception.
- MLflow and default lineage metadata now use stable analysis-ID slugs instead
  of title-derived identifiers.
- Lineage source-image metadata drops URL query strings and fragments.
- Client-controlled malformed request bodies and directory image paths now
  return typed API errors.
- Server log redaction now covers bearer-token strings.
- The container image no longer starts a broadly bound server by default.
