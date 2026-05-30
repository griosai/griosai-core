import io
import http.client
import json
import socket
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from griosai.brain import AnalysisRecord, ensure_vault
from griosai.config import GriosConfig
from griosai.server import _redact_log_value, make_handler, run_server


class ServerTests(unittest.TestCase):
    def test_post_requires_json_content_type(self) -> None:
        with running_server() as server:
            response = request(
                server,
                "POST",
                "/api/analyze-image",
                body=b"{}",
                headers={"Content-Type": "text/plain"},
            )
            self.assertEqual(response.status, 415)

    def test_post_requires_bearer_token(self) -> None:
        with running_server() as server:
            response = request(
                server,
                "POST",
                "/api/analyze-image",
                body=b"{}",
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(response.status, 401)

    def test_post_rejects_disallowed_origin(self) -> None:
        with running_server() as server:
            response = request(
                server,
                "POST",
                "/api/analyze-image",
                body=b"{}",
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json",
                    "Origin": "https://evil.example",
                },
            )
            self.assertEqual(response.status, 403)

    def test_negative_content_length_is_rejected(self) -> None:
        with running_server() as server:
            port = server.server_address[1]
            with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
                sock.sendall(
                    (
                        "POST /api/analyze-image HTTP/1.1\r\n"
                        f"Host: 127.0.0.1:{port}\r\n"
                        "Authorization: Bearer test-token\r\n"
                        "Content-Type: application/json\r\n"
                        "Content-Length: -1\r\n"
                        "\r\n"
                        "{}"
                    ).encode("utf-8")
                )
                response = sock.recv(4096)
            self.assertIn(b"400", response.splitlines()[0])

    def test_invalid_utf8_json_body_is_rejected(self) -> None:
        with running_server() as server:
            port = server.server_address[1]
            with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
                body = b"\xff"
                sock.sendall(
                    (
                        "POST /api/analyze-image HTTP/1.1\r\n"
                        f"Host: 127.0.0.1:{port}\r\n"
                        "Authorization: Bearer test-token\r\n"
                        "Content-Type: application/json\r\n"
                        f"Content-Length: {len(body)}\r\n"
                        "\r\n"
                    ).encode("utf-8")
                    + body
                )
                response = sock.recv(4096)
            self.assertIn(b"400", response.splitlines()[0])

    def test_get_health_allows_local_host(self) -> None:
        with running_server() as server:
            response = request(server, "GET", "/api/health")
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader("Cache-Control"), "no-store")
            self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")

    def test_get_openapi_returns_contract(self) -> None:
        with running_server() as server:
            response = request(server, "GET", "/api/openapi.json")
            payload = json.loads(response.read().decode("utf-8"))

            self.assertEqual(response.status, 200)
            self.assertEqual(payload["openapi"], "3.1.0")
            self.assertIn("/api/analyze-image", payload["paths"])
            self.assertIn("bearerAuth", payload["components"]["securitySchemes"])

    def test_post_analyze_image_success_returns_lineage_path(self) -> None:
        with running_server() as server:
            vault = Path(server.griosai_vault_dir)
            image = vault / "images" / "sample.png"
            image.write_bytes(b"png")
            body = json.dumps({"image_path": str(image)}).encode("utf-8")

            with patch(
                "griosai.server.analyze_image",
                return_value=AnalysisRecord(title="Server Lineage", summary="local"),
            ):
                response = request(
                    server,
                    "POST",
                    "/api/analyze-image",
                    body=body,
                    headers={
                        "Authorization": "Bearer test-token",
                        "Content-Type": "application/json",
                    },
                )
            payload = json.loads(response.read().decode("utf-8"))

            self.assertEqual(response.status, 201)
            self.assertTrue(Path(payload["note"]).exists())
            self.assertTrue(Path(payload["dashboard"]).exists())
            self.assertTrue(Path(payload["lineage"]).exists())
            self.assertEqual(Path(payload["lineage"]).parent, vault / "lineage")

    def test_post_analyze_image_missing_file_does_not_disclose_path(self) -> None:
        with running_server() as server:
            vault = Path(server.griosai_vault_dir)
            image = vault / "images" / "missing-private.png"
            body = json.dumps({"image_path": str(image)}).encode("utf-8")

            response = request(
                server,
                "POST",
                "/api/analyze-image",
                body=body,
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json",
                },
            )
            payload = json.loads(response.read().decode("utf-8"))

            self.assertEqual(response.status, 404)
            self.assertEqual(payload["error"], "image not found")
            self.assertNotIn(str(image), json.dumps(payload))

    def test_post_analyze_image_internal_error_does_not_disclose_paths(self) -> None:
        with running_server() as server:
            vault = Path(server.griosai_vault_dir)
            image = vault / "images" / "sample.png"
            image.write_bytes(b"png")
            body = json.dumps({"image_path": str(image)}).encode("utf-8")

            with patch(
                "griosai.server.analyze_image",
                return_value=AnalysisRecord(title="Server Failure", summary="local"),
            ), patch(
                "griosai.server.write_analysis_note",
                side_effect=RuntimeError("/Users/gustavorios/private/vault denied"),
            ):
                response = request(
                    server,
                    "POST",
                    "/api/analyze-image",
                    body=body,
                    headers={
                        "Authorization": "Bearer test-token",
                        "Content-Type": "application/json",
                    },
                )
            payload = json.loads(response.read().decode("utf-8"))

            self.assertEqual(response.status, 500)
            self.assertEqual(payload["error"], "internal server error")
            self.assertNotIn("/Users/gustavorios", json.dumps(payload))

    def test_post_analyze_image_rejects_directory_image_path(self) -> None:
        with running_server() as server:
            vault = Path(server.griosai_vault_dir)
            image_dir = vault / "images" / "sample.png"
            image_dir.mkdir()
            body = json.dumps({"image_path": str(image_dir)}).encode("utf-8")

            response = request(
                server,
                "POST",
                "/api/analyze-image",
                body=body,
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json",
                },
            )
            payload = json.loads(response.read().decode("utf-8"))

            self.assertEqual(response.status, 400)
            self.assertEqual(payload["error"], "REST image_path must point to a regular image file")

    def test_html_responses_include_security_headers(self) -> None:
        with running_server() as server:
            response = request(server, "GET", "/")
            self.assertEqual(response.status, 200)
            self.assertIn("frame-ancestors 'none'", response.getheader("Content-Security-Policy"))
            self.assertEqual(response.getheader("Referrer-Policy"), "no-referrer")

    def test_dashboard_symlink_is_rejected_without_disclosing_target(self) -> None:
        with running_server() as server:
            vault = Path(server.griosai_vault_dir)
            outside = vault.parent / "outside.html"
            outside.write_text("private", encoding="utf-8")
            (vault / "dashboards" / "outside.html").symlink_to(outside)

            response = request(server, "GET", "/dashboards/outside.html")
            payload = json.loads(response.read().decode("utf-8"))

            self.assertEqual(response.status, 400)
            self.assertEqual(payload["error"], "invalid dashboard name")
            self.assertNotIn(str(outside), json.dumps(payload))

    def test_run_server_does_not_print_configured_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = GriosConfig.from_env(
                vault_dir=Path(tmp) / "vault",
                api_token="configured-token-value",
            )
            output = io.StringIO()
            with patch("griosai.server.ThreadingHTTPServer", FakeServer), redirect_stdout(output):
                run_server(config)

        self.assertIn("Mutation API token: configured", output.getvalue())
        self.assertNotIn("configured-token-value", output.getvalue())

    def test_log_redactor_removes_paths_and_credentials(self) -> None:
        redacted = _redact_log_value(
            r"token=secret-value mac=/Users/gustavorios/x linux=/home/gustavo/y home=~/z windows=C:\Users\gustavo\a"
        )

        self.assertIn("token=[redacted]", redacted)
        self.assertNotIn("secret-value", redacted)
        self.assertNotIn("/Users/gustavorios", redacted)
        self.assertNotIn("/home/gustavo", redacted)
        self.assertNotIn("~/z", redacted)
        self.assertNotIn(r"C:\Users", redacted)
        self.assertEqual(
            _redact_log_value("Authorization: Bearer " + "abcdefghijk12345"),
            "Authorization: Bearer [redacted]",
        )


class running_server:
    def __enter__(self) -> ThreadingHTTPServer:
        self.tmp = tempfile.TemporaryDirectory()
        config = GriosConfig.from_env(
            vault_dir=Path(self.tmp.name) / "vault",
            api_token="test-token",
        )
        self.vault_dir = ensure_vault(config.vault_dir)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(config))
        self.server.griosai_vault_dir = str(self.vault_dir)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.server

    def __exit__(self, *args: object) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        self.tmp.cleanup()


class FakeServer:
    def __init__(self, *args: object) -> None:
        return

    def serve_forever(self) -> None:
        raise KeyboardInterrupt

    def server_close(self) -> None:
        return


def request(
    server: ThreadingHTTPServer,
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> http.client.HTTPResponse:
    port = server.server_address[1]
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request(method, path, body=body, headers=headers or {})
    return connection.getresponse()


if __name__ == "__main__":
    unittest.main()
