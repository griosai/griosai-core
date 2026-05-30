import http.client
import socket
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from griosai.config import GriosConfig
from griosai.server import make_handler


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

    def test_get_health_allows_local_host(self) -> None:
        with running_server() as server:
            response = request(server, "GET", "/api/health")
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader("Cache-Control"), "no-store")
            self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")

    def test_html_responses_include_security_headers(self) -> None:
        with running_server() as server:
            response = request(server, "GET", "/")
            self.assertEqual(response.status, 200)
            self.assertIn("frame-ancestors 'none'", response.getheader("Content-Security-Policy"))
            self.assertEqual(response.getheader("Referrer-Policy"), "no-referrer")


class running_server:
    def __enter__(self) -> ThreadingHTTPServer:
        self.tmp = tempfile.TemporaryDirectory()
        config = GriosConfig.from_env(
            vault_dir=Path(self.tmp.name) / "vault",
            api_token="test-token",
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(config))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.server

    def __exit__(self, *args: object) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        self.tmp.cleanup()


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
