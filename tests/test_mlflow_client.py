import http.server
import io
import json
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import griosai.mlflow_client as mlflow_module
from griosai.brain import AnalysisRecord
from griosai.cli import main
from griosai.mlflow_client import (
    MAX_BATCH_METRICS,
    MAX_BATCH_PARAMS,
    MAX_BATCH_TAGS,
    MAX_BATCH_TOTAL,
    MAX_REQUEST_ATTEMPTS,
    STATUS_FINALIZE_FAILED,
    MlflowClient,
    MlflowConfig,
    MlflowError,
    _chunk_log_batch,
    analysis_mlflow_payload,
    log_analysis_to_mlflow,
    validate_tracking_uri,
)


class MlflowClientTests(unittest.TestCase):
    def test_rejects_non_local_tracking_uri_by_default(self) -> None:
        with self.assertRaises(ValueError):
            MlflowClient(MlflowConfig(tracking_uri="http://mlflow-tracking:5000"))

        validate_tracking_uri("http://mlflow-tracking:5000", allow_remote=True)

    def test_rejects_tracking_uri_with_credentials_query_fragment_or_bad_port(self) -> None:
        for uri in (
            "http://user:pass@127.0.0.1:5000",
            "http://127.0.0.1:5000?token=abc",
            "http://127.0.0.1:5000#fragment",
            "http://127.0.0.1:bad",
        ):
            with self.subTest(uri=uri):
                with self.assertRaises(ValueError):
                    validate_tracking_uri(uri, allow_remote=True)

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
        self.assertNotIn("Sensitive Customer Finding", encoded)
        self.assertNotIn("sensitive-customer-finding", encoded)
        self.assertNotIn(record.summary, encoded)
        self.assertIn("kitchen.png", encoded)
        self.assertIn("griosai.analysis_id", encoded)
        self.assertIn(f"analysis-{payload['analysis_id'][:12]}", encoded)
        self.assertIn("griosai.summary_chars", encoded)

    def test_payload_uses_explicit_safe_slug_when_supplied(self) -> None:
        record = AnalysisRecord(title="Private Customer Name", summary="Local")

        payload = analysis_mlflow_payload(record, slug="public-demo")
        encoded = json.dumps(payload, sort_keys=True)

        self.assertIn("griosai-public-demo", encoded)
        self.assertNotIn("Private Customer Name", encoded)

    def test_payload_redacts_key_shaped_metadata_values(self) -> None:
        secret = "sk-proj-" + ("M" * 24)
        record = AnalysisRecord(
            title="Metadata Secret",
            summary="Local",
            model=f"model-{secret}",
            source_image=f"/tmp/{secret}.png",
        )

        payload = analysis_mlflow_payload(record, slug=f"slug-{secret}")
        encoded = json.dumps(payload, sort_keys=True)

        self.assertNotIn(secret, encoded)
        self.assertIn("[redacted-secret]", encoded)

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
        self.assertEqual(len(result.analysis_id), 64)
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
        self.assertEqual(len(parsed["analysis_id"]), 64)
        self.assertEqual(parsed["experiment_id"], "42")


class MlflowHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        # Make backoff instant so retry tests stay fast and deterministic.
        self._orig_sleep = mlflow_module.time.sleep
        mlflow_module.time.sleep = lambda *_a, **_k: None
        self.addCleanup(self._restore_sleep)

    def _restore_sleep(self) -> None:
        mlflow_module.time.sleep = self._orig_sleep

    def _record(self) -> AnalysisRecord:
        return AnalysisRecord(title="Hardening", summary="Local metadata only")

    def test_finalize_failure_surfaces_distinct_status_without_raising(self) -> None:
        # log-batch succeeds, but the terminalizing runs/update fails. The run
        # must not be reported FINISHED; the result surfaces the recoverable
        # "finalize failed" status so a terminalize-only retry is possible.
        with programmable_mlflow(fail_paths={"/api/2.0/mlflow/runs/update": 500}) as server:
            result = log_analysis_to_mlflow(MlflowConfig(tracking_uri=server.url), self._record())
        self.assertEqual(result.status, STATUS_FINALIZE_FAILED)
        self.assertEqual(result.run_id, "run-123")

    def test_log_batch_failure_still_terminalizes_run_as_failed(self) -> None:
        # The original FAILED-path guarantee must survive the finally rewrite:
        # a log-batch failure raises, but runs/update is still attempted.
        with programmable_mlflow(fail_paths={"/api/2.0/mlflow/runs/log-batch": 500}) as server:
            with self.assertRaises(MlflowError):
                log_analysis_to_mlflow(MlflowConfig(tracking_uri=server.url), self._record())
            updates = [
                req
                for req in server.requests
                if req["path"] == "/api/2.0/mlflow/runs/update"
            ]
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["json"].get("status"), "FAILED")

    def test_retries_transient_500_then_succeeds(self) -> None:
        # An idempotent GET (get-by-name) returns 500 once, then 200.
        with programmable_mlflow(
            existing_experiment=True,
            transient_failures={"/api/2.0/mlflow/experiments/get-by-name": [500]},
        ) as server:
            result = log_analysis_to_mlflow(MlflowConfig(tracking_uri=server.url), self._record())
        self.assertEqual(result.status, "FINISHED")
        get_calls = [
            req
            for req in server.requests
            if req["path"] == "/api/2.0/mlflow/experiments/get-by-name"
        ]
        self.assertEqual(len(get_calls), 2)  # one 500, one 200

    def test_honors_retry_after_header(self) -> None:
        with patch.object(mlflow_module.time, "sleep") as sleep, patch.object(
            mlflow_module.random, "random", return_value=0.0
        ):
            with programmable_mlflow(
                existing_experiment=True,
                transient_failures={"/api/2.0/mlflow/experiments/get-by-name": [429]},
                retry_after="2",
            ) as server:
                result = log_analysis_to_mlflow(MlflowConfig(tracking_uri=server.url), self._record())
        self.assertEqual(result.status, "FINISHED")
        sleep.assert_called_once_with(2.0)

    def test_retry_after_cap_and_fallback_jitter(self) -> None:
        with patch.object(mlflow_module.time, "sleep") as sleep, patch.object(
            mlflow_module.random, "random", return_value=0.0
        ) as random:
            mlflow_module._sleep_backoff(1, 100.0)
            sleep.assert_called_once_with(mlflow_module.RETRY_MAX_DELAY_SECONDS)
            random.assert_not_called()
            sleep.reset_mock()
            mlflow_module._sleep_backoff(2, None)
            sleep.assert_called_once_with(mlflow_module.RETRY_BASE_DELAY_SECONDS)
            random.assert_called_once_with()

    def test_non_idempotent_create_run_is_not_retried_on_http_500(self) -> None:
        # runs/create is non-idempotent: a confirmed 500 must surface
        # immediately (no replay) so we never create duplicate runs.
        with programmable_mlflow(
            existing_experiment=True,
            transient_failures={"/api/2.0/mlflow/runs/create": [500]},
        ) as server:
            with self.assertRaises(MlflowError):
                log_analysis_to_mlflow(MlflowConfig(tracking_uri=server.url), self._record())
            create_calls = [
                req
                for req in server.requests
                if req["path"] == "/api/2.0/mlflow/runs/create"
            ]
        self.assertEqual(len(create_calls), 1)  # no retry

    def test_non_idempotent_log_batch_is_not_retried_on_http_500(self) -> None:
        # runs/log-batch is non-idempotent: metrics are append-only, so a
        # confirmed transient 500 must surface immediately (no replay) instead
        # of re-applying a batch the server may have already (partially) applied
        # and duplicating metric points. Exactly one log-batch POST is sent.
        with programmable_mlflow(
            existing_experiment=True,
            transient_failures={"/api/2.0/mlflow/runs/log-batch": [500]},
        ) as server:
            with self.assertRaises(MlflowError):
                log_analysis_to_mlflow(MlflowConfig(tracking_uri=server.url), self._record())
            batch_calls = [
                req
                for req in server.requests
                if req["path"] == "/api/2.0/mlflow/runs/log-batch"
            ]
        self.assertEqual(len(batch_calls), 1)  # no retry: metrics not double-logged

    def test_non_idempotent_writes_are_not_retried_after_send_failure(self) -> None:
        operations = {
            "create": lambda client: client.create_run(
                "42", run_name="test", start_time_ms=0, tags=[]
            ),
            "batch": lambda client: client.log_batch(
                "run-123", metrics=[], params=[], tags=[]
            ),
        }
        for name, operation in operations.items():
            with self.subTest(operation=name):
                client = MlflowClient(MlflowConfig())
                with patch("urllib.request.http.client.HTTPConnection") as connection:
                    # Exercise urllib's real conversion of a send failure to
                    # URLError. The server may already have applied the write.
                    connection.return_value.request.side_effect = ConnectionResetError(
                        "write outcome unknown"
                    )
                    with self.assertRaises(MlflowError):
                        operation(client)
                self.assertEqual(connection.return_value.request.call_count, 1)

    def test_idempotent_lookup_retries_transport_failure(self) -> None:
        client = MlflowClient(MlflowConfig())
        with patch("urllib.request.http.client.HTTPConnection") as connection:
            connection.return_value.request.side_effect = ConnectionResetError(
                "lookup interrupted"
            )
            with self.assertRaises(MlflowError):
                client.get_experiment_by_name("test")
        self.assertEqual(connection.return_value.request.call_count, MAX_REQUEST_ATTEMPTS)

    def test_idempotent_lookup_retries_response_side_timeout(self) -> None:
        client = MlflowClient(MlflowConfig())
        with patch("urllib.request.http.client.HTTPConnection") as connection:
            connection.return_value.getresponse.side_effect = TimeoutError("read timed out")
            with self.assertRaises(MlflowError):
                client.get_experiment_by_name("test")
        self.assertEqual(connection.return_value.getresponse.call_count, MAX_REQUEST_ATTEMPTS)

    def test_redirect_to_internal_host_is_refused(self) -> None:
        # A 3xx pivot to a non-loopback host must be re-validated and refused.
        with programmable_mlflow(
            redirect_paths={"/api/2.0/mlflow/experiments/get-by-name": "http://169.254.169.254/latest"}
        ) as server:
            with self.assertRaises(MlflowError):
                log_analysis_to_mlflow(MlflowConfig(tracking_uri=server.url), self._record())

    def test_reuse_never_overwrites_run_that_finished_after_search(self) -> None:
        client = MlflowClient(MlflowConfig(reuse_existing_runs=True))
        with (
            patch.object(
                client,
                "find_run_by_analysis_id",
                return_value={"run_id": "r1", "status": "RUNNING"},
            ),
            patch.object(client, "get_run_status", return_value="FINISHED"),
            patch.object(client, "end_run") as end_run,
            patch.object(client, "_create_analysis_run", return_value="new"),
        ):
            self.assertEqual(client._acquire_run("1", {"analysis_id": "a1"}), "new")
        end_run.assert_not_called()

    def test_reuse_terminalizes_prior_running_run_then_creates_new(self) -> None:
        with programmable_mlflow(
            existing_experiment=True,
            prior_running_run="orphan-run",
        ) as server:
            result = log_analysis_to_mlflow(
                MlflowConfig(tracking_uri=server.url, reuse_existing_runs=True),
                self._record(),
            )
        self.assertEqual(result.status, "FINISHED")
        update_calls = [
            req for req in server.requests if req["path"] == "/api/2.0/mlflow/runs/update"
        ]
        # First update terminalizes the orphan as FAILED, last finishes the new run.
        self.assertEqual(update_calls[0]["json"].get("run_id"), "orphan-run")
        self.assertEqual(update_calls[0]["json"].get("status"), "FAILED")
        self.assertEqual(update_calls[-1]["json"].get("status"), "FINISHED")
        searched = any(
            req["path"] == "/api/2.0/mlflow/runs/search" for req in server.requests
        )
        self.assertTrue(searched)

    def test_experiment_create_conflict_resolves_to_existing(self) -> None:
        # MLflow3.1 returns400 for duplicate names; retain proxy409 compatibility.
        for status in (400, 409):
            with self.subTest(status=status), programmable_mlflow(
                experiment_create_conflict=True, experiment_conflict_status=status
            ) as server:
                result = log_analysis_to_mlflow(MlflowConfig(tracking_uri=server.url), self._record())
                self.assertEqual(result.experiment_id, "42")
                get_calls = [
                    req for req in server.requests
                    if req["path"] == "/api/2.0/mlflow/experiments/get-by-name"
                ]
                self.assertEqual(len(get_calls), 2)

    def test_experiment_create_unrelated_400_does_not_resolve_or_create_run(self) -> None:
        with programmable_mlflow(
            fail_paths={"/api/2.0/mlflow/experiments/create": 400}
        ) as server:
            with self.assertRaisesRegex(MlflowError, "HTTP 400.*boom"):
                log_analysis_to_mlflow(MlflowConfig(tracking_uri=server.url), self._record())
            self.assertEqual(
                [req["path"] for req in server.requests],
                ["/api/2.0/mlflow/experiments/get-by-name", "/api/2.0/mlflow/experiments/create"],
            )

    def test_experiment_commit_then_lost_response_recovers_real_conflict(self) -> None:
        client = MlflowClient(MlflowConfig(tracking_uri="http://127.0.0.1:5000"))
        created = {}
        calls = []

        def open_request(request, **kwargs):
            path = urlparse(request.full_url).path
            calls.append(path)
            if path.endswith("/get-by-name"):
                name = parse_qs(urlparse(request.full_url).query)["experiment_name"][0]
                if name not in created:
                    raise mlflow_module.urllib.error.HTTPError(
                        request.full_url, 404, "missing", {},
                        io.BytesIO(b'{"error_code":"RESOURCE_DOES_NOT_EXIST"}'),
                    )
                response = io.BytesIO(json.dumps({"experiment": {"experiment_id": created[name]}}).encode())
                response.status = 200
                return response
            self.assertTrue(path.endswith("/experiments/create"))
            name = json.loads(request.data)["name"]
            if name not in created:
                created[name] = "42"  # The server committed before the response was lost.
                raise mlflow_module.urllib.error.URLError("response lost after commit")
            raise mlflow_module.urllib.error.HTTPError(
                request.full_url, 400, "already exists", {},
                io.BytesIO(b'{"error_code":"RESOURCE_ALREADY_EXISTS"}'),
            )

        with patch.object(client._opener, "open", side_effect=open_request):
            self.assertEqual(client.ensure_experiment("shared"), "42")
        self.assertEqual(created, {"shared": "42"})
        self.assertEqual(calls, [
            "/api/2.0/mlflow/experiments/get-by-name",
            "/api/2.0/mlflow/experiments/create",
            "/api/2.0/mlflow/experiments/create",
            "/api/2.0/mlflow/experiments/get-by-name",
        ])

    def test_chunk_log_batch_respects_caps(self) -> None:
        metrics = [{"key": f"m{i}"} for i in range(MAX_BATCH_METRICS + 50)]
        params = [{"key": f"p{i}"} for i in range(MAX_BATCH_PARAMS + 30)]
        tags = [{"key": f"t{i}"} for i in range(MAX_BATCH_TAGS + 10)]
        chunks = _chunk_log_batch(metrics, params, tags)
        total_m = total_p = total_t = 0
        for m_chunk, p_chunk, t_chunk in chunks:
            self.assertLessEqual(len(m_chunk), MAX_BATCH_METRICS)
            self.assertLessEqual(len(p_chunk), MAX_BATCH_PARAMS)
            self.assertLessEqual(len(t_chunk), MAX_BATCH_TAGS)
            self.assertLessEqual(len(m_chunk) + len(p_chunk) + len(t_chunk), MAX_BATCH_TOTAL)
            total_m += len(m_chunk)
            total_p += len(p_chunk)
            total_t += len(t_chunk)
        self.assertEqual(total_m, len(metrics))
        self.assertEqual(total_p, len(params))
        self.assertEqual(total_t, len(tags))

    def test_chunk_log_batch_empty_returns_single_chunk(self) -> None:
        self.assertEqual(_chunk_log_batch([], [], []), [([], [], [])])

    def test_log_batch_chunks_oversized_payload_over_multiple_calls(self) -> None:
        with programmable_mlflow(existing_experiment=True) as server:
            client = MlflowClient(MlflowConfig(tracking_uri=server.url))
            client.log_batch(
                "run-123",
                metrics=[{"key": f"m{i}"} for i in range(MAX_BATCH_METRICS + 1)],
                params=[],
                tags=[],
            )
        batch_calls = [
            req for req in server.requests if req["path"] == "/api/2.0/mlflow/runs/log-batch"
        ]
        self.assertEqual(len(batch_calls), 2)

    # --- (a) success-path end_run failure must not strand the run ----------

    def test_success_path_finalize_failure_does_not_strand_run(self) -> None:
        # Metrics (log-batch) succeed, so the run reached a recordable state.
        # The terminalizing runs/update then fails. The reported status must
        # NOT be FINISHED (the run is still RUNNING server-side): callers see
        # the recoverable finalize-failed status and the run is not stranded
        # as silently-complete. The non-failed metric path is also confirmed.
        with programmable_mlflow(fail_paths={"/api/2.0/mlflow/runs/update": 503}) as server:
            result = log_analysis_to_mlflow(MlflowConfig(tracking_uri=server.url), self._record())
        self.assertEqual(result.status, STATUS_FINALIZE_FAILED)
        self.assertNotEqual(result.status, "FINISHED")
        self.assertGreater(result.metrics_logged, 0)
        batch_calls = [
            req for req in server.requests if req["path"] == "/api/2.0/mlflow/runs/log-batch"
        ]
        update_calls = [
            req for req in server.requests if req["path"] == "/api/2.0/mlflow/runs/update"
        ]
        # Metrics landed once. runs/update is idempotent, so the failing
        # terminalize is retried up to the bounded max before giving up; every
        # attempt asked for the FINISHED status that the run could not reach.
        self.assertEqual(len(batch_calls), 1)
        self.assertEqual(len(update_calls), MAX_REQUEST_ATTEMPTS)
        self.assertTrue(all(call["json"].get("status") == "FINISHED" for call in update_calls))

    # --- (b) bounded retry / backoff behavior ------------------------------

    def test_retries_transient_503_then_succeeds(self) -> None:
        # An idempotent GET returns 503 once, then 200: the retry wrapper
        # replays it and the overall log succeeds.
        with programmable_mlflow(
            existing_experiment=True,
            transient_failures={"/api/2.0/mlflow/experiments/get-by-name": [503]},
        ) as server:
            result = log_analysis_to_mlflow(MlflowConfig(tracking_uri=server.url), self._record())
        self.assertEqual(result.status, "FINISHED")
        get_calls = [
            req
            for req in server.requests
            if req["path"] == "/api/2.0/mlflow/experiments/get-by-name"
        ]
        self.assertEqual(len(get_calls), 2)  # one 503, one 200

    def test_retryable_status_exhausts_max_attempts_then_raises(self) -> None:
        # Every attempt of an idempotent GET returns 503. After
        # MAX_REQUEST_ATTEMPTS the wrapper gives up and raises rather than
        # looping forever, and it makes exactly MAX_REQUEST_ATTEMPTS calls.
        with programmable_mlflow(fail_paths={"/api/2.0/mlflow/experiments/get-by-name": 503}) as server:
            with self.assertRaises(MlflowError):
                log_analysis_to_mlflow(MlflowConfig(tracking_uri=server.url), self._record())
            get_calls = [
                req
                for req in server.requests
                if req["path"] == "/api/2.0/mlflow/experiments/get-by-name"
            ]
        self.assertEqual(len(get_calls), MAX_REQUEST_ATTEMPTS)

    def test_non_idempotent_create_run_not_retried_on_http_503(self) -> None:
        # runs/create is non-idempotent: even a retryable 503 must surface
        # immediately (no replay) so a duplicate run is never created.
        with programmable_mlflow(
            existing_experiment=True,
            fail_paths={"/api/2.0/mlflow/runs/create": 503},
        ) as server:
            with self.assertRaises(MlflowError):
                log_analysis_to_mlflow(MlflowConfig(tracking_uri=server.url), self._record())
            create_calls = [
                req
                for req in server.requests
                if req["path"] == "/api/2.0/mlflow/runs/create"
            ]
        self.assertEqual(len(create_calls), 1)  # no retry despite retryable status

    # --- (c) SSRF: redirect to cloud-metadata host is refused --------------

    def test_redirect_302_to_metadata_host_is_refused(self) -> None:
        # A 302 pivoting to the cloud metadata endpoint must be refused before
        # the SSRF target is contacted: the redirect is never followed, the
        # call raises, and the bearer token is not leaked in the error. Only
        # the original get-by-name request is recorded by the fake server (no
        # request reaches the metadata host, which the loopback fake could not
        # serve anyway).
        with programmable_mlflow(
            redirect_paths={
                "/api/2.0/mlflow/experiments/get-by-name": "http://169.254.169.254/latest/meta-data/"
            }
        ) as server:
            with self.assertRaises(MlflowError) as ctx:
                log_analysis_to_mlflow(
                    MlflowConfig(tracking_uri=server.url, tracking_token="secret-token"),
                    self._record(),
                )
            recorded = list(server.requests)
        message = str(ctx.exception)
        self.assertNotIn("secret-token", message)
        # The redirect was refused, so the flow stopped at get-by-name and
        # never advanced to creating a run.
        self.assertNotIn("/api/2.0/mlflow/runs/create", [req["path"] for req in recorded])

    # --- (d) auth failure surfaces a clear, token-free message -------------

    def test_unauthorized_surfaces_clear_message_without_token(self) -> None:
        # A 401 (non-retryable, unexpected) raises a clear MlflowError that
        # names the failing call and HTTP status but never leaks the bearer
        # token that was sent on the request.
        token = "super-secret-bearer-value"
        with programmable_mlflow(
            fail_paths={"/api/2.0/mlflow/experiments/get-by-name": 401}
        ) as server:
            with self.assertRaises(MlflowError) as ctx:
                log_analysis_to_mlflow(
                    MlflowConfig(tracking_uri=server.url, tracking_token=token),
                    self._record(),
                )
        message = str(ctx.exception)
        self.assertNotIn(token, message)
        self.assertIn("401", message)
        self.assertIn("/api/2.0/mlflow/experiments/get-by-name", message)

    # --- (e) unreachable server surfaces a 'could not reach' message -------

    def test_unreachable_server_surfaces_could_not_reach_message(self) -> None:
        # Pointing at a loopback port with nothing listening yields a
        # connect-level URLError on every attempt; after the bounded retries
        # the client raises the clear "could not reach MLflow" message.
        with _closed_loopback_port() as port:
            with self.assertRaises(MlflowError) as ctx:
                log_analysis_to_mlflow(
                    MlflowConfig(
                        tracking_uri=f"http://127.0.0.1:{port}",
                        timeout_seconds=1,
                    ),
                    self._record(),
                )
        self.assertIn("Could not reach MLflow", str(ctx.exception))

    # --- (f) oversized log_batch payload is chunked across calls -----------

    def test_log_batch_oversized_payload_splits_within_caps(self) -> None:
        # A log_batch whose metric payload exceeds the per-call cap must be
        # split into multiple runs/log-batch calls (none over the per-type or
        # total cap), rather than a single oversized (rejected/truncated)
        # request. Mixed params/tags are carried alongside in the chunks.
        with programmable_mlflow(existing_experiment=True) as server:
            client = MlflowClient(MlflowConfig(tracking_uri=server.url))
            client.log_batch(
                "run-123",
                metrics=[{"key": f"m{i}"} for i in range(MAX_BATCH_METRICS + 25)],
                params=[{"key": f"p{i}"} for i in range(MAX_BATCH_PARAMS + 5)],
                tags=[{"key": f"t{i}"} for i in range(MAX_BATCH_TAGS + 5)],
            )
        batch_calls = [
            req for req in server.requests if req["path"] == "/api/2.0/mlflow/runs/log-batch"
        ]
        self.assertGreaterEqual(len(batch_calls), 2)
        total_m = total_p = total_t = 0
        for call in batch_calls:
            body = call["json"]
            metrics = body.get("metrics", [])
            params = body.get("params", [])
            tags = body.get("tags", [])
            self.assertLessEqual(len(metrics), MAX_BATCH_METRICS)
            self.assertLessEqual(len(params), MAX_BATCH_PARAMS)
            self.assertLessEqual(len(tags), MAX_BATCH_TAGS)
            self.assertLessEqual(len(metrics) + len(params) + len(tags), MAX_BATCH_TOTAL)
            total_m += len(metrics)
            total_p += len(params)
            total_t += len(tags)
        # Every entry was sent exactly once across the chunked calls.
        self.assertEqual(total_m, MAX_BATCH_METRICS + 25)
        self.assertEqual(total_p, MAX_BATCH_PARAMS + 5)
        self.assertEqual(total_t, MAX_BATCH_TAGS + 5)

    # --- (g) re-run with same analysis_id does not duplicate the run -------

    def test_rerun_does_not_reterminalize_prior_finished_run(self) -> None:
        # When the prior run for this analysis_id is already terminal
        # (FINISHED, not RUNNING), a reuse-enabled re-run must look it up by
        # analysis_id (issuing runs/search) and must NOT terminalize it. A fresh
        # run is still created (the reuse path does not reuse the prior run_id);
        # this test only asserts the existing FINISHED run is left untouched.
        with programmable_mlflow(
            existing_experiment=True,
            prior_finished_run="prior-finished-run",
        ) as server:
            result = log_analysis_to_mlflow(
                MlflowConfig(tracking_uri=server.url, reuse_existing_runs=True),
                self._record(),
            )
        self.assertEqual(result.status, "FINISHED")
        searched = [
            req for req in server.requests if req["path"] == "/api/2.0/mlflow/runs/search"
        ]
        self.assertEqual(len(searched), 1)  # looked up by analysis_id
        # The pre-existing FINISHED run is never re-terminalized (no update
        # targeting it); only the fresh run is finalized.
        update_calls = [
            req for req in server.requests if req["path"] == "/api/2.0/mlflow/runs/update"
        ]
        self.assertTrue(
            all(call["json"].get("run_id") != "prior-finished-run" for call in update_calls)
        )

    def test_rerun_reuses_same_analysis_id_tag_across_runs(self) -> None:
        # Two logs of the same record carry the same analysis_id tag on every
        # runs/create, so the server can key idempotency off analysis_id.
        record = self._record()
        with programmable_mlflow(existing_experiment=True) as server:
            cfg = MlflowConfig(tracking_uri=server.url, reuse_existing_runs=True)
            first = log_analysis_to_mlflow(cfg, record)
            second = log_analysis_to_mlflow(cfg, record)
        self.assertEqual(first.analysis_id, second.analysis_id)
        create_calls = [
            req for req in server.requests if req["path"] == "/api/2.0/mlflow/runs/create"
        ]
        self.assertEqual(len(create_calls), 2)
        analysis_id_tags = [
            tag["value"]
            for call in create_calls
            for tag in call["json"].get("tags", [])
            if tag.get("key") == "griosai.analysis_id"
        ]
        self.assertEqual(len(analysis_id_tags), 2)
        self.assertEqual(analysis_id_tags[0], analysis_id_tags[1])
        self.assertEqual(analysis_id_tags[0], first.analysis_id)


def _closed_loopback_port() -> "_ClosedPort":
    return _ClosedPort()


class _ClosedPort:
    """Context manager yielding a loopback port with nothing listening.

    Binds an ephemeral port, records it, then closes the socket so a
    connection attempt is actively refused (deterministic, no real timeout).
    """

    def __enter__(self) -> int:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        self._port = sock.getsockname()[1]
        sock.close()
        return self._port

    def __exit__(self, *args: object) -> None:
        return None


class programmable_mlflow:
    """A configurable fake MLflow REST server for hardening tests."""

    def __init__(
        self,
        *,
        existing_experiment: bool = False,
        fail_paths: dict[str, int] | None = None,
        transient_failures: dict[str, list[int]] | None = None,
        retry_after: str | None = None,
        redirect_paths: dict[str, str] | None = None,
        prior_running_run: str | None = None,
        prior_finished_run: str | None = None,
        experiment_create_conflict: bool = False,
        experiment_conflict_status: int = 409,
    ) -> None:
        self.existing_experiment = existing_experiment
        self.fail_paths = fail_paths or {}
        self._get_by_name_calls = 0
        self.transient_failures = {k: list(v) for k, v in (transient_failures or {}).items()}
        self.retry_after = retry_after
        self.redirect_paths = redirect_paths or {}
        self.prior_running_run = prior_running_run
        self.prior_finished_run = prior_finished_run
        self.experiment_create_conflict = experiment_create_conflict
        self.experiment_conflict_status = experiment_conflict_status
        self.requests: list[dict[str, object]] = []

    def _maybe_inject(self, handler: http.server.BaseHTTPRequestHandler, path: str) -> bool:
        if path in self.redirect_paths:
            handler.send_response(302)
            handler.send_header("Location", self.redirect_paths[path])
            handler.send_header("Content-Length", "0")
            handler.end_headers()
            return True
        queue = self.transient_failures.get(path)
        if queue:
            status = queue.pop(0)
            self._send_error(handler, status)
            return True
        if path in self.fail_paths:
            self._send_error(handler, self.fail_paths[path])
            return True
        return False

    def _send_error(self, handler: http.server.BaseHTTPRequestHandler, status: int) -> None:
        body = json.dumps({"error_code": "INTERNAL_ERROR", "message": "boom"}).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        if self.retry_after is not None:
            handler.send_header("Retry-After", self.retry_after)
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    def __enter__(self) -> "programmable_mlflow":
        parent = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                parent.requests.append(parent._request_record(self, {}))
                if parent._maybe_inject(self, parsed.path):
                    return
                if parsed.path == "/api/2.0/mlflow/experiments/get-by-name":
                    parent._get_by_name_calls += 1
                    # In conflict mode the first lookup misses (triggering the
                    # racing create), and the post-conflict re-resolve hits.
                    exists = parent.existing_experiment or (
                        parent.experiment_create_conflict
                        and parent._get_by_name_calls > 1
                    )
                    if exists:
                        self._send_json({"experiment": {"experiment_id": "42"}})
                    else:
                        self._send_json({"error_code": "RESOURCE_DOES_NOT_EXIST"}, status=404)
                    return
                if parsed.path == "/api/2.0/mlflow/runs/get":
                    self._send_json({"run": {"info": {"run_id": "x", "status": "RUNNING"}}})
                    return
                self._send_json({"error": "not found"}, status=404)

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                parsed_body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                path = urlparse(self.path).path
                parent.requests.append(parent._request_record(self, parsed_body))
                if parent._maybe_inject(self, path):
                    return
                if path == "/api/2.0/mlflow/experiments/create":
                    if parent.experiment_create_conflict:
                        self._send_json(
                            {"error_code": "RESOURCE_ALREADY_EXISTS", "message": "exists"},
                            status=parent.experiment_conflict_status,
                        )
                        return
                    self._send_json({"experiment_id": "42"})
                    return
                if path == "/api/2.0/mlflow/runs/search":
                    if parent.prior_running_run:
                        self._send_json(
                            {
                                "runs": [
                                    {
                                        "info": {
                                            "run_id": parent.prior_running_run,
                                            "status": "RUNNING",
                                        }
                                    }
                                ]
                            }
                        )
                    elif parent.prior_finished_run:
                        self._send_json(
                            {
                                "runs": [
                                    {
                                        "info": {
                                            "run_id": parent.prior_finished_run,
                                            "status": "FINISHED",
                                        }
                                    }
                                ]
                            }
                        )
                    else:
                        self._send_json({"runs": []})
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
