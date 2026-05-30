import json
import tempfile
import unittest
from pathlib import Path

from griosai.brain import AnalysisRecord
from griosai.cli import main
from griosai.notebook import (
    NotebookConnectorAdapter,
    redact_text,
    validate_notebook_packet,
    write_notebook_packet,
)


class NotebookTests(unittest.TestCase):
    def test_write_notebook_packet_creates_sanitized_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = AnalysisRecord(
                title="Notebook Packet",
                summary="Review /Users/gustavorios/private/report.md with Bearer abcdefghijk",
                observations=["api_key=secret-value should not leak"],
                actions=["Import the packet manually"],
                source_image="/Users/gustavorios/private/image.png",
                raw={"private": "/Users/gustavorios/private/raw.jsonl"},
            )
            packet = write_notebook_packet(Path(tmp), record)

            self.assertTrue((packet.packet_dir / "index.md").exists())
            self.assertTrue((packet.packet_dir / "tables.csv").exists())
            self.assertTrue((packet.packet_dir / "report.html").exists())
            manifest = json.loads((packet.packet_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["record"]["raw_key_count"], 1)
            self.assertEqual(manifest["record"]["source_image_name"], "image.png")
            self.assertFalse(validate_notebook_packet(packet.packet_dir))

            combined = "\n".join(path.read_text(encoding="utf-8") for path in packet.source_paths())
            self.assertNotIn("/Users/gustavorios", combined)
            self.assertNotIn("abcdefghijk", combined)
            self.assertNotIn("secret-value", combined)
            self.assertIn("[local-path]", combined)
            self.assertIn("[redacted-secret]", combined)

    def test_connector_payload_uses_packet_directory_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = NotebookConnectorAdapter(Path(tmp))
            packet = adapter.write_packet({"title": "Connector", "summary": "Works"})
            payload = packet.connector_payload()

            self.assertEqual(payload["dashboard_id"], "connector")
            self.assertEqual(payload["sources"], ["index.md", "tables.csv", "report.html", "manifest.json"])
            self.assertIn("*.jsonl", payload["deny_sources"])
            self.assertEqual(payload["packet_dir"], str(packet.packet_dir))

    def test_packet_root_must_stay_inside_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            outside = Path(tmp) / "outside"
            with self.assertRaises(ValueError):
                write_notebook_packet(
                    vault,
                    AnalysisRecord(title="Unsafe", summary="No"),
                    packet_root=outside,
                )

    def test_validate_notebook_packet_flags_hidden_and_raw_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = Path(tmp) / "packet"
            packet_dir.mkdir()
            (packet_dir / ".env").write_text("TOKEN=abc", encoding="utf-8")
            (packet_dir / "raw-log.jsonl").write_text("{}", encoding="utf-8")

            findings = validate_notebook_packet(packet_dir)
            self.assertTrue(any("hidden file" in finding for finding in findings))
            self.assertTrue(any("denied source file" in finding for finding in findings))

    def test_redact_text_removes_paths_and_likely_secrets(self) -> None:
        text = redact_text("path=/Users/gustavorios/x token=abc123456 sk-abcdefghijklmnop")
        self.assertNotIn("/Users/gustavorios", text)
        self.assertNotIn("abc123456", text)
        self.assertNotIn("sk-abcdefghijklmnop", text)

    def test_cli_notebook_packet_imports_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / "analysis.json"
            vault = Path(tmp) / "vault"
            payload.write_text(
                '{"title": "Notebook CLI", "summary": "Packet please"}',
                encoding="utf-8",
            )

            self.assertEqual(
                main(["notebook-packet", "--vault", str(vault), "--json-file", str(payload)]),
                0,
            )
            self.assertTrue((vault / "notebook-packets" / "notebook-cli" / "index.md").exists())

    def test_packet_validation_blocks_unsanitized_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = Path(tmp) / "packet"
            packet_dir.mkdir()
            (packet_dir / "index.md").write_text("Bearer abcdefghijk", encoding="utf-8")

            findings = validate_notebook_packet(packet_dir)
            self.assertTrue(any("likely secret" in finding for finding in findings))


if __name__ == "__main__":
    unittest.main()
