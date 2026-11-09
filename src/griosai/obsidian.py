from __future__ import annotations

import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

from .brain import AnalysisRecord, render_markdown, slugify
from .url_safety import is_loopback_host, parse_http_url


DEFAULT_OBSIDIAN_URL = "https://127.0.0.1:27124"
DEFAULT_OBSIDIAN_FOLDER = "GriosAI/notes"


class ObsidianError(RuntimeError):
    pass


@dataclass(frozen=True)
class ObsidianConfig:
    url: str = DEFAULT_OBSIDIAN_URL
    api_key: str | None = None
    verify_tls: bool = True
    timeout_seconds: int = 10

    @classmethod
    def from_env(
        cls,
        *,
        url: str | None = None,
        api_key: str | None = None,
        verify_tls: bool | None = None,
        timeout_seconds: int | str | None = None,
    ) -> "ObsidianConfig":
        raw_verify = os.getenv("GRIOSAI_OBSIDIAN_VERIFY_TLS")
        raw_timeout = timeout_seconds or os.getenv("GRIOSAI_OBSIDIAN_TIMEOUT") or 10
        return cls(
            url=url or os.getenv("GRIOSAI_OBSIDIAN_URL") or DEFAULT_OBSIDIAN_URL,
            api_key=api_key or os.getenv("GRIOSAI_OBSIDIAN_API_KEY") or None,
            verify_tls=verify_tls if verify_tls is not None else _bool_env(raw_verify, True),
            timeout_seconds=int(raw_timeout),
        )


@dataclass(frozen=True)
class ObsidianWriteResult:
    path: str
    status: int
    replaced: bool


class ObsidianClient:
    def __init__(self, config: ObsidianConfig) -> None:
        if not config.api_key:
            raise ObsidianError("Obsidian API key is required")
        _validate_loopback_url(config.url)
        self.config = config
        self.base_url = config.url.rstrip("/")

    def health(self) -> dict[str, Any]:
        status, body = self._request("GET", "/")
        return {"status": status, "body": body}

    def put_markdown(
        self,
        note_path: str,
        content: str,
        *,
        overwrite: bool = False,
    ) -> ObsidianWriteResult:
        path = normalize_obsidian_note_path(note_path)
        replaced = self.exists(path)
        if replaced and not overwrite:
            path = self._unique_note_path(path)
            replaced = False
        status, _body = self._request(
            "PUT",
            f"/vault/{_quote_path(path)}",
            data=content.encode("utf-8"),
            headers={"Content-Type": "text/markdown; charset=utf-8"},
        )
        if status not in {200, 204}:
            raise ObsidianError(f"Obsidian write failed with HTTP {status}")
        return ObsidianWriteResult(path=path, status=status, replaced=replaced)

    def exists(self, note_path: str) -> bool:
        status, _body = self._request(
            "GET",
            f"/vault/{_quote_path(normalize_obsidian_note_path(note_path))}",
            headers={"Accept": "text/markdown"},
        )
        if status == 404:
            return False
        if status == 200:
            return True
        raise ObsidianError(f"Obsidian existence check failed with HTTP {status}")

    def _unique_note_path(self, note_path: str) -> str:
        path = PurePosixPath(note_path)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        for counter in range(1, 10_000):
            suffix = "" if counter == 1 else f"-{counter}"
            candidate = path.with_name(f"{path.stem}-{timestamp}{suffix}{path.suffix}")
            candidate_text = str(candidate)
            if not self.exists(candidate_text):
                return candidate_text
        raise ObsidianError(f"Could not allocate a unique Obsidian note path for {note_path}")

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str]:
        request_headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "User-Agent": "GriosAI/0.1",
        }
        request_headers.update(headers or {})
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=request_headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.config.timeout_seconds,
                context=self._ssl_context(),
            ) as response:
                return response.status, response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, exc.read().decode("utf-8", errors="replace")
            finally:
                exc.close()
        except urllib.error.URLError as exc:
            raise ObsidianError(f"Could not reach local Obsidian REST API: {exc}") from exc

    def _ssl_context(self) -> ssl.SSLContext | None:
        if urllib.parse.urlparse(self.base_url).scheme != "https":
            return None
        if self.config.verify_tls:
            return ssl.create_default_context()
        return ssl._create_unverified_context()


def publish_analysis_to_obsidian(
    config: ObsidianConfig,
    record: AnalysisRecord,
    *,
    folder: str = DEFAULT_OBSIDIAN_FOLDER,
    slug: str | None = None,
    overwrite: bool = False,
) -> ObsidianWriteResult:
    note_folder = normalize_obsidian_folder(folder)
    note_slug = slugify(slug or record.title)
    note_path = f"{note_folder}/{note_slug}.md" if note_folder else f"{note_slug}.md"
    client = ObsidianClient(config)
    return client.put_markdown(note_path, render_markdown(record), overwrite=overwrite)


def normalize_obsidian_folder(value: str) -> str:
    text = value.strip().replace("\\", "/").strip("/")
    if not text:
        return ""
    _validate_obsidian_parts(text.split("/"))
    return text


def normalize_obsidian_note_path(value: str) -> str:
    text = value.strip().replace("\\", "/")
    if not text or text.startswith("/") or text.startswith("~") or ":" in text:
        raise ValueError("Obsidian note path must be relative to the vault")
    parts = [part for part in text.split("/") if part]
    _validate_obsidian_parts(parts)
    path = "/".join(parts)
    if not path.endswith(".md"):
        raise ValueError("Obsidian note path must end with .md")
    return path


def _validate_obsidian_parts(parts: list[str]) -> None:
    if not parts:
        raise ValueError("Obsidian path must not be empty")
    for part in parts:
        if part in {".", ".."} or part.startswith("."):
            raise ValueError("Obsidian path must not include hidden or parent segments")


def _validate_loopback_url(value: str) -> None:
    parsed = parse_http_url(value, field_name="Obsidian URL")
    if not is_loopback_host(parsed.hostname or ""):
        raise ValueError("Obsidian URL must point to localhost")


def _quote_path(value: str) -> str:
    return "/".join(urllib.parse.quote(part, safe="") for part in value.split("/"))


def _bool_env(value: str | None, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
