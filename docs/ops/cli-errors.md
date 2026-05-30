# CLI Error Handling

`griosai` commands should be usable in scripts without exposing raw Python
tracebacks for expected operator failures.

## Behavior

Expected failures return a nonzero exit code and write a concise message to
stderr:

```bash
griosai add-analysis --vault ~/GriosAI-vault --json-file /missing/file.json
```

Output shape:

```text
error: ...
```

This applies to invalid JSON, schema validation failures, missing files, unsafe
paths, local adapter failures, backup/restore validation errors, and credential
lease validation errors.

Unexpected programming defects should still be fixed in code and covered by
tests; the CLI boundary is for operator-facing failures, not a substitute for
review.
