import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from griosai.brain import AnalysisRecord, ensure_vault, write_analysis_note
from griosai.cli import main
from griosai.dashboard import write_dashboard
from griosai.lineage import (
    LINEAGE_SCHEMA,
    analysis_id,
    format_lineage_json,
    lineage_exit_code,
    verify_lineage,
    write_lineage_manifest,
)


class LineageTests(unittest.TestCase):
    def test_analysis_id_is_stable_across_generated_timestamps(self) -> None:
        first = AnalysisRecord(
            title="Same Source",
            summary="Same body",
            created_at="2026-01-01T00:00:00+00:00",
        )
        second = AnalysisRecord(
            title="Same Source",
            summary="Same body",
            created_at="2026-01-02T00:00:00+00:00",
        )

        self.assertEqual(analysis_id(first), analysis_id(second))

    def test_write_lineage_manifest_tracks_artifact_hashes_without_raw_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            secret = "sk-" + ("C" * 24)
            record = AnalysisRecord(
                title="Private Customer Name",
                summary=f"Secret summary {secret}",
                observations=[f"private observation {secret}"],
                actions=["look at /Users/gustavorios/private"],
                raw={"token": secret},
            )
            note = write_analysis_note(vault, record, slug="private-customer")
            dashboard = write_dashboard(vault, record, slug="private-customer")

            manifest_path = write_lineage_manifest(
                vault,
                record,
                artifacts={"dashboard": dashboard, "note": note},
                slug="private-customer",
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            encoded = json.dumps(manifest, sort_keys=True)

            self.assertEqual(manifest["schema"], LINEAGE_SCHEMA)
            self.assertEqual(manifest["analysis_id"], analysis_id(record))
            self.assertNotIn(secret, encoded)
            self.assertNotIn(record.summary, encoded)
            self.assertNotIn("/Users/gustavorios", encoded)
            artifacts = {item["kind"]: item for item in manifest["artifacts"]}
            self.assertEqual(artifacts["note"]["path"], "notes/private-customer.md")
            self.assertEqual(
                artifacts["note"]["sha256"],
                hashlib.sha256(note.read_bytes()).hexdigest(),
            )

    def test_default_lineage_slug_uses_analysis_id_and_sanitizes_source_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            secret = "supersecret-token-value"
            record = AnalysisRecord(
                title=f"Private Customer {secret}",
                summary="Local",
                source_image=f"https://example.test/images/private.png?token={secret}#frag",
            )
            note = write_analysis_note(vault, record, slug="artifact")
            dashboard = write_dashboard(vault, record, slug="artifact")

            manifest_path = write_lineage_manifest(
                vault,
                record,
                artifacts={"dashboard": dashboard, "note": note},
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            encoded = json.dumps(manifest, sort_keys=True)
            expected_slug = f"analysis-{analysis_id(record)[:12]}"

            self.assertEqual(manifest_path.name, f"{expected_slug}.json")
            self.assertEqual(manifest["analysis"]["slug"], expected_slug)
            self.assertEqual(manifest["analysis"]["source_image_name"], "private.png")
            self.assertNotIn(secret, encoded)
            self.assertNotIn(record.title, encoded)

    def test_verify_lineage_detects_artifact_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            record = AnalysisRecord(title="Tamper", summary="One")
            note = write_analysis_note(vault, record, slug="tamper")
            dashboard = write_dashboard(vault, record, slug="tamper")
            write_lineage_manifest(
                vault,
                record,
                artifacts={"dashboard": dashboard, "note": note},
                slug="tamper",
            )
            note.write_text("# Changed\n", encoding="utf-8")

            verification = verify_lineage(vault)
            codes = {finding.code for finding in verification.findings}

            self.assertEqual(lineage_exit_code(verification), 1)
            self.assertIn("artifact-size", codes)
            self.assertIn("artifact-sha256", codes)

    def test_verify_lineage_rejects_raw_private_fields_in_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            record = AnalysisRecord(title="Privacy", summary="Do not duplicate")
            note = write_analysis_note(vault, record, slug="privacy")
            dashboard = write_dashboard(vault, record, slug="privacy")
            manifest_path = write_lineage_manifest(
                vault,
                record,
                artifacts={"dashboard": dashboard, "note": note},
                slug="privacy",
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["summary"] = "Do not duplicate"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            verification = verify_lineage(vault)
            codes = {finding.code for finding in verification.findings}

            self.assertEqual(lineage_exit_code(verification), 1)
            self.assertIn("manifest-raw-field", codes)

    def test_cli_lineage_verify_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            payload = Path(tmp) / "analysis.json"
            payload.write_text(
                json.dumps({"title": "CLI Lineage", "summary": "Track it"}),
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(["add-analysis", "--vault", str(vault), "--json-file", str(payload)]),
                    0,
                )

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["lineage-verify", "--vault", str(vault), "--json"]), 0)
            parsed = json.loads(output.getvalue())

            self.assertEqual(parsed["summary"]["manifests"], 1)
            self.assertEqual(parsed["summary"]["artifacts"], 2)
            self.assertEqual(parsed["summary"]["findings"]["fail"], 0)

    def test_missing_vault_fails_lineage_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            verification = verify_lineage(Path(tmp) / "missing")

            self.assertEqual(lineage_exit_code(verification), 1)
            self.assertEqual(json.loads(format_lineage_json(verification))["summary"]["findings"]["fail"], 1)


if __name__ == "__main__":
    unittest.main()
