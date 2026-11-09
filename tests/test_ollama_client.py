import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from griosai.ollama_client import (
    MAX_IMAGE_BYTES,
    ImageTooLargeError,
    OllamaError,
    UnsupportedImageError,
    _parse_model_json,
    _validate_image,
    analyze_image,
    ollama_chat_url,
    validate_ollama_url,
)


class OllamaClientTests(unittest.TestCase):
    def test_validate_ollama_url_accepts_local_and_cluster_service_urls(self) -> None:
        validate_ollama_url("http://127.0.0.1:11434")
        validate_ollama_url("http://ollama:11434")
        self.assertEqual(
            ollama_chat_url("http://127.0.0.1:11434/"),
            "http://127.0.0.1:11434/api/chat",
        )

    def test_validate_ollama_url_rejects_credentials_query_fragment_and_bad_port(self) -> None:
        for url in (
            "http://user:pass@127.0.0.1:11434",
            "http://127.0.0.1:11434?token=abc",
            "http://127.0.0.1:11434#fragment",
            "http://127.0.0.1:bad",
            "file:///tmp/ollama.sock",
            "http://127.0.0.1:11434/with space",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    validate_ollama_url(url)

    def test_validate_image_accepts_supported_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "sample.png"
            image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
            _validate_image(image)

    def test_validate_image_rejects_unsupported_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "sample.png"
            image.write_bytes(b"not really an image")
            with self.assertRaises(UnsupportedImageError):
                _validate_image(image)

    def test_validate_image_rejects_large_file_before_reading_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "sample.png"
            with image.open("wb") as handle:
                handle.truncate(MAX_IMAGE_BYTES + 1)
            with self.assertRaises(ImageTooLargeError):
                _validate_image(image)

    def test_parse_model_json_error_does_not_echo_private_content(self) -> None:
        secret = "sk-proj-" + ("O" * 24)

        with self.assertRaises(OllamaError) as caught:
            _parse_model_json(f"private image notes {secret}")

        self.assertNotIn(secret, str(caught.exception))
        self.assertNotIn("private image notes", str(caught.exception))

    def test_analyze_image_malformed_response_error_does_not_echo_response_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "sample.png"
            image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
            secret = "sk-proj-" + ("R" * 24)

            with patch(
                "griosai.ollama_client._post_json",
                return_value={"message": {"content": None}, "debug": secret},
            ), self.assertRaises(OllamaError) as caught:
                analyze_image(
                    image,
                    model="qwen2.5vl:7b",
                    ollama_url="http://127.0.0.1:11434",
                )

        self.assertNotIn(secret, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
