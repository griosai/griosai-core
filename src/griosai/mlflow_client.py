from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any

from .brain import AnalysisRecord, slugify
from .lineage import analysis_id
from .privacy import redact_likely_secrets
from .url_safety import is_loopback_url, parse_http_url


DEFAULT_MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
DEFAULT_MLFLOW_EXPERIMENT = "GriosAI"
MAX_PARAM_VALUE_CHARS = 250

# Status surfaced when a run's metrics succeeded but the terminalizing
# (end_run) call failed; a terminalize-only retry can recover the run.
STATUS_FINALIZE_FAILED = "RUNNING (finalize failed)"

# Bounded retry policy for transient transport/server failures.
MAX_REQUEST_ATTEMPTS = 3
RETRYABLE_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})
RETRY_BASE_DELAY_SECONDS = 0.5
RETRY_MAX_DELAY_SECONDS = 8.0

# MLflow per-call log-batch caps (see runs/log-batch API limits).
MAX_BATCH_METRICS = 1000
MAX_BATCH_PARAMS = 100
MAX_BATCH_TAGS = 100
MAX_BATCH_TOTAL = 1000

# Tag key used to make analysis runs idempotent across re-runs.
ANALYSIS_ID_TAG = "griosai.analysis_id"


class MlflowError(RuntimeError):
    pass


@dataclass(frozen=True)
class MlflowConfig:
    tracking_uri: str = DEFAULT_MLFLOW_TRACKING_URI
    experiment_name: str = DEFAULT_MLFLOW_EXPERIMENT
    tracking_token: str | None = None
    allow_remote: bool = False
    timeout_seconds: int = 10
    # When enabled, log_analysis looks up a prior run keyed by analysis_id
    # and reuses (or terminalizes) it instead of creating a duplicate run.
    reuse_existing_runs: bool = False

    @classmethod
    def from_env(
        cls,
        *,
        tracking_uri: str | None = None,
        experiment_name: str | None = None,
        tracking_token: str | None = None,
        allow_remote: bool | None = None,
        timeout_seconds: int | str | None = None,
        reuse_existing_runs: bool | None = None,
    ) -> "MlflowConfig":
        raw_allow = os.getenv("GRIOSAI_MLFLOW_ALLOW_REMOTE")
        raw_reuse = os.getenv("GRIOSAI_MLFLOW_REUSE_RUNS")
        raw_timeout = timeout_seconds or os.getenv("GRIOSAI_MLFLOW_TIMEOUT") or 10
        return cls(
            tracking_uri=tracking_uri
            or os.getenv("GRIOSAI_MLFLOW_TRACKING_URI")
            or DEFAULT_MLFLOW_TRACKING_URI,
            experiment_name=experiment_name
            or os.getenv("GRIOSAI_MLFLOW_EXPERIMENT")
            or DEFAULT_MLFLOW_EXPERIMENT,
            tracking_token=tracking_token
            or os.getenv("GRIOSAI_MLFLOW_TRACKING_TOKEN")
            or None,
            allow_remote=allow_remote if allow_remote is not None else bool_env(raw_allow, False),
            timeout_seconds=int(raw_timeout),
            reuse_existing_runs=(
                reuse_existing_runs
                if reuse_existing_runs is not None
                else bool_env(raw_reuse, False)
            ),
        )


@dataclass(frozen=True)
class MlflowLogResult:
    tracking_uri: str
    experiment_name: str
    experiment_id: str
    run_id: str
    analysis_id: str
    status: str
    metrics_logged: int
    params_logged: int
    tags_logged: int

    def as_dict(self) -> dict[str, object]:
        return {
            "tracking_uri": self.tracking_uri,
            "experiment_name": self.experiment_name,
            "experiment_id": self.experiment_id,
            "run_id": self.run_id,
            "analysis_id": self.analysis_id,
            "status": self.status,
            "metrics_logged": self.metrics_logged,
            "params_logged": self.params_logged,
            "tags_logged": self.tags_logged,
        }


class MlflowClient:
    def __init__(self, config: MlflowConfig) -> None:
        validate_tracking_uri(config.tracking_uri, allow_remote=config.allow_remote)
        self.config = config
        self.base_url = config.tracking_uri.rstrip("/")
        # A single opener is reused for the (typically 5) sequential calls so
        # urllib can keep the underlying connection warm. The redirect handler
        # refuses every 3xx so a tracking server cannot pivot the request to an
        # internal host (e.g. 169.254.169.254) or replay the auth token to a
        # different origin.
        self._opener = urllib.request.build_opener(
            _NoRedirectHandler(allow_remote=config.allow_remote)
        )

    def get_experiment_by_name(self, name: str) -> dict[str, Any] | None:
        status, payload = self._request_json(
            "GET",
            "/api/2.0/mlflow/experiments/get-by-name",
            query={"experiment_name": name},
            expected_statuses={200, 404},
        )
        if status == 404:
            return None
        experiment = payload.get("experiment")
        if not isinstance(experiment, dict):
            raise MlflowError("MLflow get experiment response did not include an experiment")
        return experiment

    def create_experiment(self, name: str) -> str:
        # Accept 409 so a create that races another writer (TOCTOU between
        # get-by-name and create) does not crash; the caller re-resolves.
        status, payload = self._request_json(
            "POST",
            "/api/2.0/mlflow/experiments/create",
            body={"name": name},
            expected_statuses={200, 409},
        )
        if status == 409 or _is_already_exists_error(payload):
            raise _ExperimentExistsError(name)
        experiment_id = payload.get("experiment_id")
        if experiment_id is None:
            raise MlflowError("MLflow create experiment response did not include experiment_id")
        return str(experiment_id)

    def ensure_experiment(self, name: str) -> str:
        experiment = self.get_experiment_by_name(name)
        if experiment is not None:
            return _experiment_id_from(experiment)
        try:
            return self.create_experiment(name)
        except _ExperimentExistsError:
            # Lost the create race: another writer created it concurrently.
            # Resolve to the now-existing experiment instead of failing.
            experiment = self.get_experiment_by_name(name)
            if experiment is None:
                raise MlflowError(
                    "MLflow experiment reported as existing but could not be resolved"
                )
            return _experiment_id_from(experiment)

    def create_run(
        self,
        experiment_id: str,
        *,
        run_name: str,
        start_time_ms: int,
        tags: list[dict[str, str]],
    ) -> str:
        # runs/create is non-idempotent: a confirmed HTTP failure must not be
        # retried (it could create a duplicate run). idempotent=False keeps the
        # retry wrapper to connect-level URLError only (request never sent).
        _status, payload = self._request_json(
            "POST",
            "/api/2.0/mlflow/runs/create",
            body={
                "experiment_id": experiment_id,
                "run_name": run_name,
                "start_time": start_time_ms,
                "tags": tags,
            },
            idempotent=False,
        )
        return _run_id_from(payload)

    def find_run_by_analysis_id(
        self, experiment_id: str, record_analysis_id: str
    ) -> dict[str, Any] | None:
        """Return the most recent run info tagged with this analysis_id, if any."""
        safe_id = record_analysis_id.replace("\\", "\\\\").replace('"', '\\"')
        _status, payload = self._request_json(
            "POST",
            "/api/2.0/mlflow/runs/search",
            body={
                "experiment_ids": [experiment_id],
                "filter": f'tags."{ANALYSIS_ID_TAG}" = "{safe_id}"',
                "run_view_type": "ALL",
                "max_results": 1,
            },
        )
        runs = payload.get("runs")
        if not isinstance(runs, list) or not runs:
            return None
        first = runs[0]
        if not isinstance(first, dict):
            return None
        info = first.get("info")
        return info if isinstance(info, dict) else None

    def log_batch(
        self,
        run_id: str,
        *,
        metrics: list[dict[str, object]],
        params: list[dict[str, str]],
        tags: list[dict[str, str]],
    ) -> None:
        # MLflow caps a single log-batch at 1000 metrics / 100 params /
        # 100 tags / 1000 total entries. Chunk and loop so oversized payloads
        # are accepted instead of rejected (or silently truncated) by the API.
        for metric_chunk, param_chunk, tag_chunk in _chunk_log_batch(metrics, params, tags):
            # runs/log-batch is NOT replay-safe: metrics are append-only time
            # series, so replaying a batch the server already applied (or
            # partially applied) before returning a 5xx duplicates metric points
            # (and a differing params re-write can error). idempotent=False keeps
            # the retry wrapper to connect-level URLError only (request never
            # sent), surfacing a confirmed HTTP failure immediately instead of
            # blindly re-logging metrics.
            self._request_json(
                "POST",
                "/api/2.0/mlflow/runs/log-batch",
                body={
                    "run_id": run_id,
                    "metrics": metric_chunk,
                    "params": param_chunk,
                    "tags": tag_chunk,
                },
                idempotent=False,
            )

    def end_run(self, run_id: str, *, status: str, end_time_ms: int) -> None:
        self._request_json(
            "POST",
            "/api/2.0/mlflow/runs/update",
            body={"run_id": run_id, "status": status, "end_time": end_time_ms},
        )

    def log_analysis(self, record: AnalysisRecord, *, slug: str | None = None) -> MlflowLogResult:
        experiment_id = self.ensure_experiment(self.config.experiment_name)
        payload = analysis_mlflow_payload(record, slug=slug)
        run_id = self._acquire_run(experiment_id, payload)

        # status reflects the outcome we *want* to terminalize the run with.
        # On metrics failure it becomes FAILED; if the final end_run itself
        # fails we surface STATUS_FINALIZE_FAILED so the run is not silently
        # reported FINISHED while still RUNNING server-side, and a
        # terminalize-only retry remains possible.
        status = "FINISHED"
        try:
            self.log_batch(
                run_id,
                metrics=payload["metrics"],
                params=payload["params"],
                tags=payload["batch_tags"],
            )
        except Exception:
            status = "FAILED"
            raise
        finally:
            try:
                self.end_run(run_id, status=status, end_time_ms=_now_ms())
            except Exception:
                # Could not terminalize. If metrics succeeded, downgrade the
                # reported status so callers know the run is still RUNNING and
                # can retry the terminalize step. If metrics already failed we
                # are unwinding an exception and must not mask it.
                if status == "FINISHED":
                    status = STATUS_FINALIZE_FAILED

        return MlflowLogResult(
            tracking_uri=self.base_url,
            experiment_name=self.config.experiment_name,
            experiment_id=experiment_id,
            run_id=run_id,
            analysis_id=payload["analysis_id"],
            status=status,
            metrics_logged=len(payload["metrics"]),
            params_logged=len(payload["params"]),
            tags_logged=len(payload["run_tags"]) + len(payload["batch_tags"]),
        )

    def _acquire_run(self, experiment_id: str, payload: dict[str, Any]) -> str:
        """Create a fresh run, terminalizing a stranded prior attempt first.

        With reuse_existing_runs enabled, re-running an analysis always creates a
        new run keyed by the same griosai.analysis_id tag; it does NOT reuse a
        prior run's run_id. The only guarantee is that a previous attempt left
        stranded RUNNING is terminalized as FAILED (it never completed) before
        the fresh run is created, so re-runs do not leave orphaned RUNNING runs.
        A prior terminal (e.g. FINISHED) run is left untouched.

        Concurrency: there is a benign TOCTOU between find_run_by_analysis_id
        and the subsequent create — two concurrent re-runs may both terminalize
        the same orphan and both create new runs. This is acceptable for the
        best-effort cleanup this method provides.
        """
        if not self.config.reuse_existing_runs:
            return self._create_analysis_run(experiment_id, payload)

        prior = self.find_run_by_analysis_id(experiment_id, payload["analysis_id"])
        if prior is not None and str(prior.get("status", "")).upper() == "RUNNING":
            prior_run_id = prior.get("run_id") or prior.get("run_uuid")
            if prior_run_id is not None:
                try:
                    self.end_run(str(prior_run_id), status="FAILED", end_time_ms=_now_ms())
                except Exception:
                    # Best-effort cleanup of the orphan; never block the re-run.
                    pass
        return self._create_analysis_run(experiment_id, payload)

    def _create_analysis_run(self, experiment_id: str, payload: dict[str, Any]) -> str:
        return self.create_run(
            experiment_id,
            run_name=payload["run_name"],
            start_time_ms=payload["timestamp_ms"],
            tags=payload["run_tags"],
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
        expected_statuses: set[int] | None = None,
        idempotent: bool = True,
    ) -> tuple[int, dict[str, Any]]:
        """Issue a request with bounded retry/backoff and connection reuse.

        Retry policy:
        - Idempotent requests (GET, and POSTs whose replay is safe) retry on
          connect-level URLError and on HTTP 429/500/502/503/504, honoring
          Retry-After.
        - Non-idempotent requests (e.g. runs/create) only retry on
          connect-level URLError, where the request was never confirmed
          server-side; a confirmed HTTP failure is surfaced immediately so a
          partially-applied write is not duplicated.
        """
        expected = expected_statuses or {200}
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "GriosAI/0.1",
        }
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.config.tracking_token:
            headers["Authorization"] = f"Bearer {self.config.tracking_token}"

        last_error: Exception | None = None
        for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
            request = urllib.request.Request(url, data=data, headers=headers, method=method)
            retry_after: float | None = None
            try:
                with self._opener.open(
                    request, timeout=self.config.timeout_seconds
                ) as response:
                    response_body = response.read().decode("utf-8", errors="replace")
                    status = response.status
            except urllib.error.HTTPError as exc:
                try:
                    response_body = exc.read().decode("utf-8", errors="replace")
                    status = exc.code
                    retry_after = _parse_retry_after(exc.headers.get("Retry-After"))
                finally:
                    exc.close()
                # Only replay confirmed HTTP failures when it is safe to do so.
                if (
                    idempotent
                    and status in RETRYABLE_HTTP_STATUSES
                    and attempt < MAX_REQUEST_ATTEMPTS
                ):
                    last_error = MlflowError(
                        f"MLflow {method} {path} returned retryable HTTP {status}"
                    )
                    _sleep_backoff(attempt, retry_after)
                    continue
            except urllib.error.URLError as exc:
                # Connect-level failure: the request was not confirmed by the
                # server, so it is safe to replay even for non-idempotent POSTs.
                last_error = MlflowError(
                    f"Could not reach MLflow tracking server: {exc}"
                )
                if attempt < MAX_REQUEST_ATTEMPTS:
                    _sleep_backoff(attempt, None)
                    continue
                raise last_error from exc

            payload = _decode_json_response(response_body)
            if status not in expected:
                raise MlflowError(
                    f"MLflow {method} {path} failed with HTTP {status}: {_error_message(payload)}"
                )
            return status, payload

        # Exhausted retries on a retryable HTTP status.
        raise last_error or MlflowError(f"MLflow {method} {path} failed after retries")


def log_analysis_to_mlflow(
    config: MlflowConfig,
    record: AnalysisRecord,
    *,
    slug: str | None = None,
) -> MlflowLogResult:
    return MlflowClient(config).log_analysis(record, slug=slug)


def analysis_mlflow_payload(
    record: AnalysisRecord,
    *,
    slug: str | None = None,
) -> dict[str, Any]:
    timestamp_ms = _now_ms()
    record_analysis_id = analysis_id(record)
    analysis_slug = _metadata_slug(record_analysis_id, slug)
    source_image_name = _source_image_name(record.source_image)

    params = [
        _param("griosai.analysis_id", record_analysis_id),
        _param("griosai.analysis_slug", analysis_slug),
        _param("griosai.model", record.model or "manual"),
    ]
    if source_image_name:
        params.append(_param("griosai.source_image_name", source_image_name))

    metrics = [
        _metric("griosai.summary_chars", len(record.summary), timestamp_ms),
        _metric("griosai.observation_count", len(record.observations), timestamp_ms),
        _metric("griosai.action_count", len(record.actions), timestamp_ms),
        _metric("griosai.raw_field_count", len(record.raw), timestamp_ms),
    ]
    run_tags = [
        _tag("mlflow.runName", f"griosai-{analysis_slug}"),
        _tag("griosai.kind", "analysis"),
        _tag("griosai.privacy", "metadata-only"),
        # Set at run-create time as a searchable tag so re-runs can find and
        # reuse/terminalize the prior run for the same analysis (idempotency).
        _tag(ANALYSIS_ID_TAG, record_analysis_id),
    ]
    batch_tags = [
        _tag("griosai.created_at", record.created_at),
        _tag("griosai.content_policy", "no-summary-observations-actions-or-raw-json"),
    ]
    return {
        "analysis_id": record_analysis_id,
        "timestamp_ms": timestamp_ms,
        "run_name": f"griosai-{analysis_slug}",
        "params": params,
        "metrics": metrics,
        "run_tags": run_tags,
        "batch_tags": batch_tags,
    }


def validate_tracking_uri(value: str, *, allow_remote: bool = False) -> None:
    parse_http_url(value, field_name="MLflow tracking URI")
    if not allow_remote and not is_loopback_tracking_uri(value):
        raise ValueError(
            "MLflow tracking URI must point to localhost unless remote tracking is explicitly allowed"
        )


def is_loopback_tracking_uri(value: str) -> bool:
    return is_loopback_url(value)


def bool_env(value: str | None, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _param(key: str, value: object) -> dict[str, str]:
    return {"key": key, "value": _safe_param_value(value)}


def _metric(key: str, value: int | float, timestamp_ms: int) -> dict[str, object]:
    return {"key": key, "value": float(value), "timestamp": timestamp_ms, "step": 0}


def _tag(key: str, value: object) -> dict[str, str]:
    return {"key": key, "value": _safe_param_value(value)}


def _safe_param_value(value: object) -> str:
    text = " ".join(redact_likely_secrets(value).split())
    if len(text) <= MAX_PARAM_VALUE_CHARS:
        return text
    return text[: MAX_PARAM_VALUE_CHARS - 3] + "..."


def _source_image_name(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme and parsed.path:
        name = PurePath(parsed.path).name
    else:
        name = PurePath(value.replace("\\", "/")).name
    return _safe_param_value(name) if name else None


def _metadata_slug(record_analysis_id: str, slug: str | None) -> str:
    fallback = f"analysis-{record_analysis_id[:12]}"
    if slug is None:
        return fallback
    return slugify(redact_likely_secrets(slug), fallback=fallback)


def _run_info(payload: dict[str, Any]) -> dict[str, Any]:
    run = payload.get("run")
    if not isinstance(run, dict):
        raise MlflowError("MLflow response did not include run")
    info = run.get("info")
    if not isinstance(info, dict):
        raise MlflowError("MLflow run response did not include run info")
    return info


def _run_id_from(payload: dict[str, Any]) -> str:
    info = _run_info(payload)
    run_id = info.get("run_id") or info.get("run_uuid")
    if run_id is None:
        raise MlflowError("MLflow create run response did not include run_id")
    return str(run_id)


def _experiment_id_from(experiment: dict[str, Any]) -> str:
    experiment_id = experiment.get("experiment_id")
    if experiment_id is None:
        raise MlflowError("MLflow experiment response did not include experiment_id")
    return str(experiment_id)


def _is_already_exists_error(payload: dict[str, Any]) -> bool:
    code = payload.get("error_code")
    return isinstance(code, str) and code.upper() == "RESOURCE_ALREADY_EXISTS"


class _ExperimentExistsError(Exception):
    """Raised internally when create-experiment loses a TOCTOU race."""

    def __init__(self, name: str) -> None:
        super().__init__(f"MLflow experiment already exists: {name}")
        self.name = name


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse to auto-follow any 3xx response from the tracking server.

    urllib follows redirects transparently, so a tracking server that returns
    a 3xx pointing at an internal address (e.g. 169.254.169.254 cloud metadata)
    would otherwise bypass the construction-time SSRF gate. The redirect target
    is re-validated against the loopback/allow gate, and every redirect is then
    refused outright. The MLflow REST endpoints used here never legitimately
    redirect, so treating 3xx as an error is the safe choice: it blocks the
    SSRF pivot AND prevents the Authorization header from being replayed to a
    different host (stdlib does not strip it across redirects).
    """

    def __init__(self, *, allow_remote: bool) -> None:
        super().__init__()
        self._allow_remote = allow_remote

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        # Re-validate the target purely to produce a precise error; the request
        # is refused regardless of whether the target would have been allowed.
        try:
            validate_tracking_uri(newurl, allow_remote=self._allow_remote)
            reason = "MLflow client does not follow redirects"
        except ValueError as exc:
            reason = f"refused redirect to disallowed host: {exc}"
        raise urllib.error.HTTPError(newurl, code, reason, headers, fp)


def _chunk_log_batch(
    metrics: list[dict[str, object]],
    params: list[dict[str, str]],
    tags: list[dict[str, str]],
) -> list[tuple[list[dict[str, object]], list[dict[str, str]], list[dict[str, str]]]]:
    """Split metrics/params/tags into log-batch calls within MLflow caps.

    Each chunk respects the per-type limits (1000 metrics / 100 params /
    100 tags) and the 1000-entry total cap. At least one (possibly empty)
    chunk is returned so the caller always issues one request.
    """
    chunks: list[
        tuple[list[dict[str, object]], list[dict[str, str]], list[dict[str, str]]]
    ] = []
    m_i = p_i = t_i = 0
    while m_i < len(metrics) or p_i < len(params) or t_i < len(tags):
        budget = MAX_BATCH_TOTAL
        m_take = min(len(metrics) - m_i, MAX_BATCH_METRICS, budget)
        budget -= m_take
        p_take = min(len(params) - p_i, MAX_BATCH_PARAMS, budget)
        budget -= p_take
        t_take = min(len(tags) - t_i, MAX_BATCH_TAGS, budget)
        if m_take == 0 and p_take == 0 and t_take == 0:
            # Defensive: should not happen given the loop guard, but avoids an
            # infinite loop if all remaining items somehow exceed the budget.
            break
        chunks.append(
            (
                metrics[m_i : m_i + m_take],
                params[p_i : p_i + p_take],
                tags[t_i : t_i + t_take],
            )
        )
        m_i += m_take
        p_i += p_take
        t_i += t_take
    if not chunks:
        chunks.append(([], [], []))
    return chunks


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    value = value.strip()
    try:
        seconds = float(value)
    except ValueError:
        return None
    if seconds < 0:
        return None
    return seconds


def _sleep_backoff(attempt: int, retry_after: float | None) -> None:
    if retry_after is not None:
        delay = min(retry_after, RETRY_MAX_DELAY_SECONDS)
    else:
        delay = min(RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)), RETRY_MAX_DELAY_SECONDS)
    # Full jitter to avoid thundering-herd retries against the tracking server.
    time.sleep(delay * (0.5 + random.random() * 0.5))


def _decode_json_response(value: str) -> dict[str, Any]:
    if not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise MlflowError("MLflow response was not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise MlflowError("MLflow response JSON must be an object")
    return parsed


def _error_message(payload: dict[str, Any]) -> str:
    for key in ("message", "error_code", "error"):
        value = payload.get(key)
        if value:
            return _safe_param_value(value)
    return "unexpected response"


def _now_ms() -> int:
    return int(time.time() * 1000)
