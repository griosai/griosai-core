# Analysis Input Schema

GriosAI accepts one local JSON object as the input contract for manual import,
Notebook packet generation, Obsidian sync, and MLflow metadata logging.

Print the machine-readable JSON Schema:

```bash
griosai analysis-schema
```

Validate a payload before writing vault artifacts:

```bash
griosai validate-analysis --json-file ./examples/sample-analysis.json
griosai validate-analysis --json-file ./examples/sample-analysis.json --json
```

## Required Content

Each payload must include:

- `title` or `headline`
- `summary` or `description`

Optional normalized fields are:

- `observations` or `findings`
- `actions` or `recommendations`
- `model`
- `source_image`

Observation/action fields may be either a string or an array of strings.
Unknown top-level fields are preserved in local raw notes but reported as
warnings because normalized outputs ignore them.

## Guardrails

Validation fails when the payload is not a JSON object, required text is
missing, normalized fields have the wrong type, strings/lists/objects exceed
built-in local limits, or nesting is too deep.

Secret-looking values are warnings, not failures, because a private local vault
may intentionally contain sensitive notes. Treat warnings as a review prompt
before export, sync, or MLflow logging.
