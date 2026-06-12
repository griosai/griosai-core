from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .privacy import OPENAI_STYLE_KEY_RE, SECRET_VALUE_RE


ANALYSIS_SCHEMA_VERSION = "griosai.analysis-input.v1"
MAX_ANALYSIS_JSON_BYTES = 1_000_000
MAX_ANALYSIS_STRING_CHARS = 20_000
MAX_ANALYSIS_LIST_ITEMS = 500
MAX_ANALYSIS_OBJECT_KEYS = 500
MAX_ANALYSIS_DEPTH = 12


@dataclass(frozen=True)
class AnalysisValidationFinding:
    severity: str
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }


class AnalysisValidationError(ValueError):
    def __init__(self, findings: tuple[AnalysisValidationFinding, ...]) -> None:
        self.findings = findings
        super().__init__(format_analysis_validation_text(findings))


def analysis_input_schema() -> dict[str, Any]:
    return deepcopy(_ANALYSIS_INPUT_SCHEMA)


def analysis_input_schema_json() -> str:
    return json.dumps(analysis_input_schema(), indent=2, sort_keys=True)


def validate_analysis_payload(
    payload: object,
    *,
    source_bytes: int | None = None,
) -> tuple[AnalysisValidationFinding, ...]:
    findings: list[AnalysisValidationFinding] = []
    if source_bytes is not None and source_bytes > MAX_ANALYSIS_JSON_BYTES:
        findings.append(
            AnalysisValidationFinding(
                "fail",
                "payload-too-large",
                "$",
                f"analysis JSON must be at most {MAX_ANALYSIS_JSON_BYTES} bytes",
            )
        )
    if not isinstance(payload, dict):
        findings.append(
            AnalysisValidationFinding("fail", "payload-not-object", "$", "analysis JSON must be an object")
        )
        return tuple(findings)

    _validate_required_text(payload, names=("title", "headline"), label="title", findings=findings)
    _validate_required_text(
        payload,
        names=("summary", "description"),
        label="summary",
        findings=findings,
    )
    _validate_optional_text(payload, "model", findings)
    _validate_optional_text(payload, "source_image", findings)
    for name in ("observations", "findings", "actions", "recommendations"):
        _validate_text_or_text_list(payload, name, findings)
    findings.extend(_validate_shape(payload))
    findings.extend(_secret_findings(payload))
    findings.extend(_unknown_top_level_findings(payload))
    return tuple(findings)


def validation_exit_code(findings: tuple[AnalysisValidationFinding, ...]) -> int:
    return 1 if any(item.severity == "fail" for item in findings) else 0


def format_analysis_validation_json(findings: tuple[AnalysisValidationFinding, ...]) -> str:
    return json.dumps(
        {
            "summary": {
                "fail": sum(1 for item in findings if item.severity == "fail"),
                "warn": sum(1 for item in findings if item.severity == "warn"),
                "info": sum(1 for item in findings if item.severity == "info"),
            },
            "findings": [item.as_dict() for item in findings],
        },
        indent=2,
        sort_keys=True,
    )


def format_analysis_validation_text(findings: tuple[AnalysisValidationFinding, ...]) -> str:
    if not findings:
        return "Analysis JSON: valid"
    return "\n".join(
        f"[{finding.severity.upper()}] {finding.code} {finding.path}: {finding.message}"
        for finding in findings
    )


def require_valid_analysis_payload(payload: object, *, source_bytes: int | None = None) -> dict[str, Any]:
    findings = validate_analysis_payload(payload, source_bytes=source_bytes)
    failures = tuple(item for item in findings if item.severity == "fail")
    if failures:
        raise AnalysisValidationError(failures)
    if not isinstance(payload, dict):
        raise AnalysisValidationError(
            (AnalysisValidationFinding("fail", "payload-not-object", "$", "analysis JSON must be an object"),)
        )
    return payload


def _validate_required_text(
    payload: dict[str, object],
    *,
    names: tuple[str, str],
    label: str,
    findings: list[AnalysisValidationFinding],
) -> None:
    values = [(name, payload.get(name)) for name in names if name in payload]
    valid = [item for item in values if isinstance(item[1], str) and item[1].strip()]
    if not valid:
        findings.append(
            AnalysisValidationFinding(
                "fail",
                f"{label}-required",
                "$",
                f"analysis JSON must include a non-empty {names[0]} or {names[1]}",
            )
        )
    for name, value in values:
        if not isinstance(value, str):
            findings.append(
                AnalysisValidationFinding("fail", f"{name}-type", f"$.{name}", f"{name} must be a string")
            )
        elif not value.strip():
            findings.append(
                AnalysisValidationFinding("fail", f"{name}-empty", f"$.{name}", f"{name} must not be empty")
            )
    if len(valid) > 1:
        findings.append(
            AnalysisValidationFinding(
                "warn",
                f"{label}-alias-conflict",
                "$",
                f"both {names[0]} and {names[1]} are set; {names[0]} will be used",
            )
        )


def _validate_optional_text(
    payload: dict[str, object],
    name: str,
    findings: list[AnalysisValidationFinding],
) -> None:
    if name in payload and not isinstance(payload[name], str):
        findings.append(
            AnalysisValidationFinding("fail", f"{name}-type", f"$.{name}", f"{name} must be a string")
        )


def _validate_text_or_text_list(
    payload: dict[str, object],
    name: str,
    findings: list[AnalysisValidationFinding],
) -> None:
    if name not in payload:
        return
    value = payload[name]
    if isinstance(value, str):
        return
    if not isinstance(value, list):
        findings.append(
            AnalysisValidationFinding(
                "fail",
                f"{name}-type",
                f"$.{name}",
                f"{name} must be a string or an array of strings",
            )
        )
        return
    for index, item in enumerate(value):
        if not isinstance(item, str):
            findings.append(
                AnalysisValidationFinding(
                    "fail",
                    f"{name}-item-type",
                    f"$.{name}[{index}]",
                    f"{name} items must be strings",
                )
            )


def _validate_shape(payload: object) -> tuple[AnalysisValidationFinding, ...]:
    findings: list[AnalysisValidationFinding] = []

    def visit(value: object, path: str, depth: int) -> None:
        if depth > MAX_ANALYSIS_DEPTH:
            findings.append(
                AnalysisValidationFinding(
                    "fail",
                    "payload-too-deep",
                    path,
                    f"analysis JSON nesting must be at most {MAX_ANALYSIS_DEPTH}",
                )
            )
            return
        if isinstance(value, str):
            if len(value) > MAX_ANALYSIS_STRING_CHARS:
                findings.append(
                    AnalysisValidationFinding(
                        "fail",
                        "string-too-long",
                        path,
                        f"strings must be at most {MAX_ANALYSIS_STRING_CHARS} characters",
                    )
                )
        elif isinstance(value, list):
            if len(value) > MAX_ANALYSIS_LIST_ITEMS:
                findings.append(
                    AnalysisValidationFinding(
                        "fail",
                        "array-too-long",
                        path,
                        f"arrays must contain at most {MAX_ANALYSIS_LIST_ITEMS} items",
                    )
                )
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]", depth + 1)
        elif isinstance(value, dict):
            if len(value) > MAX_ANALYSIS_OBJECT_KEYS:
                findings.append(
                    AnalysisValidationFinding(
                        "fail",
                        "object-too-wide",
                        path,
                        f"objects must contain at most {MAX_ANALYSIS_OBJECT_KEYS} keys",
                    )
                )
            for key, item in value.items():
                if not isinstance(key, str):
                    findings.append(
                        AnalysisValidationFinding("fail", "key-type", path, "JSON object keys must be strings")
                    )
                    continue
                visit(item, f"{path}.{key}", depth + 1)
        elif value is None or isinstance(value, (int, float, bool)):
            return
        else:
            findings.append(
                AnalysisValidationFinding(
                    "fail",
                    "unsupported-value",
                    path,
                    "analysis JSON values must be JSON scalars, arrays, or objects",
                )
            )

    visit(payload, "$", 0)
    return tuple(findings)


def _secret_findings(payload: object) -> tuple[AnalysisValidationFinding, ...]:
    findings: list[AnalysisValidationFinding] = []

    def visit(value: object, path: str) -> None:
        if isinstance(value, str):
            if SECRET_VALUE_RE.search(value):
                findings.append(
                    AnalysisValidationFinding(
                        "warn",
                        "secret-looking-assignment",
                        path,
                        "value contains a secret-looking assignment",
                    )
                )
            if OPENAI_STYLE_KEY_RE.search(value):
                findings.append(
                    AnalysisValidationFinding(
                        "warn",
                        "secret-looking-key",
                        path,
                        "value contains an OpenAI-style key pattern",
                    )
                )
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
        elif isinstance(value, dict):
            for key, item in value.items():
                visit(item, f"{path}.{key}")

    visit(payload, "$")
    return tuple(findings)


def _unknown_top_level_findings(payload: dict[str, object]) -> tuple[AnalysisValidationFinding, ...]:
    known = {
        "title",
        "headline",
        "summary",
        "description",
        "observations",
        "findings",
        "actions",
        "recommendations",
        "model",
        "source_image",
    }
    return tuple(
        AnalysisValidationFinding(
            "warn",
            "unknown-top-level-field",
            f"$.{key}",
            "field is preserved in raw local notes but ignored by normalized outputs",
        )
        for key in sorted(payload)
        if key not in known
    )


_TEXT_SCHEMA = {
    "type": "string",
    "minLength": 1,
    "maxLength": MAX_ANALYSIS_STRING_CHARS,
}
_TEXT_OR_LIST_SCHEMA = {
    "oneOf": [
        _TEXT_SCHEMA,
        {
            "type": "array",
            "maxItems": MAX_ANALYSIS_LIST_ITEMS,
            "items": _TEXT_SCHEMA,
        },
    ]
}
_ANALYSIS_INPUT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://griosai.local/schemas/analysis-input.v1.json",
    "title": "GriosAI Analysis Input",
    "description": "Local analysis payload accepted by GriosAI import, packet, Obsidian, and MLflow commands.",
    "type": "object",
    "additionalProperties": True,
    "allOf": [
        {"anyOf": [{"required": ["title"]}, {"required": ["headline"]}]},
        {"anyOf": [{"required": ["summary"]}, {"required": ["description"]}]},
    ],
    "properties": {
        "title": _TEXT_SCHEMA,
        "headline": _TEXT_SCHEMA,
        "summary": _TEXT_SCHEMA,
        "description": _TEXT_SCHEMA,
        "observations": _TEXT_OR_LIST_SCHEMA,
        "findings": _TEXT_OR_LIST_SCHEMA,
        "actions": _TEXT_OR_LIST_SCHEMA,
        "recommendations": _TEXT_OR_LIST_SCHEMA,
        "model": _TEXT_SCHEMA,
        "source_image": _TEXT_SCHEMA,
    },
    "x-griosai": {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "max_json_bytes": MAX_ANALYSIS_JSON_BYTES,
        "max_depth": MAX_ANALYSIS_DEPTH,
        "privacy": "payload is stored locally in notes; downstream packet and MLflow outputs are sanitized",
    },
}
