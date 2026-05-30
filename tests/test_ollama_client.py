import tempfile
import unittest
from pathlib import Path

from griosai.ollama_client import (
    MAX_IMAGE_BYTES,
    ImageTooLargeError,
    UnsupportedImageError,
    _validate_image,
)


class OllamaClientTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
