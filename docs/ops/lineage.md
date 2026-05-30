# Analysis Lineage

GriosAI writes a JSON lineage manifest for every generated analysis note and
dashboard. The manifest gives local operators and MLflow runs the same stable
`analysis_id` without copying raw summaries, observations, actions, source
paths, or raw JSON into experiment metadata.

## What Is Stored

Lineage manifests live under `lineage/` in the selected vault and contain:

- schema and generation timestamp
- stable SHA-256 `analysis_id`
- slug, model label, source image basename, and count metrics
- privacy declaration for omitted raw fields
- relative artifact paths, byte sizes, and SHA-256 hashes

The manifest is still private metadata. It can reveal filenames, counts, and
content hashes, so keep it inside the vault and backup boundary.

## Verify

Run verification before MLflow logging, backup, export, or handoff:

```bash
griosai lineage-verify --vault ~/GriosAI-vault
griosai lineage-verify --vault ~/GriosAI-vault --json
```

Verification fails when a manifest is malformed, includes raw private field
keys, points outside the vault, references a missing artifact, or has artifact
sizes/hashes that no longer match. Empty or missing lineage is a warning so
older vaults can be migrated by running `griosai init` and creating new
analysis outputs.

## MLflow Correlation

`griosai mlflow-log` logs the same `griosai.analysis_id` as metadata. This lets
you correlate an MLflow run with local vault artifacts while keeping the MLflow
payload metadata-only.
