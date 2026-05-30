from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .brain import AnalysisRecord


MAX_IMAGE_BYTES = 12 * 1024 * 1024
DEFAULT_IMAGE_PROMPT = (
    "Analyze this image for a private local dashboard. Return strict JSON with "
    "title, summary, observations, and actions. Keep observations factual and "
    "actions practical."
)


class OllamaError(RuntimeError):
    pass


class ImageTooLargeError(OllamaError):
    pass


class UnsupportedImageError(OllamaError):
    pass


def analyze_image(
    image_path: Path,
    *,
    model: str,
    ollama_url: str,
    prompt: str = DEFAULT_IMAGE_PROMPT,
    timeout_seconds: int = 120,
) -> AnalysisRecord:
    image = image_path.expanduser().resolve()
    if not image.exists():
        raise FileNotFoundError(image)
    _validate_image(image)

    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [base64.b64encode(image.read_bytes()).decode("ascii")],
            }
        ],
    }
    response = _post_json(f"{ollama_url.rstrip('/')}/api/chat", payload, timeout_seconds)
    content = response.get("message", {}).get("content")
    if not isinstance(content, str):
        raise OllamaError(f"Ollama response did not include message.content: {response}")

    parsed = _parse_model_json(content)
    return AnalysisRecord.from_mapping(parsed, model=model, source_image=str(image))


def _post_json(url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise OllamaError(f"Could not reach local Ollama at {url}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise OllamaError(f"Ollama returned invalid JSON from {url}") from exc


def _parse_model_json(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise OllamaError(f"Model did not return valid JSON: {content[:300]}") from exc
    if not isinstance(parsed, dict):
        raise OllamaError("Model JSON must be an object")
    return parsed


def _validate_image(image: Path) -> None:
    size = image.stat().st_size
    if size > MAX_IMAGE_BYTES:
        raise ImageTooLargeError(
            f"Image is {size} bytes, above the {MAX_IMAGE_BYTES} byte limit"
        )
    with image.open("rb") as handle:
        header = handle.read(16)
    if not _looks_like_supported_image(header):
        raise UnsupportedImageError("Image type is unsupported or does not match its extension")


def _looks_like_supported_image(header: bytes) -> bool:
    return (
        header.startswith(b"\x89PNG\r\n\x1a\n")
        or header.startswith(b"\xff\xd8\xff")
        or header.startswith(b"GIF87a")
        or header.startswith(b"GIF89a")
        or header.startswith(b"BM")
        or (header.startswith(b"RIFF") and header[8:12] == b"WEBP")
    )
