from __future__ import annotations

import ipaddress
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any

from .brain import AnalysisRecord, slugify
from .lineage import analysis_id


DEFAULT_MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
DEFAULT_MLFLOW_EXPERIMENT = "GriosAI"
MAX_PARAM_VALUE_CHARS = 250


class MlflowError(RuntimeError):
    pass


@dataclass(frozen=True)
class MlflowConfig:
    tracking_uri: str = DEFAULT_MLFLOW_TRACKING_URI
    experiment_name: str = DEFAULT_MLFLOW_EXPERIMENT
    tracking_token: str | None = None
    allow_remote: bool = False
    timeout_seconds: int = 10

    @classmethod
    def from_env(
        cls,
        *,
        tracking_uri: str | None = None,
        experiment_name: str | None = None,
        tracking_token: str | None = None,
        allow_remote: bool | None = None,
        timeout_seconds: int | str | None = None,
    ) -> "MlflowConfig":
        raw_allow = os.getenv("GRIOSAI_MLFLOW_ALLOW_REMOTE")
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
        _status, payload = self._request_json(
            "POST",
            "/api/2.0/mlflow/experiments/create",
            body={"name": name},
        )
        experiment_id = payload.get("experiment_id")
        if experiment_id is None:
            raise MlflowError("MLflow create experiment response did not include experiment_id")
        return str(experiment_id)

    def ensure_experiment(self, name: str) -> str:
        experiment = self.get_experiment_by_name(name)
        if experiment is not None:
            experiment_id = experiment.get("experiment_id")
            if experiment_id is None:
                raise MlflowError("MLflow experiment response did not include experiment_id")
            return str(experiment_id)
        return self.create_experiment(name)

    def create_run(
        self,
        experiment_id: str,
        *,
        run_name: str,
        start_time_ms: int,
        tags: list[dict[str, str]],
    ) -> str:
        _status, payload = self._request_json(
            "POST",
            "/api/2.0/mlflow/runs/create",
            body={
                "experiment_id": experiment_id,
                "run_name": run_name,
                "start_time": start_time_ms,
                "tags": tags,
            },
        )
        info = _run_info(payload)
        run_id = info.get("run_id") or info.get("run_uuid")
        if run_id is None:
            raise MlflowError("MLflow create run response did not include run_id")
        return str(run_id)

    def log_batch(
        self,
        run_id: str,
        *,
        metrics: list[dict[str, object]],
        params: list[dict[str, str]],
        tags: list[dict[str, str]],
    ) -> None:
        self._request_json(
            "POST",
            "/api/2.0/mlflow/runs/log-batch",
            body={
                "run_id": run_id,
                "metrics": metrics,
                "params": params,
                "tags": tags,
            },
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
        run_id = self.create_run(
            experiment_id,
            run_name=payload["run_name"],
            start_time_ms=payload["timestamp_ms"],
            tags=payload["run_tags"],
        )
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
            try:
                self.end_run(run_id, status=status, end_time_ms=_now_ms())
            except MlflowError:
                pass
            raise
        self.end_run(run_id, status=status, end_time_ms=_now_ms())
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

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
        expected_statuses: set[int] | None = None,
    ) -> tuple[int, dict[str, Any]]:
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

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                response_body = response.read().decode("utf-8", errors="replace")
                status = response.status
        except urllib.error.HTTPError as exc:
            try:
                response_body = exc.read().decode("utf-8", errors="replace")
                status = exc.code
            finally:
                exc.close()
        except urllib.error.URLError as exc:
            raise MlflowError(f"Could not reach MLflow tracking server: {exc}") from exc

        payload = _decode_json_response(response_body)
        if status not in expected:
            raise MlflowError(
                f"MLflow {method} {path} failed with HTTP {status}: {_error_message(payload)}"
            )
        return status, payload


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
    analysis_slug = slugify(slug or record.title)
    record_analysis_id = analysis_id(record)
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
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("MLflow tracking URI must use http or https")
    if parsed.username or parsed.password:
        raise ValueError("MLflow tracking URI must not include credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("MLflow tracking URI must not include query or fragment values")
    if not parsed.hostname:
        raise ValueError("MLflow tracking URI must include a hostname")
    if not allow_remote and not is_loopback_tracking_uri(value):
        raise ValueError(
            "MLflow tracking URI must point to localhost unless remote tracking is explicitly allowed"
        )


def is_loopback_tracking_uri(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    hostname = parsed.hostname or ""
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


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
    text = " ".join(str(value).split())
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


def _run_info(payload: dict[str, Any]) -> dict[str, Any]:
    run = payload.get("run")
    if not isinstance(run, dict):
        raise MlflowError("MLflow response did not include run")
    info = run.get("info")
    if not isinstance(info, dict):
        raise MlflowError("MLflow run response did not include run info")
    return info


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
