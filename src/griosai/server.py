from __future__ import annotations

import json
import secrets
from dataclasses import replace
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

from .brain import AnalysisRecord, ensure_vault, list_notes, safe_child, slugify, write_analysis_note
from .config import GriosConfig
from .dashboard import list_dashboards, write_dashboard
from .ollama_client import (
    DEFAULT_IMAGE_PROMPT,
    ImageTooLargeError,
    OllamaError,
    UnsupportedImageError,
    analyze_image,
)


MAX_BODY_BYTES = 2_000_000
ALLOWED_IMAGE_SUFFIXES = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"}


class ClientError(ValueError):
    def __init__(self, message: str, status: HTTPStatus) -> None:
        super().__init__(message)
        self.status = status


def run_server(config: GriosConfig) -> None:
    if config.api_token is None:
        config = replace(config, api_token=secrets.token_urlsafe(24))
    ensure_vault(config.vault_dir)
    handler = make_handler(config)
    server = ThreadingHTTPServer((config.host, config.port), handler)
    print(f"GriosAI listening on http://{config.host}:{config.port}")
    print(f"Mutation API token: {config.api_token}")
    if config.host != "127.0.0.1":
        print("Warning: non-local bind requested. Confirm your network exposure is intentional.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping GriosAI.")
    finally:
        server.server_close()


def make_handler(config: GriosConfig) -> type[BaseHTTPRequestHandler]:
    class GriosHandler(BaseHTTPRequestHandler):
        server_version = "GriosAI/0.1"

        def do_GET(self) -> None:
            if not self._validate_host():
                return
            path = urlparse(self.path).path
            if path == "/":
                self._send_html(_index_html(config))
                return
            if path == "/api/health":
                self._send_json(
                    {
                        "ok": True,
                        "vault_dir": str(ensure_vault(config.vault_dir)),
                        "host": config.host,
                        "port": config.port,
                    }
                )
                return
            if path == "/api/notes":
                self._send_json({"notes": list_notes(config.vault_dir)})
                return
            if path == "/api/dashboards":
                self._send_json({"dashboards": list_dashboards(config.vault_dir)})
                return
            if path.startswith("/dashboards/"):
                self._serve_dashboard(path.removeprefix("/dashboards/"))
                return
            self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if not self._validate_host() or not self._validate_mutation_headers():
                return
            path = urlparse(self.path).path
            if path != "/api/analyze-image":
                self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
                return
            try:
                payload = self._read_json_body()
                image_path = payload.get("image_path")
                if not isinstance(image_path, str) or not image_path.strip():
                    self._send_json(
                        {"error": "image_path is required"},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                model = str(payload.get("model") or config.vision_model)
                prompt = str(payload.get("prompt") or DEFAULT_IMAGE_PROMPT)
                api_image = _resolve_api_image_path(config.vault_dir, image_path)
                record = analyze_image(
                    api_image,
                    model=model,
                    ollama_url=config.ollama_url,
                    prompt=prompt,
                )
                slug = slugify(record.title)
                note_path = write_analysis_note(config.vault_dir, record, slug=slug)
                dashboard_path = write_dashboard(config.vault_dir, record, slug=slug)
                self._send_json(
                    {
                        "ok": True,
                        "note": str(note_path),
                        "dashboard": str(dashboard_path),
                        "dashboard_url": f"/dashboards/{dashboard_path.name}",
                    },
                    status=HTTPStatus.CREATED,
                )
            except ClientError as exc:
                self._send_json({"error": str(exc)}, status=exc.status)
            except FileNotFoundError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
            except ImageTooLargeError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            except UnsupportedImageError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            except OllamaError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
            except Exception as exc:
                self._send_json(
                    {"error": str(exc)},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )

        def log_message(self, format: str, *args: object) -> None:
            print(f"{self.address_string()} - {format % args}")

        def _serve_dashboard(self, raw_name: str) -> None:
            name = unquote(raw_name)
            if "/" in name or "\\" in name or not name.endswith(".html"):
                self._send_json({"error": "invalid dashboard name"}, status=HTTPStatus.BAD_REQUEST)
                return
            path = safe_child(ensure_vault(config.vault_dir), "dashboards", name)
            if not path.exists():
                self._send_json({"error": "dashboard not found"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_html(path.read_text(encoding="utf-8"))

        def _read_json_body(self) -> dict[str, object]:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ClientError("Content-Length is required", HTTPStatus.LENGTH_REQUIRED)
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ClientError("Content-Length must be an integer", HTTPStatus.BAD_REQUEST) from exc
            if length < 0:
                raise ClientError("Content-Length must not be negative", HTTPStatus.BAD_REQUEST)
            if length > MAX_BODY_BYTES:
                raise ClientError("request body too large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            body = self.rfile.read(length)
            try:
                parsed = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise ClientError("request body must be valid JSON", HTTPStatus.BAD_REQUEST) from exc
            if not isinstance(parsed, dict):
                raise ClientError("JSON body must be an object", HTTPStatus.BAD_REQUEST)
            return parsed

        def _validate_host(self) -> bool:
            host_header = self.headers.get("Host")
            if not host_header:
                self._send_json({"error": "Host header is required"}, status=HTTPStatus.BAD_REQUEST)
                return False
            host = _host_without_port(host_header)
            if host not in _allowed_hostnames(config):
                self._send_json({"error": "Host header is not allowed"}, status=HTTPStatus.FORBIDDEN)
                return False
            return True

        def _validate_mutation_headers(self) -> bool:
            content_type = self.headers.get("Content-Type", "")
            if content_type.split(";", 1)[0].strip().lower() != "application/json":
                self._send_json(
                    {"error": "Content-Type must be application/json"},
                    status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                )
                return False

            if not config.api_token:
                self._send_json(
                    {"error": "Mutation API token is not configured"},
                    status=HTTPStatus.SERVICE_UNAVAILABLE,
                )
                return False

            authorization = self.headers.get("Authorization", "")
            expected = f"Bearer {config.api_token}"
            if not secrets.compare_digest(authorization, expected):
                self._send_json({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
                return False

            origin = self.headers.get("Origin")
            if origin and _host_without_port(urlparse(origin).netloc) not in _allowed_hostnames(config):
                self._send_json({"error": "Origin is not allowed"}, status=HTTPStatus.FORBIDDEN)
                return False
            return True

        def _send_json(
            self,
            payload: dict[str, object],
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(
            self,
            body: str,
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return GriosHandler


def create_sample(vault_dir: Path) -> tuple[Path, Path]:
    record = AnalysisRecord(
        title="GriosAI Phase 0 Local Dashboard",
        summary="A local-only sample dashboard proving the vault, renderer, and server flow.",
        observations=[
            "The brain is a plain-file vault.",
            "Dashboards are static HTML with no remote assets.",
            "Local model calls are optional and adapter-based.",
        ],
        actions=[
            "Run the server on 127.0.0.1.",
            "Expose to a phone only through a private network path.",
            "Add Notebook/Python connector imports around the package API.",
        ],
        model="sample",
    )
    slug = slugify(record.title)
    note_path = write_analysis_note(vault_dir, record, slug=slug)
    dashboard_path = write_dashboard(vault_dir, record, slug=slug)
    return note_path, dashboard_path


def _index_html(config: GriosConfig) -> str:
    dashboards = list_dashboards(config.vault_dir)
    links = "\n".join(
        f'<li><a href="/dashboards/{quote(item["name"])}">{escape(item["name"])}</a></li>'
        for item in dashboards
    )
    if not links:
        links = "<li>No dashboards yet. Run `griosai sample` or analyze an image.</li>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GriosAI</title>
  <style>
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f7f7f2;
      color: #171717;
    }}
    main {{
      width: min(840px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0;
    }}
    h1 {{ margin: 0 0 8px; letter-spacing: 0; }}
    p {{ color: #5b605c; }}
    a {{ color: #176b87; }}
    li + li {{ margin-top: 8px; }}
    code {{ overflow-wrap: anywhere; }}
  </style>
</head>
<body>
  <main>
    <h1>GriosAI</h1>
    <p>Vault: <code>{escape(str(config.vault_dir))}</code></p>
    <h2>Dashboards</h2>
    <ul>{links}</ul>
  </main>
</body>
</html>
"""


def _resolve_api_image_path(vault_dir: Path, raw_path: str) -> Path:
    vault = ensure_vault(vault_dir)
    images_root = safe_child(vault, "images")
    image = Path(raw_path).expanduser().resolve()
    if image != images_root and images_root not in image.parents:
        raise ClientError(
            "REST image_path must point inside the vault/images directory",
            HTTPStatus.BAD_REQUEST,
        )
    if image.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
        raise ClientError(
            "REST image_path must use a supported image extension",
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        )
    return image


def _allowed_hostnames(config: GriosConfig) -> set[str]:
    allowed = {host for host in config.allowed_hosts if host}
    allowed.update({"127.0.0.1", "localhost", "::1"})
    if config.host not in {"0.0.0.0", "::", ""}:
        allowed.add(config.host)
    return allowed


def _host_without_port(value: str) -> str:
    host = value.strip()
    if host.startswith("["):
        end = host.find("]")
        if end != -1:
            return host[1:end]
    return host.rsplit(":", 1)[0] if ":" in host else host
