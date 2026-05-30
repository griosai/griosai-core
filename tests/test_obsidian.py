import http.server
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import unquote, urlparse

from griosai.brain import AnalysisRecord
from griosai.cli import main
from griosai.obsidian import (
    ObsidianClient,
    ObsidianConfig,
    ObsidianError,
    normalize_obsidian_note_path,
    publish_analysis_to_obsidian,
)


class ObsidianTests(unittest.TestCase):
    def test_rejects_non_loopback_url(self) -> None:
        with self.assertRaises(ValueError):
            ObsidianClient(ObsidianConfig(url="https://example.com", api_key="test-key"))

    def test_requires_api_key(self) -> None:
        with self.assertRaises(ObsidianError):
            ObsidianClient(ObsidianConfig(url="http://127.0.0.1:27123"))

    def test_normalize_note_path_rejects_unsafe_paths(self) -> None:
        self.assertEqual(normalize_obsidian_note_path("GriosAI/notes/test.md"), "GriosAI/notes/test.md")
        for value in ("/absolute.md", "../outside.md", "GriosAI/.hidden.md", "C:/temp/test.md"):
            with self.assertRaises(ValueError):
                normalize_obsidian_note_path(value)

    def test_put_markdown_writes_to_vault_with_auth(self) -> None:
        with fake_obsidian() as server:
            client = ObsidianClient(
                ObsidianConfig(url=server.url, api_key="test-key", verify_tls=False)
            )
            result = client.put_markdown("GriosAI/notes/test.md", "# Hello")

            self.assertEqual(result.path, "GriosAI/notes/test.md")
            self.assertEqual(result.status, 204)
            self.assertEqual(server.requests[-1]["authorization"], "Bearer test-key")
            self.assertEqual(server.requests[-1]["path"], "/vault/GriosAI/notes/test.md")
            self.assertEqual(server.requests[-1]["body"], "# Hello")

    def test_publish_analysis_allocates_unique_path_by_default(self) -> None:
        with fake_obsidian(existing={"/vault/GriosAI/notes/same.md"}) as server:
            result = publish_analysis_to_obsidian(
                ObsidianConfig(url=server.url, api_key="test-key", verify_tls=False),
                AnalysisRecord(title="Same", summary="Do not clobber"),
            )

            self.assertTrue(result.path.startswith("GriosAI/notes/same-"))
            self.assertTrue(result.path.endswith(".md"))
            self.assertFalse(result.replaced)

    def test_cli_obsidian_sync_imports_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_obsidian() as server:
            payload = Path(tmp) / "analysis.json"
            payload.write_text(
                json.dumps({"title": "Obsidian CLI", "summary": "Sync me"}),
                encoding="utf-8",
            )

            self.assertEqual(
                main(
                    [
                        "obsidian-sync",
                        "--json-file",
                        str(payload),
                        "--obsidian-url",
                        server.url,
                        "--obsidian-api-key",
                        "test-key",
                    ]
                ),
                0,
            )
            self.assertEqual(server.requests[-1]["path"], "/vault/GriosAI/notes/obsidian-cli.md")


class fake_obsidian:
    def __init__(self, *, existing: set[str] | None = None) -> None:
        self.existing = existing or set()
        self.requests: list[dict[str, str]] = []

    def __enter__(self) -> "fake_obsidian":
        parent = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parent.requests.append(parent._request_record(self, ""))
                path = urlparse(self.path).path
                if path == "/":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"ok":"OK"}')
                    return
                self.send_response(200 if path in parent.existing else 404)
                self.end_headers()

            def do_PUT(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8")
                parent.requests.append(parent._request_record(self, body))
                parent.existing.add(urlparse(self.path).path)
                self.send_response(204)
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                return

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        return self

    def __exit__(self, *args: object) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()

    def _request_record(
        self,
        handler: http.server.BaseHTTPRequestHandler,
        body: str,
    ) -> dict[str, str]:
        return {
            "authorization": handler.headers.get("Authorization", ""),
            "content_type": handler.headers.get("Content-Type", ""),
            "path": unquote(urlparse(handler.path).path),
            "body": body,
        }


if __name__ == "__main__":
    unittest.main()
