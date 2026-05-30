from __future__ import annotations

import json
from copy import deepcopy
from typing import Any


OPENAPI_PATH = "/api/openapi.json"


def openapi_spec() -> dict[str, Any]:
    return deepcopy(_OPENAPI_SPEC)


def openapi_json() -> str:
    return json.dumps(openapi_spec(), indent=2, sort_keys=True)


_ERROR_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["error"],
    "properties": {"error": {"type": "string"}},
}


_OPENAPI_SPEC: dict[str, Any] = {
    "openapi": "3.1.0",
    "info": {
        "title": "GriosAI Local API",
        "version": "0.1.0",
        "description": (
            "Local-first dashboard and vault API. Mutation endpoints require a bearer token "
            "and all endpoints are intended for localhost or private-network access."
        ),
    },
    "servers": [{"url": "/"}],
    "tags": [
        {"name": "status"},
        {"name": "vault"},
        {"name": "dashboards"},
        {"name": "analysis"},
        {"name": "contract"},
    ],
    "paths": {
        "/api/health": {
            "get": {
                "tags": ["status"],
                "operationId": "getHealth",
                "summary": "Return server and vault readiness status.",
                "responses": {
                    "200": {
                        "description": "Server health payload.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HealthResponse"}
                            }
                        },
                    },
                    "400": {"$ref": "#/components/responses/BadRequest"},
                    "403": {"$ref": "#/components/responses/Forbidden"},
                },
            }
        },
        "/api/notes": {
            "get": {
                "tags": ["vault"],
                "operationId": "listNotes",
                "summary": "List generated markdown notes.",
                "responses": {
                    "200": {
                        "description": "Generated note summaries.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/NotesResponse"}
                            }
                        },
                    },
                    "400": {"$ref": "#/components/responses/BadRequest"},
                    "403": {"$ref": "#/components/responses/Forbidden"},
                },
            }
        },
        "/api/dashboards": {
            "get": {
                "tags": ["dashboards"],
                "operationId": "listDashboards",
                "summary": "List generated dashboard files.",
                "responses": {
                    "200": {
                        "description": "Generated dashboards.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DashboardsResponse"}
                            }
                        },
                    },
                    "400": {"$ref": "#/components/responses/BadRequest"},
                    "403": {"$ref": "#/components/responses/Forbidden"},
                },
            }
        },
        "/api/openapi.json": {
            "get": {
                "tags": ["contract"],
                "operationId": "getOpenApi",
                "summary": "Return this OpenAPI contract.",
                "responses": {
                    "200": {
                        "description": "OpenAPI document.",
                        "content": {
                            "application/json": {
                                "schema": {"type": "object", "additionalProperties": True}
                            }
                        },
                    },
                    "400": {"$ref": "#/components/responses/BadRequest"},
                    "403": {"$ref": "#/components/responses/Forbidden"},
                },
            }
        },
        "/dashboards/{file}": {
            "get": {
                "tags": ["dashboards"],
                "operationId": "getDashboard",
                "summary": "Serve one generated dashboard HTML file.",
                "parameters": [
                    {
                        "name": "file",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "pattern": "^[^/\\\\]+\\.html$"},
                        "description": "Dashboard filename under the vault dashboards directory.",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Dashboard HTML.",
                        "content": {"text/html": {"schema": {"type": "string"}}},
                    },
                    "400": {"$ref": "#/components/responses/BadRequest"},
                    "403": {"$ref": "#/components/responses/Forbidden"},
                    "404": {"$ref": "#/components/responses/NotFound"},
                },
            }
        },
        "/api/analyze-image": {
            "post": {
                "tags": ["analysis"],
                "operationId": "analyzeImage",
                "summary": "Analyze a vault image through the configured local Ollama adapter.",
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/AnalyzeImageRequest"}
                        }
                    },
                },
                "responses": {
                    "201": {
                        "description": "Analysis note and dashboard created.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AnalyzeImageResponse"}
                            }
                        },
                    },
                    "400": {"$ref": "#/components/responses/BadRequest"},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "403": {"$ref": "#/components/responses/Forbidden"},
                    "404": {"$ref": "#/components/responses/NotFound"},
                    "413": {"$ref": "#/components/responses/PayloadTooLarge"},
                    "415": {"$ref": "#/components/responses/UnsupportedMediaType"},
                    "502": {"$ref": "#/components/responses/BadGateway"},
                },
            }
        },
    },
    "components": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "description": "Per-run or configured mutation API token.",
            }
        },
        "schemas": {
            "HealthResponse": {
                "type": "object",
                "additionalProperties": False,
                "required": ["ok", "vault_dir", "host", "port"],
                "properties": {
                    "ok": {"type": "boolean"},
                    "vault_dir": {"type": "string"},
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
            "NoteSummary": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "title", "updated_at"],
                "properties": {
                    "name": {"type": "string"},
                    "title": {"type": "string"},
                    "updated_at": {"type": "string", "format": "date-time"},
                },
            },
            "DashboardSummary": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "url"],
                "properties": {
                    "name": {"type": "string"},
                    "url": {"type": "string"},
                },
            },
            "NotesResponse": {
                "type": "object",
                "additionalProperties": False,
                "required": ["notes"],
                "properties": {
                    "notes": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/NoteSummary"},
                    }
                },
            },
            "DashboardsResponse": {
                "type": "object",
                "additionalProperties": False,
                "required": ["dashboards"],
                "properties": {
                    "dashboards": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/DashboardSummary"},
                    }
                },
            },
            "AnalyzeImageRequest": {
                "type": "object",
                "additionalProperties": False,
                "required": ["image_path"],
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Absolute path under the selected vault images directory.",
                    },
                    "prompt": {"type": "string"},
                    "model": {"type": "string"},
                },
            },
            "AnalyzeImageResponse": {
                "type": "object",
                "additionalProperties": False,
                "required": ["ok", "note", "dashboard", "lineage", "dashboard_url"],
                "properties": {
                    "ok": {"type": "boolean"},
                    "note": {"type": "string"},
                    "dashboard": {"type": "string"},
                    "lineage": {"type": "string"},
                    "dashboard_url": {"type": "string"},
                },
            },
            "ErrorResponse": _ERROR_SCHEMA,
        },
        "responses": {
            "BadRequest": {
                "description": "Request is invalid.",
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
            },
            "Unauthorized": {
                "description": "Bearer token is missing or invalid.",
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
            },
            "Forbidden": {
                "description": "Host or Origin is not allowed.",
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
            },
            "NotFound": {
                "description": "Requested object was not found.",
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
            },
            "PayloadTooLarge": {
                "description": "Request body or image is too large.",
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
            },
            "UnsupportedMediaType": {
                "description": "Content-Type or image type is unsupported.",
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
            },
            "BadGateway": {
                "description": "Local model adapter failed.",
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
            },
        },
    },
}
