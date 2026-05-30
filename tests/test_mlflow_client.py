import http.server
import io
import json
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from griosai.brain import AnalysisRecord
from griosai.cli import main
from griosai.mlflow_client import (
    MlflowClient,
    MlflowConfig,
    analysis_mlflow_payload,
    log_analysis_to_mlflow,
    validate_tracking_uri,
)


class MlflowClientTests(unittest.TestCase):
    def test_rejects_non_local_tracking_uri_by_default(self) -> None:
        with self.assertRaises(ValueError):
            MlflowClient(MlflowConfig(tracking_uri="http://mlflow-tracking:5000"))

        validate_tracking_uri("http://mlflow-tracking:5000", allow_remote=True)

    def test_payload_tracks_metadata_without_raw_private_body(self) -> None:
        secret = "sk-" + ("A" * 24)
        record = AnalysisRecord(
            title="Sensitive Customer Finding",
            summary=f"Do not send this body {secret}",
            observations=[f"Observation with {secret}"],
            actions=["Action with /Users/gustavorios/private"],
            model="qwen2.5vl:7b",
            source_image="/Users/gustavorios/private/screenshots/kitchen.png",
            raw={"token": secret, "absolute_path": "/Users/gustavorios/private/file"},
        )

        payload = analysis_mlflow_payload(record)
        encoded = json.dumps(payload, sort_keys=True)

        self.assertNotIn(secret, encoded)
        self.assertNotIn("/Users/gustavorios", encoded)
        self.assertNotIn(record.summary, encoded)
        self.assertIn("kitchen.png", encoded)
        self.assertIn("griosai.summary_chars", encoded)

    def test_log_analysis_uses_mlflow_rest_api(self) -> None:
        secret = "sk-" + ("B" * 24)
        record = AnalysisRecord(
            title="MLflow Smoke",
            summary=f"Private summary {secret}",
            observations=["one", "two"],
            actions=["ship"],
            raw={"secret": secret},
        )

        with fake_mlflow() as server:
            result = log_analysis_to_mlflow(
                MlflowConfig(tracking_uri=server.url, tracking_token="test-token"),
                record,
            )

        self.assertEqual(result.status, "FINISHED")
        self.assertEqual(result.experiment_id, "42")
        self.assertEqual(result.run_id, "run-123")
        paths = [request["path"] for request in server.requests]
        self.assertEqual(
            paths,
            [
                "/api/2.0/mlflow/experiments/get-by-name",
                "/api/2.0/mlflow/experiments/create",
                "/api/2.0/mlflow/runs/create",
                "/api/2.0/mlflow/runs/log-batch",
                "/api/2.0/mlflow/runs/update",
            ],
        )
        self.assertTrue(
            all(
                request["authorization"] == "Bearer test-token"
                for request in server.requests
            )
        )
        bodies = json.dumps([request["json"] for request in server.requests], sort_keys=True)
        self.assertNotIn(secret, bodies)
        self.assertIn("metadata-only", bodies)

    def test_cli_mlflow_log_prints_result_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_mlflow(existing_experiment=True) as server:
            payload = Path(tmp) / "analysis.json"
            payload.write_text(
                json.dumps({"title": "CLI Tracking", "summary": "Track metadata"}),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "mlflow-log",
                            "--json-file",
                            str(payload),
                            "--tracking-uri",
                            server.url,
                            "--tracking-token",
                            "test-token",
                        ]
                    ),
                    0,
                )

        parsed = json.loads(output.getvalue())
        self.assertEqual(parsed["run_id"], "run-123")
        self.assertEqual(parsed["experiment_id"], "42")


class fake_mlflow:
    def __init__(self, *, existing_experiment: bool = False) -> None:
        self.existing_experiment = existing_experiment
        self.requests: list[dict[str, object]] = []

    def __enter__(self) -> "fake_mlflow":
        parent = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parent.requests.append(parent._request_record(self, {}))
                parsed = urlparse(self.path)
                if parsed.path == "/api/2.0/mlflow/experiments/get-by-name":
                    query = parse_qs(parsed.query)
                    if parent.existing_experiment:
                        self._send_json(
                            {
                                "experiment": {
                                    "experiment_id": "42",
                                    "name": query.get("experiment_name", [""])[0],
                                }
                            }
                        )
                    else:
                        self._send_json({"error_code": "RESOURCE_DOES_NOT_EXIST"}, status=404)
                    return
                self._send_json({"error": "not found"}, status=404)

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                parsed_body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                parent.requests.append(parent._request_record(self, parsed_body))
                path = urlparse(self.path).path
                if path == "/api/2.0/mlflow/experiments/create":
                    self._send_json({"experiment_id": "42"})
                    return
                if path == "/api/2.0/mlflow/runs/create":
                    self._send_json({"run": {"info": {"run_id": "run-123"}}})
                    return
                if path == "/api/2.0/mlflow/runs/log-batch":
                    self._send_json({})
                    return
                if path == "/api/2.0/mlflow/runs/update":
                    self._send_json({"run_info": {"run_id": parsed_body.get("run_id")}})
                    return
                self._send_json({"error": "not found"}, status=404)

            def log_message(self, format: str, *args: object) -> None:
                return

            def _send_json(self, payload: dict[str, object], *, status: int = 200) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

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
        body: dict[str, object],
    ) -> dict[str, object]:
        return {
            "authorization": handler.headers.get("Authorization", ""),
            "content_type": handler.headers.get("Content-Type", ""),
            "path": urlparse(handler.path).path,
            "json": body,
        }


if __name__ == "__main__":
    unittest.main()
