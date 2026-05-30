from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_VAULT = "~/GriosAI-vault"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_VISION_MODEL = "qwen2.5vl:7b"


@dataclass(frozen=True)
class GriosConfig:
    vault_dir: Path
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    ollama_url: str = DEFAULT_OLLAMA_URL
    vision_model: str = DEFAULT_VISION_MODEL
    api_token: str | None = None
    allowed_hosts: tuple[str, ...] = ()

    @classmethod
    def from_env(
        cls,
        *,
        vault_dir: str | Path | None = None,
        host: str | None = None,
        port: int | str | None = None,
        ollama_url: str | None = None,
        vision_model: str | None = None,
        api_token: str | None = None,
        allowed_hosts: tuple[str, ...] | None = None,
    ) -> "GriosConfig":
        raw_port = port or os.getenv("GRIOSAI_PORT") or DEFAULT_PORT
        raw_allowed_hosts = os.getenv("GRIOSAI_ALLOWED_HOSTS") or ""
        return cls(
            vault_dir=resolve_path(vault_dir or os.getenv("GRIOSAI_VAULT_DIR") or DEFAULT_VAULT),
            host=host or os.getenv("GRIOSAI_HOST") or DEFAULT_HOST,
            port=int(raw_port),
            ollama_url=ollama_url or os.getenv("GRIOSAI_OLLAMA_URL") or DEFAULT_OLLAMA_URL,
            vision_model=vision_model
            or os.getenv("GRIOSAI_VISION_MODEL")
            or DEFAULT_VISION_MODEL,
            api_token=api_token or os.getenv("GRIOSAI_API_TOKEN") or None,
            allowed_hosts=allowed_hosts
            if allowed_hosts is not None
            else tuple(item.strip() for item in raw_allowed_hosts.split(",") if item.strip()),
        )


def resolve_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()
